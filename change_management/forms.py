from django import forms
from django.forms import inlineformset_factory

from .models import (
    ApprovalStep,
    ChangeComment,
    ChangeEvidence,
    ChangeRequest,
    ChangeRiskAssessment,
    ImplementationTask,
)


class ChangeRequestForm(forms.ModelForm):
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
        widgets = {
            "planned_start": forms.DateTimeInput(
                attrs={"type": "datetime-local", "placeholder": "Select the planned implementation start time."}
            ),
            "planned_end": forms.DateTimeInput(
                attrs={"type": "datetime-local", "placeholder": "Select the planned implementation end time."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["business_justification"].label = "Reason for change"
        self.fields["change_type"].queryset = self.fields["change_type"].queryset.filter(slug__in=["major", "minor"])
        self.fields["risk_level"].choices = [
            (ChangeRequest.RISK_LOW, "Low"),
            (ChangeRequest.RISK_HIGH, "High"),
            (ChangeRequest.RISK_CRITICAL, "Critical"),
        ]
        for field_name, placeholder in self.PLACEHOLDERS.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["placeholder"] = placeholder


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


ImplementationTaskFormSet = inlineformset_factory(
    ChangeRequest,
    ImplementationTask,
    fields=["title"],
    extra=1,
    max_num=1,
    validate_max=True,
    can_delete=False,
)
