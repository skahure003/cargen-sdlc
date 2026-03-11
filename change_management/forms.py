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
        "business_justification": "Explain why this change is needed, what risk or business outcome it addresses, and why now.",
        "affected_services": "List the systems, services, teams, or business capabilities that will be affected.",
        "implementation_plan": "Describe the implementation steps in execution order, including owners and prerequisites.",
        "test_validation_plan": "Describe how the change will be tested and what evidence will confirm success.",
        "rollback_plan": "Describe how the change will be reversed safely if validation fails.",
        "outage_impact": "State any expected downtime, degraded service, customer impact, or communication requirements.",
        "security_impact": "Capture any security implications, control changes, or risk introduced by this change.",
        "privacy_impact": "Note whether personal data, access patterns, or data flows are affected.",
        "compliance_impact": "Document any policy, regulatory, audit, or governance considerations.",
        "linked_items": "Reference related tickets, repositories, release IDs, deployment jobs, or CAB records.",
        "post_implementation_results": "After implementation, record the outcome, validation evidence, incidents, or follow-up actions.",
    }

    class Meta:
        model = ChangeRequest
        fields = [
            "title",
            "change_type",
            "template",
            "risk_level",
            "business_justification",
            "affected_services",
            "implementation_plan",
            "test_validation_plan",
            "rollback_plan",
            "planned_start",
            "planned_end",
            "outage_impact",
            "security_impact",
            "privacy_impact",
            "compliance_impact",
            "linked_items",
            "post_implementation_results",
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
        for field_name, placeholder in self.PLACEHOLDERS.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["placeholder"] = placeholder


class ChangeRiskAssessmentForm(forms.ModelForm):
    class Meta:
        model = ChangeRiskAssessment
        fields = ["impact_summary", "likelihood_summary", "residual_risk", "cab_review_required"]


class ApprovalDecisionForm(forms.Form):
    outcome = forms.ChoiceField(
        choices=[
            (ApprovalStep.STATUS_APPROVED, "Approve"),
            (ApprovalStep.STATUS_REJECTED, "Reject"),
            (ApprovalStep.STATUS_SKIPPED, "Skip"),
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
    fields=["title", "description", "sequence", "owner", "status", "due_at"],
    extra=1,
    can_delete=True,
    widgets={"due_at": forms.DateTimeInput(attrs={"type": "datetime-local"})},
)
