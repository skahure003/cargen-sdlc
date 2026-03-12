from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.content import load_site_content

from .models import ApprovalStep, ChangeRequest, ChangeType


class ChangeManagementSmokeTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username="requester", password="pass12345")
        self.requester.groups.add(Group.objects.get(name="Requester"))
        self.approver = User.objects.create_user(username="approver", password="pass12345")
        self.approver.groups.add(Group.objects.get(name="Approver"))
        self.implementer = User.objects.create_user(username="implementer", password="pass12345")
        self.implementer.groups.add(Group.objects.get(name="Implementer"))
        self.auditor = User.objects.create_user(username="auditor", password="pass12345")
        self.auditor.groups.add(Group.objects.get(name="Auditor/Admin"))
        self.change_type = ChangeType.objects.get(slug="normal")

    def test_dashboard_loads(self):
        response = self.client.get(reverse("change_management:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_policy_page_loads(self):
        response = self.client.get(reverse("policy"))
        self.assertEqual(response.status_code, 200)

    def test_index_pages_do_not_duplicate_top_level_heading(self):
        load_site_content.cache_clear()
        data = load_site_content()
        self.assertNotIn("<h1>Risks</h1>", data["pages"]["risks_index"]["body_html"])
        self.assertNotIn("<h1>Controls", data["pages"]["controls_index"]["body_html"])

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_registration_page_loads(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/register.html")

    def test_registration_creates_requester_and_redirects_to_change_management(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new_requester",
                "email": "new_requester@example.local",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/changes/")
        user = User.objects.get(username="new_requester")
        self.assertEqual(user.email, "new_requester@example.local")
        self.assertTrue(user.groups.filter(name="Requester").exists())

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
        self.assertEqual(change_request.approval_steps.count(), 1)
        self.assertEqual(change_request.approval_steps.first().assigned_role, ApprovalStep.ROLE_APPROVER)

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

    def test_requester_only_sees_own_requests(self):
        other_requester = User.objects.create_user(username="requester_three", password="pass12345")
        other_requester.groups.add(Group.objects.get(name="Requester"))
        own_request = ChangeRequest.objects.create(
            title="Own change",
            business_justification="Own record.",
            requester=self.requester,
            change_type=self.change_type,
            affected_services="API",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
        )
        other_request = ChangeRequest.objects.create(
            title="Other change",
            business_justification="Other record.",
            requester=other_requester,
            change_type=self.change_type,
            affected_services="Worker",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
        )
        self.client.login(username="requester", password="pass12345")
        list_response = self.client.get(reverse("change_management:request_list"))
        self.assertContains(list_response, own_request.title)
        self.assertNotContains(list_response, other_request.title)
        detail_response = self.client.get(reverse("change_management:request_detail", args=[other_request.pk]))
        self.assertEqual(detail_response.status_code, 403)

    def test_non_assigned_user_cannot_view_approver_owned_request(self):
        change_request = ChangeRequest.objects.create(
            title="Approver owned request",
            business_justification="Approval only",
            requester=self.requester,
            change_type=self.change_type,
            affected_services="Billing",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
        )
        ApprovalStep.objects.create(
            change_request=change_request,
            name="Final Approval",
            sequence=1,
            assigned_role=ApprovalStep.ROLE_APPROVER,
            assigned_group="Approver",
        )
        outsider = User.objects.create_user(username="outsider", password="pass12345")
        outsider.groups.add(Group.objects.get(name="Requester"))
        self.client.login(username="outsider", password="pass12345")
        response = self.client.get(reverse("change_management:request_detail", args=[change_request.pk]))
        self.assertEqual(response.status_code, 403)

    def test_high_risk_assessment_does_not_inject_extra_approval_steps(self):
        change_request = ChangeRequest.objects.create(
            title="High risk release",
            business_justification="Critical update",
            requester=self.requester,
            change_type=self.change_type,
            affected_services="Payments",
            implementation_plan="Deploy release",
            test_validation_plan="Regression test",
            rollback_plan="Rollback release",
            status=ChangeRequest.STATUS_SUBMITTED,
        )
        ApprovalStep.objects.create(
            change_request=change_request,
            name="Final Approval",
            sequence=1,
            assigned_role=ApprovalStep.ROLE_APPROVER,
            assigned_group="Approver",
        )
        self.client.login(username="approver", password="pass12345")
        response = self.client.post(
            reverse("change_management:update_risk", args=[change_request.pk]),
            {
                "impact_summary": "High impact",
                "likelihood_summary": "Likely",
                "residual_risk": ChangeRequest.RISK_HIGH,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(change_request.approval_steps.count(), 1)

    def test_schedule_requires_completed_risk_assessment(self):
        change_request = ChangeRequest.objects.create(
            title="Awaiting scheduling",
            business_justification="Ready to schedule",
            requester=self.requester,
            change_type=self.change_type,
            affected_services="API",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
            status=ChangeRequest.STATUS_APPROVED,
        )
        self.client.login(username="implementer", password="pass12345")
        response = self.client.post(
            reverse("change_management:transition_request", args=[change_request.pk]),
            {"target_status": ChangeRequest.STATUS_SCHEDULED, "notes": ""},
        )
        self.assertEqual(response.status_code, 302)
        change_request.refresh_from_db()
        self.assertEqual(change_request.status, ChangeRequest.STATUS_APPROVED)

    def test_implemented_requires_planned_window(self):
        change_request = ChangeRequest.objects.create(
            title="No planned window",
            business_justification="Window missing",
            requester=self.requester,
            change_type=self.change_type,
            affected_services="API",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
            status=ChangeRequest.STATUS_SCHEDULED,
        )
        self.client.login(username="implementer", password="pass12345")
        response = self.client.post(
            reverse("change_management:transition_request", args=[change_request.pk]),
            {"target_status": ChangeRequest.STATUS_IMPLEMENTED, "notes": ""},
        )
        self.assertEqual(response.status_code, 302)
        change_request.refresh_from_db()
        self.assertEqual(change_request.status, ChangeRequest.STATUS_SCHEDULED)

    def test_close_requires_results_and_evidence(self):
        change_request = ChangeRequest.objects.create(
            title="Close gate",
            business_justification="Testing close gate",
            requester=self.requester,
            change_type=self.change_type,
            affected_services="API",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
            status=ChangeRequest.STATUS_VALIDATED,
        )
        self.client.login(username="approver", password="pass12345")
        response = self.client.post(
            reverse("change_management:transition_request", args=[change_request.pk]),
            {"target_status": ChangeRequest.STATUS_CLOSED, "notes": ""},
        )
        self.assertEqual(response.status_code, 302)
        change_request.refresh_from_db()
        self.assertEqual(change_request.status, ChangeRequest.STATUS_VALIDATED)

    def test_seed_demo_users_command_creates_users(self):
        User.objects.filter(username="requester_demo").delete()
        call_command("seed_demo_users", force=True)
        self.assertTrue(User.objects.filter(username="requester_demo").exists())
        self.assertTrue(User.objects.filter(username="approver_demo").exists())

    def test_approver_can_approve_request(self):
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
            status=ChangeRequest.STATUS_SUBMITTED,
        )
        step = ApprovalStep.objects.create(
            change_request=change_request,
            name="Final Approval",
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

    def test_approver_can_reject_request(self):
        change_request = ChangeRequest.objects.create(
            title="Rejected request",
            business_justification="Not ready.",
            requester=self.requester,
            change_type=self.change_type,
            risk_level=ChangeRequest.RISK_MEDIUM,
            affected_services="Customer API",
            implementation_plan="Apply update",
            test_validation_plan="Run smoke tests",
            rollback_plan="Rollback release",
            status=ChangeRequest.STATUS_SUBMITTED,
        )
        step = ApprovalStep.objects.create(
            change_request=change_request,
            name="Final Approval",
            sequence=1,
            assigned_role=ApprovalStep.ROLE_APPROVER,
        )
        self.client.login(username="approver", password="pass12345")
        response = self.client.post(
            reverse("change_management:decide_step", args=[step.pk]),
            {"outcome": ApprovalStep.STATUS_REJECTED, "comments": "Needs revision."},
        )
        self.assertEqual(response.status_code, 302)
        change_request.refresh_from_db()
        self.assertEqual(change_request.status, ChangeRequest.STATUS_REJECTED)
