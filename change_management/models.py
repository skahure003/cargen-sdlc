from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify


class ImmutableAuditModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(f"{self.__class__.__name__} records are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(f"{self.__class__.__name__} records cannot be deleted.")


class ChangeType(models.Model):
    APPROVAL_SEQUENTIAL = "sequential"
    APPROVAL_PARALLEL = "parallel"
    APPROVAL_MODE_CHOICES = [
        (APPROVAL_SEQUENTIAL, "Sequential"),
        (APPROVAL_PARALLEL, "Parallel"),
    ]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_preapproved = models.BooleanField(default=False)
    requires_retro_review = models.BooleanField(default=False)
    default_approval_mode = models.CharField(
        max_length=20,
        choices=APPROVAL_MODE_CHOICES,
        default=APPROVAL_SEQUENTIAL,
    )
    default_implementation_window_hours = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ChangeTemplate(models.Model):
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(unique=True)
    change_type = models.ForeignKey(ChangeType, on_delete=models.PROTECT, related_name="templates")
    description = models.TextField(blank=True)
    implementation_plan_template = models.TextField(blank=True)
    test_plan_template = models.TextField(blank=True)
    rollback_plan_template = models.TextField(blank=True)
    security_guidance = models.TextField(blank=True)
    compliance_guidance = models.TextField(blank=True)
    default_risk_level = models.CharField(max_length=20, blank=True)
    default_outage_impact = models.TextField(blank=True)
    default_approval_steps = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ChangeRequest(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_IN_REVIEW = "in_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_SCHEDULED = "scheduled"
    STATUS_IMPLEMENTED = "implemented"
    STATUS_VALIDATED = "validated"
    STATUS_CLOSED = "closed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_IN_REVIEW, "In Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_IMPLEMENTED, "Implemented"),
        (STATUS_VALIDATED, "Validated"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    RISK_LOW = "low"
    RISK_HIGH = "high"
    RISK_CRITICAL = "critical"
    RISK_CHOICES = [
        (RISK_LOW, "Low"),
        (RISK_HIGH, "High"),
        (RISK_CRITICAL, "Critical"),
    ]

    CHANGE_ID_PREFIX = "CHG"

    change_id = models.CharField(max_length=32, unique=True, blank=True)
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=160, blank=True)
    system_or_application = models.CharField(max_length=200, blank=True)
    business_justification = models.TextField(verbose_name="Reason for change")
    business_impact = models.TextField(blank=True)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_changes",
    )
    change_type = models.ForeignKey(ChangeType, on_delete=models.PROTECT, related_name="requests")
    template = models.ForeignKey(
        ChangeTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requests",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default=RISK_LOW)
    affected_services = models.TextField(help_text="Systems, services, or business capabilities impacted.")
    implementation_plan = models.TextField()
    test_validation_plan = models.TextField()
    rollback_plan = models.TextField()
    planned_start = models.DateTimeField(null=True, blank=True)
    planned_end = models.DateTimeField(null=True, blank=True)
    outage_impact = models.TextField(blank=True)
    security_impact = models.TextField(blank=True)
    compliance_impact = models.TextField(blank=True)
    linked_items = models.TextField(blank=True, help_text="Tickets, repositories, releases, deployments.")
    post_implementation_results = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    implemented_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    TRANSITIONS = {
        STATUS_DRAFT: {STATUS_SUBMITTED, STATUS_CANCELLED},
        STATUS_SUBMITTED: {STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED},
        STATUS_IN_REVIEW: {STATUS_APPROVED, STATUS_REJECTED, STATUS_CANCELLED},
        STATUS_APPROVED: {STATUS_SCHEDULED, STATUS_CANCELLED},
        STATUS_REJECTED: {STATUS_DRAFT, STATUS_CANCELLED},
        STATUS_SCHEDULED: {STATUS_IMPLEMENTED, STATUS_CANCELLED},
        STATUS_IMPLEMENTED: {STATUS_VALIDATED, STATUS_CANCELLED},
        STATUS_VALIDATED: {STATUS_CLOSED, STATUS_CANCELLED},
        STATUS_CLOSED: set(),
        STATUS_CANCELLED: set(),
    }

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("submit_change", "Can submit change requests"),
            ("review_change", "Can review change requests"),
            ("approve_change", "Can approve change requests"),
            ("implement_change", "Can implement approved changes"),
            ("audit_change", "Can audit change requests"),
        ]

    def __str__(self):
        return self.change_id or self.title

    def clean(self):
        if self.planned_start and self.planned_end and self.planned_end <= self.planned_start:
            raise ValidationError("Planned end must be after planned start.")

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating and not self.change_id:
            self.change_id = f"{self.CHANGE_ID_PREFIX}-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(change_id=self.change_id)

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.TRANSITIONS.get(self.status, set())

    def transition_to(self, *, new_status: str, actor, summary: str = "", metadata: dict | None = None):
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Cannot move from {self.status} to {new_status}.")
        previous_status = self.status
        previous_display = self.get_status_display()
        now = timezone.now()
        self.status = new_status
        if new_status == self.STATUS_SUBMITTED and not self.submitted_at:
            self.submitted_at = now
        if new_status == self.STATUS_APPROVED and not self.approved_at:
            self.approved_at = now
        if new_status == self.STATUS_SCHEDULED and not self.scheduled_at:
            self.scheduled_at = now
        if new_status == self.STATUS_IMPLEMENTED and not self.implemented_at:
            self.implemented_at = now
        if new_status == self.STATUS_VALIDATED and not self.validated_at:
            self.validated_at = now
        if new_status == self.STATUS_CLOSED and not self.closed_at:
            self.closed_at = now
        if new_status == self.STATUS_CANCELLED and not self.cancelled_at:
            self.cancelled_at = now
        self.save()
        ChangeActivity.record(
            change_request=self,
            actor=actor,
            action=ChangeActivity.ACTION_STATUS_CHANGED,
            from_status=previous_status,
            to_status=new_status,
            summary=summary or f"Status changed from {previous_display} to {self.get_status_display()}.",
            metadata=metadata or {},
        )


