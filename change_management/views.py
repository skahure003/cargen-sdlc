from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    ApprovalDecisionForm,
    ChangeCommentForm,
    ChangeEvidenceForm,
    ChangeRequestForm,
    ChangeRiskAssessmentForm,
    ImplementationTaskFormSet,
    StatusTransitionForm,
)
from .models import (
    ApprovalStep,
    ChangeActivity,
    ChangeRequest,
    ChangeRiskAssessment,
    ChangeType,
    initialize_workflow,
)


def has_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def can_edit_request(user, change_request: ChangeRequest) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or has_group(user, "Auditor/Admin"):
        return True
    return change_request.requester_id == user.id and change_request.status in {
        ChangeRequest.STATUS_DRAFT,
        ChangeRequest.STATUS_REJECTED,
    }


def can_transition(user, change_request: ChangeRequest, target_status: str) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or has_group(user, "Auditor/Admin"):
        return True
    if target_status == ChangeRequest.STATUS_SUBMITTED:
        return change_request.requester_id == user.id
    if target_status in {ChangeRequest.STATUS_APPROVED, ChangeRequest.STATUS_REJECTED}:
        return has_group(user, "Approver") or has_group(user, "CAB")
    if target_status in {
        ChangeRequest.STATUS_SCHEDULED,
        ChangeRequest.STATUS_IMPLEMENTED,
        ChangeRequest.STATUS_VALIDATED,
    }:
        return has_group(user, "Implementer")
    if target_status == ChangeRequest.STATUS_CLOSED:
        return has_group(user, "Reviewer") or has_group(user, "Approver") or has_group(user, "CAB")
    if target_status == ChangeRequest.STATUS_CANCELLED:
        return change_request.requester_id == user.id
    return False


def can_assess_risk(user) -> bool:
    if not user.is_authenticated:
        return False
    return (
        user.is_superuser
        or has_group(user, "Reviewer")
        or has_group(user, "Approver")
        or has_group(user, "CAB")
        or has_group(user, "Auditor/Admin")
    )


def can_add_evidence(user, change_request: ChangeRequest) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or has_group(user, "Auditor/Admin"):
        return True
    if change_request.requester_id == user.id:
        return True
    return any(
        has_group(user, group_name)
        for group_name in ["Reviewer", "Approver", "CAB", "Implementer"]
    )


def dashboard(request):
    changes = ChangeRequest.objects.select_related("change_type", "requester").all()[:8]
    metrics = ChangeRequest.objects.aggregate(
        total=Count("id"),
        submitted=Count("id", filter=Q(status=ChangeRequest.STATUS_SUBMITTED)),
        in_review=Count("id", filter=Q(status=ChangeRequest.STATUS_IN_REVIEW)),
        approved=Count("id", filter=Q(status=ChangeRequest.STATUS_APPROVED)),
    )
    queue_count = 0
    my_changes = []
    if request.user.is_authenticated:
        queue_count = sum(
            1
            for step in ApprovalStep.objects.select_related("assigned_user")
            if step.is_waiting_for(request.user)
        )
        my_changes = ChangeRequest.objects.filter(requester=request.user).select_related("change_type")[:6]
    return render(
        request,
        "change_management/dashboard.html",
        {
            "changes": changes,
            "metrics": metrics,
            "queue_count": queue_count,
            "my_changes": my_changes,
            "change_types": ChangeType.objects.filter(is_active=True),
        },
    )


@login_required
def request_list(request):
    changes = ChangeRequest.objects.select_related("change_type", "requester").all()
    return render(request, "change_management/request_list.html", {"changes": changes})


@login_required
def request_create(request):
    if not (
        request.user.is_superuser
        or request.user.has_perm("change_management.submit_change")
        or has_group(request.user, "Requester")
    ):
        raise PermissionDenied
    if request.method == "POST":
        form = ChangeRequestForm(request.POST)
        task_formset = ImplementationTaskFormSet(request.POST, prefix="tasks")
        if form.is_valid() and task_formset.is_valid():
            change_request = form.save(commit=False)
            change_request.requester = request.user
            change_request.save()
            task_formset.instance = change_request
            task_formset.save()
            initialize_workflow(change_request)
            ChangeActivity.record(
                change_request=change_request,
                actor=request.user,
                action=ChangeActivity.ACTION_CREATED,
                summary="Change request created.",
            )
            messages.success(request, f"{change_request.change_id} created.")
            return redirect("change_management:request_detail", pk=change_request.pk)
    else:
        form = ChangeRequestForm()
        task_formset = ImplementationTaskFormSet(prefix="tasks")
    return render(
        request,
        "change_management/request_form.html",
        {"form": form, "task_formset": task_formset, "page_title": "Create change request"},
    )


