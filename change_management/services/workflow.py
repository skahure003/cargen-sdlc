from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from change_management.models import (
    ApprovalStep,
    ChangeActivity,
    ChangeNotification,
    ChangeRequest,
    ChangeRiskAssessment,
    ImplementationTask,
    initialize_workflow,
)


ROLE_GROUP_MAP = {
    ApprovalStep.ROLE_REQUESTER: "Requester",
    ApprovalStep.ROLE_REVIEWER: "Reviewer",
    ApprovalStep.ROLE_APPROVER: "Approver",
    ApprovalStep.ROLE_IMPLEMENTER: "Implementer",
    ApprovalStep.ROLE_AUDITOR: "Auditor/Admin",
    ApprovalStep.ROLE_CAB: "CAB",
}
OPERATIONAL_GROUPS = ["Approver", "Implementer", "Auditor/Admin"]


def get_risk_assessment(change_request: ChangeRequest) -> ChangeRiskAssessment | None:
    try:
        return change_request.risk_assessment
    except ChangeRiskAssessment.DoesNotExist:
        return None


def has_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def has_any_group(user, group_names: list[str]) -> bool:
    return user.is_authenticated and user.groups.filter(name__in=group_names).exists()


def default_group_for_role(role: str) -> str:
    return ROLE_GROUP_MAP.get(role, "")