class ChangeRiskAssessment(models.Model):
    change_request = models.OneToOneField(
        ChangeRequest,
        on_delete=models.CASCADE,
        related_name="risk_assessment",
    )
    impact_summary = models.TextField(blank=True)
    likelihood_summary = models.TextField(blank=True)
    residual_risk = models.CharField(max_length=20, choices=ChangeRequest.RISK_CHOICES)
    cab_review_required = models.BooleanField(default=False)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_assessments",
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Risk for {self.change_request}"


class ApprovalStep(models.Model):
    ROLE_REQUESTER = "requester"
    ROLE_REVIEWER = "reviewer"
    ROLE_APPROVER = "approver"
    ROLE_IMPLEMENTER = "implementer"
    ROLE_AUDITOR = "auditor"
    ROLE_CAB = "cab"
    ROLE_CHOICES = [
        (ROLE_REQUESTER, "Requester"),
        (ROLE_REVIEWER, "Reviewer"),
        (ROLE_APPROVER, "Approver"),
        (ROLE_IMPLEMENTER, "Implementer"),
        (ROLE_AUDITOR, "Auditor"),
        (ROLE_CAB, "CAB"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="approval_steps")
    name = models.CharField(max_length=160)
    sequence = models.PositiveIntegerField(default=1)
    assigned_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_REVIEWER)
    assigned_group = models.CharField(max_length=160, blank=True)
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_approval_steps",
    )
    required = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sequence", "pk"]
        unique_together = [("change_request", "sequence", "name")]

    def __str__(self):
        return f"{self.change_request} - {self.name}"

    def is_unblocked(self) -> bool:
        if self.change_request.change_type.default_approval_mode != ChangeType.APPROVAL_SEQUENTIAL:
            return True
        previous_required_steps = self.change_request.approval_steps.filter(
            sequence__lt=self.sequence,
            required=True,
        ).exclude(status__in=[self.STATUS_APPROVED, self.STATUS_SKIPPED])
        return not previous_required_steps.exists()

    def is_waiting_for(self, user) -> bool:
        if self.status != self.STATUS_PENDING or not user.is_authenticated:
            return False
        if not self.is_unblocked():
            return False
        if self.assigned_user_id == user.id:
            return True
        groups = set(user.groups.values_list("name", flat=True))
        if self.assigned_group and self.assigned_group in groups:
            return True
        role_group_names = {
            self.ROLE_REVIEWER: "Reviewer",
            self.ROLE_APPROVER: "Approver",
            self.ROLE_IMPLEMENTER: "Implementer",
            self.ROLE_AUDITOR: "Auditor/Admin",
            self.ROLE_CAB: "CAB",
            self.ROLE_REQUESTER: "Requester",
        }
        return role_group_names.get(self.assigned_role) in groups

    def decide(self, *, actor, outcome: str, comments: str = ""):
        if self.status != self.STATUS_PENDING:
            raise ValidationError("This approval step has already been decided.")
        if not self.is_unblocked():
            raise ValidationError("This approval step is blocked by an earlier required decision.")
        if outcome not in {self.STATUS_APPROVED, self.STATUS_REJECTED, self.STATUS_SKIPPED}:
            raise ValidationError("Unsupported approval outcome.")
        now = timezone.now()
        self.status = outcome
        self.decided_at = now
        self.decision_notes = comments
        self.save(update_fields=["status", "decided_at", "decision_notes", "updated_at"])
        ApprovalDecision.objects.create(
            change_request=self.change_request,
            approval_step=self,
            decided_by=actor,
            outcome=outcome,
            comments=comments,
        )
        ChangeActivity.record(
            change_request=self.change_request,
            actor=actor,
            action=ChangeActivity.ACTION_APPROVAL_DECIDED,
            summary=f"{self.name} marked as {outcome.replace('_', ' ')}.",
            metadata={"step": self.name, "outcome": outcome},
        )