@login_required
def request_update(request, pk: int):
    change_request = get_object_or_404(ChangeRequest.objects.select_related("requester"), pk=pk)
    if not can_edit_request(request.user, change_request):
        raise PermissionDenied
    if request.method == "POST":
        form = ChangeRequestForm(request.POST, instance=change_request)
        task_formset = ImplementationTaskFormSet(request.POST, instance=change_request, prefix="tasks")
        if form.is_valid() and task_formset.is_valid():
            change_request = form.save()
            task_formset.save()
            ChangeActivity.record(
                change_request=change_request,
                actor=request.user,
                action=ChangeActivity.ACTION_UPDATED,
                summary="Change request updated.",
            )
            messages.success(request, f"{change_request.change_id} updated.")
            return redirect("change_management:request_detail", pk=change_request.pk)
    else:
        form = ChangeRequestForm(instance=change_request)
        task_formset = ImplementationTaskFormSet(instance=change_request, prefix="tasks")
    return render(
        request,
        "change_management/request_form.html",
        {
            "form": form,
            "task_formset": task_formset,
            "change_request": change_request,
            "page_title": f"Edit {change_request.change_id}",
        },
    )


@login_required
def request_detail(request, pk: int):
    change_request = get_object_or_404(
        ChangeRequest.objects.select_related("requester", "change_type", "template").prefetch_related(
            "approval_steps",
            "approval_decisions",
            "implementation_tasks",
            "evidence",
            "comments",
            "activity",
        ),
        pk=pk,
    )
    risk_assessment, _ = ChangeRiskAssessment.objects.get_or_create(
        change_request=change_request,
        defaults={"residual_risk": change_request.risk_level},
    )
    decision_forms = {}
    for step in change_request.approval_steps.all():
        if step.is_waiting_for(request.user):
            decision_forms[step.id] = ApprovalDecisionForm(step=step)
    available_transitions = [
        status
        for status in change_request.TRANSITIONS.get(change_request.status, set())
        if can_transition(request.user, change_request, status)
    ]
    return render(
        request,
        "change_management/request_detail.html",
        {
            "change_request": change_request,
            "comment_form": ChangeCommentForm(),
            "evidence_form": ChangeEvidenceForm(),
            "risk_form": ChangeRiskAssessmentForm(instance=risk_assessment),
            "transition_form": StatusTransitionForm(
                change_request=change_request,
                allowed_statuses=available_transitions,
            ),
            "decision_forms": decision_forms,
            "can_edit": can_edit_request(request.user, change_request),
            "can_assess_risk": can_assess_risk(request.user),
            "can_add_evidence": can_add_evidence(request.user, change_request),
            "available_transitions": available_transitions,
        },
    )


@login_required
def submit_request(request, pk: int):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    if not can_transition(request.user, change_request, ChangeRequest.STATUS_SUBMITTED):
        raise PermissionDenied
    if change_request.status == ChangeRequest.STATUS_DRAFT:
        change_request.transition_to(
            new_status=ChangeRequest.STATUS_SUBMITTED,
            actor=request.user,
            summary="Change request submitted for review.",
        )
        change_request.transition_to(
            new_status=ChangeRequest.STATUS_IN_REVIEW,
            actor=request.user,
            summary="Change request entered the review phase.",
        )
        ChangeActivity.record(
            change_request=change_request,
            actor=request.user,
            action=ChangeActivity.ACTION_SUBMITTED,
            summary="Change request submitted.",
        )
        messages.success(request, f"{change_request.change_id} submitted for review.")
    return redirect("change_management:request_detail", pk=pk)


@login_required
def approval_queue(request):
    steps = [
        step
        for step in ApprovalStep.objects.select_related("change_request", "assigned_user")
        if step.is_waiting_for(request.user)
    ]
    return render(request, "change_management/approval_queue.html", {"steps": steps})


