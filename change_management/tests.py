from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import ApprovalStep, ChangeRequest, ChangeType


class ChangeManagementSmokeTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username="requester", password="pass12345")
        self.requester.groups.add(Group.objects.get(name="Requester"))
        self.reviewer = User.objects.create_user(username="reviewer", password="pass12345")
        self.reviewer.groups.add(Group.objects.get(name="Reviewer"))
        self.approver = User.objects.create_user(username="approver", password="pass12345")
        self.approver.groups.add(Group.objects.get(name="Approver"))
        self.change_type = ChangeType.objects.get(slug="normal")

    def test_dashboard_loads(self):
        response = self.client.get(reverse("change_management:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_policy_page_loads(self):
        response = self.client.get(reverse("policy"))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_requester_can_create_change_request(self):
        self.client.login(username="requester", password="pass12345")
        response = self.client.post(
            reverse("change_management:request_create"),
            {
                "title": "Deploy release 2026.03.11",
                "change_type": self.change_type.pk,
                "template": "",
                "risk_level": ChangeRequest.RISK_MEDIUM,
                "business_justification": "Required for planned release.",
                "affected_services": "Customer API and reporting worker.",
                "implementation_plan": "Deploy the application and verify health checks.",
                "test_validation_plan": "Run smoke tests and verify dashboards.",
                "rollback_plan": "Rollback to previous container image.",
                "planned_start": "",
                "planned_end": "",
                "outage_impact": "Brief restart only.",
                "security_impact": "No material change.",
                "privacy_impact": "No privacy data change.",
                "compliance_impact": "No compliance impact.",
                "linked_items": "JIRA-101, release/2026.03.11",
                "post_implementation_results": "",
                "tasks-TOTAL_FORMS": "1",
                "tasks-INITIAL_FORMS": "0",
                "tasks-MIN_NUM_FORMS": "0",
                "tasks-MAX_NUM_FORMS": "1000",
                "tasks-0-title": "Deploy application",
                "tasks-0-description": "Apply release artifact.",
                "tasks-0-sequence": "1",
                "tasks-0-owner": "",
                "tasks-0-status": "pending",
                "tasks-0-due_at": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        change_request = ChangeRequest.objects.get(title="Deploy release 2026.03.11")
        self.assertTrue(change_request.change_id.startswith("CHG-"))
        self.assertEqual(change_request.approval_steps.count(), 2)

    def test_requester_cannot_add_evidence_to_other_users_change(self):
        other_requester = User.objects.create_user(username="requester_two", password="pass12345")
        other_requester.groups.add(Group.objects.get(name="Requester"))
        change_request = ChangeRequest.objects.create(
            title="Infra restart",
            business_justification="Routine restart.",
            requester=other_requester,
            change_type=self.change_type,
            risk_level=ChangeRequest.RISK_LOW,
            affected_services="Background jobs",
            implementation_plan="Restart the worker pool.",
            test_validation_plan="Check queue drain.",
            rollback_plan="Restart previous worker version.",
        )
        self.client.login(username="requester", password="pass12345")
        response = self.client.post(
            reverse("change_management:add_evidence", args=[change_request.pk]),
            {
                "evidence_type": "link",
                "title": "Release notes",
                "description": "Notes",
                "external_url": "https://example.com/release",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_approval_step_can_approve_request(self):
        change_request = ChangeRequest.objects.create(
            title="Database patch",
            business_justification="Critical fix.",
            requester=self.requester,
            change_type=self.change_type,
            risk_level=ChangeRequest.RISK_MEDIUM,
            affected_services="Primary database",
            implementation_plan="Apply patch",
            test_validation_plan="Run validation query",
            rollback_plan="Restore snapshot",
            status=ChangeRequest.STATUS_IN_REVIEW,
        )
        step = ApprovalStep.objects.create(
            change_request=change_request,
            name="Change Approval",
            sequence=1,
            assigned_role=ApprovalStep.ROLE_APPROVER,
        )
        self.client.login(username="approver", password="pass12345")
        response = self.client.post(
            reverse("change_management:decide_step", args=[step.pk]),
            {"outcome": ApprovalStep.STATUS_APPROVED, "comments": "Approved for execution."},
        )
        self.assertEqual(response.status_code, 302)
        change_request.refresh_from_db()
        step.refresh_from_db()
        self.assertEqual(step.status, ApprovalStep.STATUS_APPROVED)
        self.assertEqual(change_request.status, ChangeRequest.STATUS_APPROVED)