class ApprovalDecision(ImmutableAuditModel):
    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="approval_decisions")
    approval_step = models.ForeignKey(ApprovalStep, on_delete=models.PROTECT, related_name="decisions")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_decisions",
    )
    outcome = models.CharField(max_length=20, choices=ApprovalStep.STATUS_CHOICES)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.change_request} - {self.outcome}"


class ImplementationTask(models.Model):
    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_BLOCKED = "blocked"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_DONE, "Done"),
        (STATUS_BLOCKED, "Blocked"),
    ]

    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="implementation_tasks")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sequence = models.PositiveIntegerField(default=1)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="implementation_tasks",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sequence", "pk"]

    def __str__(self):
        return self.title


class ChangeEvidence(models.Model):
    TYPE_FILE = "file"
    TYPE_LINK = "link"
    TYPE_SCREENSHOT = "screenshot"
    TYPE_TEST_RESULT = "test_result"
    TYPE_CHOICES = [
        (TYPE_FILE, "File"),
        (TYPE_LINK, "Link"),
        (TYPE_SCREENSHOT, "Screenshot"),
        (TYPE_TEST_RESULT, "Test Result"),
    ]

    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="evidence")
    evidence_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_FILE)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="change_evidence/", blank=True)
    external_url = models.URLField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_change_evidence",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if not self.file and not self.external_url:
            raise ValidationError("Provide either a file or an external URL.")

    def __str__(self):
        return self.title


class ChangeComment(models.Model):
    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="change_comments",
    )
    comment = models.TextField()
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.change_request}"