@login_required
def decide_step(request, pk: int):
    step = get_object_or_404(ApprovalStep.objects.select_related("change_request"), pk=pk)
    if not step.is_waiting_for(request.user) and not request.user.is_superuser:
        raise PermissionDenied
    form = ApprovalDecisionForm(request.POST or None, step=step)
    if request.method == "POST" and form.is_valid():
        outcome = form.cleaned_data["outcome"]
        step.decide(actor=request.user, outcome=outcome, comments=form.cleaned_data["comments"])
        pending_required = step.change_request.approval_steps.filter(
            status=ApprovalStep.STATUS_PENDING,
            required=True,
        ).exists()
        any_rejected = step.change_request.approval_steps.filter(status=ApprovalStep.STATUS_REJECTED).exists()
        if any_rejected and step.change_request.can_transition_to(ChangeRequest.STATUS_REJECTED):
            step.change_request.transition_to(
                new_status=ChangeRequest.STATUS_REJECTED,
                actor=request.user,
                summary="Approval step rejected the request.",
            )
        elif not pending_required and step.change_request.can_transition_to(ChangeRequest.STATUS_APPROVED):
            step.change_request.transition_to(
                new_status=ChangeRequest.STATUS_APPROVED,
                actor=request.user,
                summary="All required approvals completed.",
            )
        messages.success(request, "Approval recorded.")
    return redirect("change_management:request_detail", pk=step.change_request.pk)


@login_required
def transition_request(request, pk: int):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    available_transitions = [
        status
        for status in change_request.TRANSITIONS.get(change_request.status, set())
        if can_transition(request.user, change_request, status)
    ]
    form = StatusTransitionForm(
        request.POST or None,
        change_request=change_request,
        allowed_statuses=available_transitions,
    )
    if request.method != "POST" or not form.is_valid():
        if request.method == "POST":
            messages.error(request, "Could not apply the requested status transition.")
        return redirect("change_management:request_detail", pk=pk)
    target_status = form.cleaned_data["target_status"]
    if not can_transition(request.user, change_request, target_status):
        raise PermissionDenied
    try:
        notes = form.cleaned_data["notes"]
        change_request.transition_to(
            new_status=target_status,
            actor=request.user,
            summary=notes or f"Status changed to {dict(ChangeRequest.STATUS_CHOICES)[target_status]}.",
        )
        if target_status == ChangeRequest.STATUS_IMPLEMENTED and notes:
            change_request.post_implementation_results = notes
            change_request.save(update_fields=["post_implementation_results", "updated_at"])
        messages.success(request, f"{change_request.change_id} moved to {dict(ChangeRequest.STATUS_CHOICES)[target_status]}.")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return redirect("change_management:request_detail", pk=pk)


@login_required
def add_comment(request, pk: int):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    form = ChangeCommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.change_request = change_request
        comment.author = request.user
        comment.save()
        ChangeActivity.record(
            change_request=change_request,
            actor=request.user,
            action=ChangeActivity.ACTION_COMMENT_ADDED,
            summary="Comment added.",
        )
    return redirect("change_management:request_detail", pk=pk)


@login_required
def add_evidence(request, pk: int):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    if not can_add_evidence(request.user, change_request):
        raise PermissionDenied
    form = ChangeEvidenceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        evidence = form.save(commit=False)
        evidence.change_request = change_request
        evidence.uploaded_by = request.user
        evidence.save()
        ChangeActivity.record(
            change_request=change_request,
            actor=request.user,
            action=ChangeActivity.ACTION_EVIDENCE_ADDED,
            summary=f"Evidence added: {evidence.title}.",
        )
        messages.success(request, "Evidence attached.")
    elif request.method == "POST":
        messages.error(request, "Evidence must include a title and either a file or an external URL.")
    return redirect("change_management:request_detail", pk=pk)


@login_required
def update_risk(request, pk: int):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    if not can_assess_risk(request.user):
        raise PermissionDenied
    risk_assessment, _ = ChangeRiskAssessment.objects.get_or_create(
        change_request=change_request,
        defaults={"residual_risk": change_request.risk_level},
    )
    form = ChangeRiskAssessmentForm(request.POST or None, instance=risk_assessment)
    if request.method == "POST" and form.is_valid():
        risk = form.save(commit=False)
        risk.change_request = change_request
        risk.assessed_by = request.user
        risk.assessed_at = timezone.now()
        risk.save()
        change_request.risk_level = risk.residual_risk
        change_request.save(update_fields=["risk_level", "updated_at"])
        ChangeActivity.record(
            change_request=change_request,
            actor=request.user,
            action=ChangeActivity.ACTION_UPDATED,
            summary="Risk assessment updated.",
        )
        messages.success(request, "Risk assessment saved.")
    elif request.method == "POST":
        messages.error(request, "Risk assessment could not be saved. Check the submitted fields.")
    return redirect("change_management:request_detail", pk=pk)
