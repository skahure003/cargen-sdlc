from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    ApprovalUserCreationForm,
    ApprovalDecisionForm,
    ChangeCommentForm,
    EmailApprovalConfirmForm,
    ChangeEvidenceForm,
    ChangeRequestForm,
    ChangeRiskAssessmentForm,
    StatusTransitionForm,
)
from .models import ApprovalStep, ChangeActivity, ChangeComment, ChangeEvidence, ChangeNotification, ChangeRequest, ChangeRiskAssessment, ChangeType
from .services.workflow import (
    can_add_evidence,
    can_assess_risk,
    can_edit_request,
    can_transition,
    can_view_request,
    create_change_request,
    decide_approval_step,
    has_any_group,
    has_group,
    pending_steps_for_user,
    read_email_approval_token,
    step_is_assigned_to_user,
    submit_change_request,
    transition_change_request,
    get_risk_assessment,
    update_change_request,
    update_risk as update_risk_workflow,
    visible_requests_for_user,
)


def render_access_denied(request, *, title: str, message: str, return_label: str):
    return render(
        request,
        "change_management/access_denied.html",
        {
            "page_title": title,
            "message": message,
            "return_label": return_label,
        },
        status=403,
    )


def dashboard(request):
    changes = ChangeRequest.objects.select_related("change_type", "requester").all()[:8]
    metrics = ChangeRequest.objects.aggregate(
        total=Count("id"),
        submitted=Count("id", filter=Q(status=ChangeRequest.STATUS_SUBMITTED)),
        approved=Count("id", filter=Q(status=ChangeRequest.STATUS_APPROVED)),
    )
    metrics["pending_approvals"] = ApprovalStep.objects.filter(status=ApprovalStep.STATUS_PENDING).count()
    queue_count = 0
    my_changes = []
    unread_notifications = []
    if request.user.is_authenticated:
        queue_count = len(pending_steps_for_user(request.user))
        my_changes = ChangeRequest.objects.filter(requester=request.user).select_related("change_type")[:6]
        unread_notifications = ChangeNotification.objects.filter(user=request.user, read_at__isnull=True)[:5]
    can_create_requests = (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or request.user.has_perm("change_management.submit_change")
            or has_group(request.user, "Requester")
        )
    )
    can_access_approval_queue = (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or has_any_group(request.user, ["Reviewer", "Approver", "Implementer", "Auditor/Admin"])
        )
    )
    can_manage_approval_users = (
        request.user.is_authenticated
        and (
            request.user.is_superuser
            or has_group(request.user, "Auditor/Admin")
        )
    )
    return render(
        request,
        "change_management/dashboard.html",
        {
            "changes": changes,
            "metrics": metrics,
            "queue_count": queue_count,
            "my_changes": my_changes,
            "change_types": ChangeType.objects.filter(is_active=True),
            "notifications": unread_notifications,
            "can_create_requests": can_create_requests,
            "can_access_approval_queue": can_access_approval_queue,
            "can_manage_approval_users": can_manage_approval_users,
        },
    )


@login_required
def approval_user_create(request):
    if not request.user.is_superuser and not has_group(request.user, "Auditor/Admin"):
        return render_access_denied(
            request,
            title="Admin Access Required",
            message="Only administrators can create approval users.",
            return_label="Back to dashboard",
        )
    if request.method == "POST":
        form = ApprovalUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Approval user {user.username} created.")
            return redirect("change_management:approval_user_create")
    else:
        form = ApprovalUserCreationForm()
    return render(
        request,
        "change_management/approval_user_form.html",
        {
            "form": form,
            "page_title": "Create approval user",
        },
    )


@login_required
def request_list(request):
    changes = visible_requests_for_user(request.user)
    can_create_requests = (
        request.user.is_superuser
        or request.user.has_perm("change_management.submit_change")
        or has_group(request.user, "Requester")
    )
    return render(
        request,
        "change_management/request_list.html",
        {"changes": changes, "can_create_requests": can_create_requests},
    )