class ChangeActivity(ImmutableAuditModel):
    ACTION_CREATED = "created"
    ACTION_STATUS_CHANGED = "status_changed"
    ACTION_SUBMITTED = "submitted"
    ACTION_APPROVAL_DECIDED = "approval_decided"
    ACTION_COMMENT_ADDED = "comment_added"
    ACTION_EVIDENCE_ADDED = "evidence_added"
    ACTION_UPDATED = "updated"

    ACTION_CHOICES = [
        (ACTION_CREATED, "Created"),
        (ACTION_STATUS_CHANGED, "Status Changed"),
        (ACTION_SUBMITTED, "Submitted"),
        (ACTION_APPROVAL_DECIDED, "Approval Decided"),
        (ACTION_COMMENT_ADDED, "Comment Added"),
        (ACTION_EVIDENCE_ADDED, "Evidence Added"),
        (ACTION_UPDATED, "Updated"),
    ]

    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="activity")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="change_activity",
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    from_status = models.CharField(max_length=20, choices=ChangeRequest.STATUS_CHOICES, blank=True)
    to_status = models.CharField(max_length=20, choices=ChangeRequest.STATUS_CHOICES, blank=True)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def record(
        cls,
        *,
        change_request: ChangeRequest,
        actor,
        action: str,
        summary: str,
        metadata: dict | None = None,
        from_status: str = "",
        to_status: str = "",
    ):
        return cls.objects.create(
            change_request=change_request,
            actor=actor,
            action=action,
            from_status=from_status,
            to_status=to_status,
            summary=summary,
            metadata=metadata or {},
        )

    def __str__(self):
        return f"{self.change_request} - {self.summary}"


class ChangeNotification(models.Model):
    CATEGORY_SUBMISSION = "submission"
    CATEGORY_APPROVAL = "approval"
    CATEGORY_REJECTION = "rejection"
    CATEGORY_SCHEDULE = "schedule"
    CATEGORY_CHOICES = [
        (CATEGORY_SUBMISSION, "Submission"),
        (CATEGORY_APPROVAL, "Approval"),
        (CATEGORY_REJECTION, "Rejection"),
        (CATEGORY_SCHEDULE, "Schedule"),
    ]

    change_request = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name="notifications")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="change_notifications",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    message = models.CharField(max_length=255)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.message}"


def default_approval_blueprint(change_type: ChangeType, risk_level: str) -> list[dict]:
    return [
        {
            "name": "Process Owner Approval",
            "sequence": 1,
            "assigned_role": ApprovalStep.ROLE_REVIEWER,
            "assigned_group": "Reviewer",
        },
        {
            "name": "Business Owner Approval",
            "sequence": 2,
            "assigned_role": ApprovalStep.ROLE_APPROVER,
            "assigned_group": "Approver",
        },
        {
            "name": "Head of IT Approval",
            "sequence": 3,
            "assigned_role": ApprovalStep.ROLE_AUDITOR,
            "assigned_group": "Auditor/Admin",
        },
        {
            "name": "IT Implementation Acknowledgement",
            "sequence": 4,
            "assigned_role": ApprovalStep.ROLE_IMPLEMENTER,
            "assigned_group": "Implementer",
        },
    ]


@transaction.atomic
def initialize_workflow(change_request: ChangeRequest):
    if change_request.approval_steps.exists():
        return
    blueprint = default_approval_blueprint(change_request.change_type, change_request.risk_level)
    for item in blueprint:
        role = item.get("assigned_role", ApprovalStep.ROLE_APPROVER)
        default_group = {
            ApprovalStep.ROLE_REQUESTER: "Requester",
            ApprovalStep.ROLE_REVIEWER: "Reviewer",
            ApprovalStep.ROLE_APPROVER: "Approver",
            ApprovalStep.ROLE_IMPLEMENTER: "Implementer",
            ApprovalStep.ROLE_AUDITOR: "Auditor/Admin",
            ApprovalStep.ROLE_CAB: "CAB",
        }.get(role, "")
        ApprovalStep.objects.create(
            change_request=change_request,
            name=item["name"],
            sequence=item["sequence"],
            assigned_role=role,
            assigned_group=item.get("assigned_group", default_group),
            required=item.get("required", True),
        )
