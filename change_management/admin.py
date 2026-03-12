from django.contrib import admin

from .models import (
    ApprovalDecision,
    ApprovalStep,
    ChangeActivity,
    ChangeComment,
    ChangeEvidence,
    ChangeNotification,
    ChangeRequest,
    ChangeRiskAssessment,
    ChangeTemplate,
    ChangeType,
    ImplementationTask,
)


class ApprovalStepInline(admin.TabularInline):
    model = ApprovalStep
    extra = 0


class ImplementationTaskInline(admin.TabularInline):
    model = ImplementationTask
    extra = 0


class ChangeEvidenceInline(admin.TabularInline):
    model = ChangeEvidence
    extra = 0


class ChangeCommentInline(admin.TabularInline):
    model = ChangeComment
    extra = 0


@admin.register(ChangeType)
class ChangeTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_preapproved", "requires_retro_review", "is_active")
    list_filter = ("is_active", "is_preapproved", "requires_retro_review")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ChangeTemplate)
class ChangeTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "change_type", "is_active", "updated_at")
    list_filter = ("change_type", "is_active")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("change_id", "title", "change_type", "status", "risk_level", "requester", "planned_start")
    list_filter = ("status", "risk_level", "change_type")
    search_fields = ("change_id", "title", "business_justification", "affected_services")
    readonly_fields = (
        "change_id",
        "submitted_at",
        "approved_at",
        "scheduled_at",
        "implemented_at",
        "validated_at",
        "closed_at",
        "cancelled_at",
        "created_at",
        "updated_at",
    )
    inlines = [ApprovalStepInline, ImplementationTaskInline, ChangeEvidenceInline, ChangeCommentInline]


@admin.register(ChangeRiskAssessment)
class ChangeRiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ("change_request", "residual_risk", "cab_review_required", "assessed_by", "assessed_at")
    list_filter = ("residual_risk", "cab_review_required")
    search_fields = ("change_request__change_id", "change_request__title")


@admin.register(ApprovalDecision)
class ApprovalDecisionAdmin(admin.ModelAdmin):
    list_display = ("change_request", "approval_step", "outcome", "decided_by", "created_at")
    list_filter = ("outcome",)
    search_fields = ("change_request__change_id", "approval_step__name", "comments")
    readonly_fields = ("created_at",)


@admin.register(ChangeActivity)
class ChangeActivityAdmin(admin.ModelAdmin):
    list_display = ("change_request", "action", "actor", "summary", "created_at")
    list_filter = ("action",)
    search_fields = ("change_request__change_id", "summary")
    readonly_fields = ("created_at",)


@admin.register(ChangeEvidence)
class ChangeEvidenceAdmin(admin.ModelAdmin):
    list_display = ("change_request", "title", "evidence_type", "uploaded_by", "created_at")
    list_filter = ("evidence_type",)
    search_fields = ("change_request__change_id", "title", "description")


@admin.register(ChangeComment)
class ChangeCommentAdmin(admin.ModelAdmin):
    list_display = ("change_request", "author", "is_system", "created_at")
    list_filter = ("is_system",)
    search_fields = ("change_request__change_id", "comment")


@admin.register(ChangeNotification)
class ChangeNotificationAdmin(admin.ModelAdmin):
    list_display = ("change_request", "user", "category", "message", "read_at", "created_at")
    list_filter = ("category", "read_at")
    search_fields = ("change_request__change_id", "user__username", "message")
    readonly_fields = ("created_at",)
