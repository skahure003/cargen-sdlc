from django.contrib.auth import get_user_model
from django import forms
from django.utils import timezone

from .models import (
    ApprovalStep,
    ChangeComment,
    ChangeEvidence,
    ChangeRequest,
    ChangeRiskAssessment,
)


class ChangeRequestForm(forms.ModelForm):
    planned_start = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "Select the planned implementation start date."}),
    )
    planned_end = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "Select the planned implementation end date."}),
    )
    process_owner_approver = forms.ModelChoiceField(queryset=None, required=True, label="Process Owner approval")
    business_owner_approver = forms.ModelChoiceField(queryset=None, required=True, label="Business Owner approval")
    head_of_it_approver = forms.ModelChoiceField(queryset=None, required=True, label="Head of IT approval")
    implementation_acknowledger = forms.ModelChoiceField(queryset=None, required=True, label="IT Implementation acknowledgement")

    PLACEHOLDERS = {
        "title": "Summarize the planned change in one clear line.",
        "department": "Select or enter the requesting department.",
        "system_or_application": "State the system, application, or module affected by this change.",
        "business_justification": "Explain why the change is required and the business or operational need it addresses.",
        "business_impact": "Describe the expected business impact, service effect, or operational outcome of the change.",
        "implementation_plan": "Describe the implementation steps in execution order, including owners and prerequisites.",
        "test_validation_plan": "Describe how the change will be tested and what evidence will confirm success.",
        "rollback_plan": "Describe how the change will be reversed safely if validation fails.",
        "security_impact": "Capture any security implications, control changes, or risk introduced by this change.",
    }

    class Meta:
        model = ChangeRequest
        fields = [
            "title",
            "department",
            "system_or_application",
            "change_type",
            "risk_level",
            "business_justification",
            "business_impact",
            "implementation_plan",
            "test_validation_plan",
            "rollback_plan",
            "planned_start",
            "planned_end",
            "security_impact",
        ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["process_owner_approver"].queryset = User.objects.filter(groups__name="Reviewer").distinct().order_by("username")
        self.fields["business_owner_approver"].queryset = User.objects.filter(groups__name="Approver").distinct().order_by("username")
        self.fields["head_of_it_approver"].queryset = User.objects.filter(groups__name="Auditor/Admin").distinct().order_by("username")
        self.fields["implementation_acknowledger"].queryset = User.objects.filter(groups__name="Implementer").distinct().order_by("username")
        self.fields["business_justification"].label = "Reason for change"
        self.fields["change_type"].queryset = self.fields["change_type"].queryset.filter(slug__in=["major", "minor"])
        self.fields["risk_level"].choices = [
            (ChangeRequest.RISK_LOW, "Low"),
            (ChangeRequest.RISK_HIGH, "High"),
            (ChangeRequest.RISK_CRITICAL, "Critical"),
        ]
        self.order_fields(
            [
                "title",
                "department",
                "system_or_application",
                "change_type",
                "risk_level",
                "process_owner_approver",
                "business_owner_approver",
                "head_of_it_approver",
                "implementation_acknowledger",
                "business_justification",
                "business_impact",
                "implementation_plan",
                "test_validation_plan",
                "rollback_plan",
                "planned_start",
                "planned_end",
                "security_impact",
            ]
        )
        for field_name, placeholder in self.PLACEHOLDERS.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["placeholder"] = placeholder
        if self.instance.pk:
            approvals_by_name = {step.name: step.assigned_user for step in self.instance.approval_steps.select_related("assigned_user")}
            self.fields["process_owner_approver"].initial = approvals_by_name.get("Process Owner Approval")
            self.fields["business_owner_approver"].initial = approvals_by_name.get("Business Owner Approval")
            self.fields["head_of_it_approver"].initial = approvals_by_name.get("Head of IT Approval")
            self.fields["implementation_acknowledger"].initial = approvals_by_name.get("IT Implementation Acknowledgement")

    def clean_planned_start(self):
        planned_start = self.cleaned_data.get("planned_start")
        if planned_start:
            planned_start = timezone.make_aware(timezone.datetime.combine(planned_start, timezone.datetime.min.time()))
        return planned_start

    def clean_planned_end(self):
        planned_end = self.cleaned_data.get("planned_end")
        if planned_end:
            planned_end = timezone.make_aware(timezone.datetime.combine(planned_end, timezone.datetime.min.time()))
        return planned_end


class ChangeRiskAssessmentForm(forms.ModelForm):
    class Meta:
        model = ChangeRiskAssessment
        fields = ["impact_summary", "likelihood_summary", "residual_risk"]


class ApprovalDecisionForm(forms.Form):
    outcome = forms.ChoiceField(
        choices=[
            (ApprovalStep.STATUS_APPROVED, "Approve"),
            (ApprovalStep.STATUS_REJECTED, "Reject"),
        ]
    )
    comments = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def __init__(self, *args, step=None, **kwargs):
        self.step = step
        super().__init__(*args, **kwargs)


class EmailApprovalConfirmForm(forms.Form):
    comments = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Optional approval note.",
            }
        ),
        required=False,
    )


class StatusTransitionForm(forms.Form):
    target_status = forms.ChoiceField(choices=[])
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def __init__(self, *args, change_request=None, allowed_statuses=None, **kwargs):
        self.change_request = change_request
        super().__init__(*args, **kwargs)
        if change_request:
            allowed_statuses = list(allowed_statuses or change_request.TRANSITIONS.get(change_request.status, set()))
            self.fields["target_status"].choices = [
                (status, dict(ChangeRequest.STATUS_CHOICES)[status])
                for status in allowed_statuses
            ]


class ChangeCommentForm(forms.ModelForm):
    class Meta:
        model = ChangeComment
        fields = ["comment"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Add implementation notes, reviewer observations, or follow-ups.",
                }
            )
        }


class ChangeEvidenceForm(forms.ModelForm):
    class Meta:
        model = ChangeEvidence
        fields = ["evidence_type", "title", "description", "file", "external_url"]