def step_is_assigned_to_user(step: ApprovalStep, user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or has_group(user, "Auditor/Admin"):
        return True
    if step.assigned_user_id == user.id:
        return True
    user_groups = set(user.groups.values_list("name", flat=True))
    if step.assigned_group and step.assigned_group in user_groups:
        return True
    return ROLE_GROUP_MAP.get(step.assigned_role) in user_groups


def can_view_request(user, change_request: ChangeRequest) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or has_group(user, "Auditor/Admin"):
        return True
    if change_request.requester_id == user.id:
        return True
    if change_request.approval_steps.filter(assigned_user=user).exists():
        return True
    user_groups = list(user.groups.values_list("name", flat=True))
    if change_request.approval_steps.filter(assigned_group__in=user_groups).exists():
        return True
    if change_request.approval_steps.filter(
        assigned_user__isnull=True,
        assigned_group="",
        assigned_role__in=[role for role, group in ROLE_GROUP_MAP.items() if group in user_groups],
    ).exists():
        return True
    if change_request.implementation_tasks.filter(owner=user).exists():
        return True
    if has_group(user, "Approver") and change_request.approval_steps.filter(assigned_role=ApprovalStep.ROLE_APPROVER).exists():
        return True
    if has_group(user, "Implementer") and change_request.status in {
        ChangeRequest.STATUS_APPROVED,
        ChangeRequest.STATUS_SCHEDULED,
        ChangeRequest.STATUS_IMPLEMENTED,
        ChangeRequest.STATUS_VALIDATED,
    }:
        return True
    return False


def visible_requests_for_user(user):
    queryset = ChangeRequest.objects.select_related("change_type", "requester").prefetch_related(
        "approval_steps",
        "implementation_tasks",
    )
    if user.is_superuser or has_group(user, "Auditor/Admin"):
        return queryset
    visible_ids = [change_request.pk for change_request in queryset if can_view_request(user, change_request)]
    return queryset.filter(pk__in=visible_ids)


def can_edit_request(user, change_request: ChangeRequest) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or has_group(user, "Auditor/Admin"):
        return True
    return change_request.requester_id == user.id and change_request.status in {
        ChangeRequest.STATUS_DRAFT,
        ChangeRequest.STATUS_REJECTED,
    }


def can_assess_risk(user) -> bool:
    return user.is_authenticated and (
        user.is_superuser
        or has_any_group(user, ["Approver", "Auditor/Admin"])
    )


def can_add_evidence(user, change_request: ChangeRequest) -> bool:
    return can_view_request(user, change_request)


def pending_steps_for_user(user):
    if not user.is_authenticated:
        return []
    steps = ApprovalStep.objects.select_related("change_request", "assigned_user")
    return [step for step in steps if step.is_waiting_for(user)]


def all_required_approvals_complete(change_request: ChangeRequest) -> bool:
    return not change_request.approval_steps.filter(
        required=True,
        status=ApprovalStep.STATUS_PENDING,
    ).exists()


def cab_required(change_request: ChangeRequest, risk_assessment: ChangeRiskAssessment | None = None) -> bool:
    return False


def ensure_step_assignments(change_request: ChangeRequest):
    for step in change_request.approval_steps.all():
        if not step.assigned_group and not step.assigned_user_id:
            step.assigned_group = default_group_for_role(step.assigned_role)
            step.save(update_fields=["assigned_group", "updated_at"])


def ensure_cab_step(change_request: ChangeRequest) -> ApprovalStep | None:
    return None


@transaction.atomic
def synchronize_risk_workflow(change_request: ChangeRequest, actor=None):
    ensure_step_assignments(change_request)
    ensure_cab_step(change_request)


def validate_submission(change_request: ChangeRequest):
    required_fields = [
        "title",
        "business_justification",
        "implementation_plan",
        "test_validation_plan",
        "rollback_plan",
    ]
    missing = [field.replace("_", " ").title() for field in required_fields if not getattr(change_request, field)]
    if missing:
        raise ValidationError(f"Cannot submit until required fields are complete: {', '.join(missing)}.")
    if not change_request.approval_steps.exists():
        raise ValidationError("Cannot submit a change request without approval steps.")


def validate_transition_preconditions(change_request: ChangeRequest, target_status: str):
    if target_status == ChangeRequest.STATUS_SUBMITTED:
        validate_submission(change_request)
    elif target_status == ChangeRequest.STATUS_APPROVED:
        if not all_required_approvals_complete(change_request):
            raise ValidationError("All required approval steps must be completed before approval.")
    elif target_status == ChangeRequest.STATUS_SCHEDULED:
        risk_assessment = get_risk_assessment(change_request)
        if not risk_assessment or not risk_assessment.assessed_at:
            raise ValidationError("A completed risk assessment is required before scheduling.")
        if not all_required_approvals_complete(change_request):
            raise ValidationError("All required approvals must be completed before scheduling.")
    elif target_status == ChangeRequest.STATUS_IMPLEMENTED:
        if not change_request.planned_start or not change_request.planned_end:
            raise ValidationError("A planned implementation window is required before marking implemented.")
    elif target_status == ChangeRequest.STATUS_CLOSED:
        if not change_request.evidence.exists():
            raise ValidationError("At least one evidence attachment is required before closing the change.")


def can_transition(user, change_request: ChangeRequest, target_status: str) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or has_group(user, "Auditor/Admin"):
        return True
    if target_status == ChangeRequest.STATUS_SUBMITTED:
        return change_request.requester_id == user.id
    if target_status in {ChangeRequest.STATUS_APPROVED, ChangeRequest.STATUS_REJECTED}:
        return has_group(user, "Approver")
    if target_status in {
        ChangeRequest.STATUS_SCHEDULED,
        ChangeRequest.STATUS_IMPLEMENTED,
        ChangeRequest.STATUS_VALIDATED,
    }:
        return has_group(user, "Implementer")
    if target_status == ChangeRequest.STATUS_CLOSED:
        return has_group(user, "Approver")
    if target_status == ChangeRequest.STATUS_CANCELLED:
        return change_request.requester_id == user.id
    return False


def notify_users(change_request: ChangeRequest, users, category: str, message: str):
    unique_users = {user.pk: user for user in users if user and getattr(user, "is_authenticated", True)}.values()
    for user in unique_users:
        ChangeNotification.objects.create(
            change_request=change_request,
            user=user,
            category=category,
            message=message,
        )


def users_for_pending_steps(change_request: ChangeRequest):
    User = get_user_model()
    groups = set()
    user_ids = set()
    for step in change_request.approval_steps.filter(status=ApprovalStep.STATUS_PENDING):
        if step.assigned_user_id:
            user_ids.add(step.assigned_user_id)
        elif step.assigned_group:
            groups.add(step.assigned_group)
        else:
            default_group = default_group_for_role(step.assigned_role)
            if default_group:
                groups.add(default_group)
    users = list(User.objects.filter(pk__in=user_ids))
    if groups:
        users.extend(User.objects.filter(groups__name__in=list(groups)).distinct())
    return users


@transaction.atomic
def create_change_request(change_request: ChangeRequest, actor, task_formset):
    change_request.requester = actor
    change_request.save()
    task_formset.instance = change_request
    task_formset.save()
    initialize_workflow(change_request)
    ensure_step_assignments(change_request)
    synchronize_risk_workflow(change_request, actor=actor)
    ChangeActivity.record(
        change_request=change_request,
        actor=actor,
        action=ChangeActivity.ACTION_CREATED,
        summary="Change request created.",
    )
    return change_request


def update_change_request(change_request: ChangeRequest, actor, form, task_formset):
    change_request = form.save()
    task_formset.save()
    synchronize_risk_workflow(change_request, actor=actor)
    ChangeActivity.record(
        change_request=change_request,
        actor=actor,
        action=ChangeActivity.ACTION_UPDATED,
        summary="Change request updated.",
    )
    return change_request


@transaction.atomic
def submit_change_request(change_request: ChangeRequest, actor):
    validate_transition_preconditions(change_request, ChangeRequest.STATUS_SUBMITTED)
    synchronize_risk_workflow(change_request, actor=actor)
    change_request.transition_to(
        new_status=ChangeRequest.STATUS_SUBMITTED,
        actor=actor,
        summary="Change request submitted for approval.",
    )
    ChangeActivity.record(
        change_request=change_request,
        actor=actor,
        action=ChangeActivity.ACTION_SUBMITTED,
        summary="Change request submitted.",
    )
    notify_users(
        change_request,
        users_for_pending_steps(change_request),
        category="submission",
        message=f"{change_request.change_id} is waiting for approval.",
    )


@transaction.atomic
def decide_approval_step(step: ApprovalStep, actor, outcome: str, comments: str = ""):
    if not step_is_assigned_to_user(step, actor) and not actor.is_superuser:
        raise ValidationError("You are not assigned to this approval step.")
    step.decide(actor=actor, outcome=outcome, comments=comments)
    change_request = step.change_request
    any_rejected = change_request.approval_steps.filter(status=ApprovalStep.STATUS_REJECTED).exists()
    if any_rejected:
        change_request.transition_to(
            new_status=ChangeRequest.STATUS_REJECTED,
            actor=actor,
            summary="Approver rejected the request.",
        )
        notify_users(
            change_request,
            [change_request.requester],
            category="rejection",
            message=f"{change_request.change_id} was rejected by the approver.",
        )
        return
    if all_required_approvals_complete(change_request):
        validate_transition_preconditions(change_request, ChangeRequest.STATUS_APPROVED)
        change_request.transition_to(
            new_status=ChangeRequest.STATUS_APPROVED,
            actor=actor,
            summary="All required approvals completed.",
        )
        notify_users(
            change_request,
            [change_request.requester],
            category="approval",
            message=f"{change_request.change_id} has been approved.",
        )
    else:
        notify_users(
            change_request,
            users_for_pending_steps(change_request),
            category="approval",
            message=f"{change_request.change_id} is awaiting your approval.",
        )


@transaction.atomic
def transition_change_request(change_request: ChangeRequest, actor, target_status: str, notes: str = ""):
    validate_transition_preconditions(change_request, target_status)
    change_request.transition_to(
        new_status=target_status,
        actor=actor,
        summary=notes or f"Status changed to {dict(ChangeRequest.STATUS_CHOICES)[target_status]}.",
    )
    if target_status == ChangeRequest.STATUS_SCHEDULED:
        recipients = list(change_request.implementation_tasks.exclude(owner__isnull=True).values_list("owner", flat=True))
        if recipients:
            User = get_user_model()
            notify_users(
                change_request,
                User.objects.filter(pk__in=recipients),
                category="schedule",
                message=f"{change_request.change_id} is scheduled and ready for implementation.",
            )


@transaction.atomic
def update_risk(change_request: ChangeRequest, risk_assessment: ChangeRiskAssessment, actor):
    risk_assessment.change_request = change_request
    risk_assessment.assessed_by = actor
    risk_assessment.assessed_at = timezone.now()
    risk_assessment.save()
    change_request.risk_level = risk_assessment.residual_risk
    change_request.save(update_fields=["risk_level", "updated_at"])
    synchronize_risk_workflow(change_request, actor=actor)
    ChangeActivity.record(
        change_request=change_request,
        actor=actor,
        action=ChangeActivity.ACTION_UPDATED,
        summary="Risk assessment updated.",
    )