@login_required
def request_create(request):
    can_create_requests = (
        request.user.is_superuser
        or request.user.has_perm("change_management.submit_change")
        or has_group(request.user, "Requester")
    )
    if not can_create_requests:
        return render_access_denied(
            request,
            title="Request Access Required",
            message="This page is for requesters. Approver-only accounts cannot create change requests.",
            return_label="Back to dashboard",
        )
    if request.method == "POST":
        form = ChangeRequestForm(request.POST)
        if form.is_valid():
            change_request = create_change_request(form.save(commit=False), request.user, form)
            messages.success(request, f"{change_request.change_id} created.")
            return redirect("change_management:request_detail", pk=change_request.pk)
    else:
        form = ChangeRequestForm()
    return render(
        request,
        "change_management/request_form.html",
        {"form": form, "page_title": "Create change request"},
    )


@login_required
def request_update(request, pk: int):
    change_request = get_object_or_404(ChangeRequest.objects.select_related("requester"), pk=pk)
    if not can_edit_request(request.user, change_request):
        raise PermissionDenied
    if request.method == "POST":
        form = ChangeRequestForm(request.POST, instance=change_request)
        if form.is_valid():
            change_request = update_change_request(change_request, request.user, form)
            messages.success(request, f"{change_request.change_id} updated.")
            return redirect("change_management:request_detail", pk=change_request.pk)
    else:
        form = ChangeRequestForm(instance=change_request)
    return render(
        request,
        "change_management/request_form.html",
        {
            "form": form,
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
    if not can_view_request(request.user, change_request):
        raise PermissionDenied
    risk_assessment = get_risk_assessment(change_request) or ChangeRiskAssessment(
        change_request=change_request,
        residual_risk=change_request.risk_level,
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
    ChangeNotification.objects.filter(user=request.user, change_request=change_request, read_at__isnull=True).update(read_at=timezone.now())
    return render(
        request,
        "change_management/request_detail.html",
        {
            "change_request": change_request,
            "comment_form": ChangeCommentForm(),
            "risk_form": ChangeRiskAssessmentForm(instance=risk_assessment),
            "transition_form": StatusTransitionForm(
                change_request=change_request,
                allowed_statuses=available_transitions,
            ),
            "decision_forms": decision_forms,
            "can_edit": can_edit_request(request.user, change_request),
            "can_assess_risk": can_assess_risk(request.user),
            "available_transitions": available_transitions,
        },
    )


@login_required
def submit_request(request, pk: int):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    if not can_transition(request.user, change_request, ChangeRequest.STATUS_SUBMITTED):
        raise PermissionDenied
    if change_request.status == ChangeRequest.STATUS_DRAFT:
        try:
            submit_change_request(change_request, request.user)
            messages.success(request, f"{change_request.change_id} submitted for approval.")
        except ValidationError as exc:
            messages.error(request, str(exc))
    return redirect("change_management:request_detail", pk=pk)


@login_required
def approval_queue(request):
    if not has_any_group(request.user, ["Reviewer", "Approver", "Implementer", "Auditor/Admin"]) and not request.user.is_superuser:
        return render_access_denied(
            request,
            title="Approval Access Required",
            message="This page is for approvers and implementation reviewers. Requester-only accounts cannot open the approval queue.",
            return_label="Back to dashboard",
        )
    return render(request, "change_management/approval_queue.html", {"steps": pending_steps_for_user(request.user)})


@login_required
def decide_step(request, pk: int):
    step = get_object_or_404(ApprovalStep.objects.select_related("change_request"), pk=pk)
    if not step_is_assigned_to_user(step, request.user) and not request.user.is_superuser:
        return render_access_denied(
            request,
            title="Approval Access Required",
            message="You are not assigned to this approval step, so you cannot record a decision here.",
            return_label="Back to dashboard",
        )
    form = ApprovalDecisionForm(request.POST or None, step=step)
    if request.method == "POST" and form.is_valid():
        try:
            decide_approval_step(step, request.user, form.cleaned_data["outcome"], form.cleaned_data["comments"])
            messages.success(request, "Approval recorded.")
        except ValidationError as exc:
            messages.error(request, str(exc))
    return redirect("change_management:request_detail", pk=step.change_request.pk)


@login_required
def email_approval_confirm(request, token: str):
    try:
        token_data = read_email_approval_token(token)
    except Exception:
        return render_access_denied(
            request,
            title="Approval Link Invalid",
            message="This approval link is invalid or has expired.",
            return_label="Back to dashboard",
        )
    step = get_object_or_404(ApprovalStep.objects.select_related("change_request", "assigned_user"), pk=token_data["step_id"])
    outcome = token_data["outcome"]
    if step.assigned_user_id != request.user.id and not request.user.is_superuser:
        return render_access_denied(
            request,
            title="Approval Link Restricted",
            message="This approval link was issued for a different user account.",
            return_label="Back to dashboard",
        )
    if step.status != ApprovalStep.STATUS_PENDING:
        return render_access_denied(
            request,
            title="Approval Already Recorded",
            message="This approval step is no longer pending.",
            return_label="Open request",
        )
    action_label = "Approve" if outcome == ApprovalStep.STATUS_APPROVED else "Reject"
    form = EmailApprovalConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            decide_approval_step(step, request.user, outcome, form.cleaned_data["comments"])
            messages.success(request, f"{step.change_request.change_id} {action_label.lower()}d from email confirmation.")
            return redirect("change_management:request_detail", pk=step.change_request.pk)
        except ValidationError as exc:
            messages.error(request, str(exc))
            return redirect("change_management:request_detail", pk=step.change_request.pk)
    return render(
        request,
        "change_management/email_approval_confirm.html",
        {
            "step": step,
            "change_request": step.change_request,
            "action_label": action_label,
            "form": form,
        },
    )


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
        transition_change_request(change_request, request.user, target_status, form.cleaned_data["notes"])
        messages.success(request, f"{change_request.change_id} moved to {dict(ChangeRequest.STATUS_CHOICES)[target_status]}.")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return redirect("change_management:request_detail", pk=pk)


@login_required
def add_comment(request, pk: int):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    if not can_view_request(request.user, change_request):
        raise PermissionDenied
    form = ChangeCommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = ChangeComment(
            change_request=change_request,
            author=request.user,
            comment=form.cleaned_data["comment"],
        )
        comment.save()
        ChangeActivity.record(
            change_request=change_request,
            actor=request.user,
            action=ChangeActivity.ACTION_COMMENT_ADDED,
            summary="Comment added.",
        )
        messages.success(request, "Comment added.")
    return redirect("change_management:request_detail", pk=pk)


@login_required
def add_evidence(request, pk: int):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    if not can_add_evidence(request.user, change_request):
        raise PermissionDenied
    form = ChangeEvidenceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        evidence = ChangeEvidence(
            change_request=change_request,
            uploaded_by=request.user,
            **form.cleaned_data,
        )
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
    risk_assessment = get_risk_assessment(change_request) or ChangeRiskAssessment(
        change_request=change_request,
        residual_risk=change_request.risk_level,
    )
    form = ChangeRiskAssessmentForm(request.POST or None, instance=risk_assessment)
    if request.method == "POST" and form.is_valid():
        try:
            update_risk_workflow(change_request, form.save(commit=False), request.user)
            messages.success(request, "Risk assessment saved.")
        except ValidationError as exc:
            messages.error(request, str(exc))
    elif request.method == "POST":
        messages.error(request, "Risk assessment could not be saved. Check the submitted fields.")
    return redirect("change_management:request_detail", pk=pk)
