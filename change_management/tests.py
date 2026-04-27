from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.content import load_site_content

from .models import ApprovalStep, ChangeRequest, ChangeType


class ChangeManagementSmokeTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.local",
            password="pass12345",
        )
        self.requester = User.objects.create_user(username="requester", password="pass12345")
        self.requester.groups.add(Group.objects.get(name="Requester"))
        self.reviewer = User.objects.create_user(username="reviewer", password="pass12345")
        self.reviewer.groups.add(Group.objects.get(name="Reviewer"))
        self.approver = User.objects.create_user(username="approver", password="pass12345")
        self.approver.groups.add(Group.objects.get(name="Approver"))
        self.implementer = User.objects.create_user(username="implementer", password="pass12345")
        self.implementer.groups.add(Group.objects.get(name="Implementer"))
        self.auditor = User.objects.create_user(username="auditor", password="pass12345")
        self.auditor.groups.add(Group.objects.get(name="Auditor/Admin"))
        self.major_change_type = ChangeType.objects.get(slug="major")
        self.minor_change_type = ChangeType.objects.get(slug="minor")

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

    def test_agile_process_area_is_documented(self):
        load_site_content.cache_clear()
        data = load_site_content()
        process_area = data["area_lookup"]["process"]
        self.assertEqual(process_area["title"], "Agile Delivery Process")
        self.assertIn("Sprint planning", process_area["body_html"])
        self.assertIn("retrospective", process_area["body_html"].lower())

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
                "department": "ICT",
                "system_or_application": "Express Way",
                "change_type": self.major_change_type.pk,
                "risk_level": ChangeRequest.RISK_HIGH,
                "process_owner_approver": self.reviewer.pk,
                "business_owner_approver": self.approver.pk,
                "head_of_it_approver": self.auditor.pk,
                "implementation_acknowledger": self.implementer.pk,
                "business_justification": "Required for planned release.",
                "business_impact": "Improves service stability.",
                "implementation_plan": "Deploy the application and verify health checks.",
                "test_validation_plan": "Run smoke tests and verify dashboards.",
                "rollback_plan": "Rollback to previous container image.",
                "planned_start": "",
                "planned_end": "",
                "security_impact": "No material change.",
                "tasks-TOTAL_FORMS": "1",
                "tasks-INITIAL_FORMS": "0",
                "tasks-MIN_NUM_FORMS": "0",
                "tasks-MAX_NUM_FORMS": "1000",
                "tasks-0-title": "Deploy application",
            },
        )
        self.assertEqual(response.status_code, 302)
        change_request = ChangeRequest.objects.get(title="Deploy release 2026.03.11")
        self.assertTrue(change_request.change_id.startswith("CHG-"))
        self.assertEqual(change_request.approval_steps.count(), 4)
        self.assertEqual(change_request.approval_steps.get(name="Process Owner Approval").assigned_user, self.reviewer)
        self.assertEqual(change_request.approval_steps.get(name="Business Owner Approval").assigned_user, self.approver)
        self.assertEqual(change_request.approval_steps.get(name="Head of IT Approval").assigned_user, self.auditor)
        self.assertEqual(change_request.approval_steps.get(name="IT Implementation Acknowledgement").assigned_user, self.implementer)
        self.assertFalse(change_request.approval_steps.get(name="Head of IT Approval").required)

    def test_superuser_can_create_vendor_change_request(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.post(
            reverse("change_management:request_create"),
            {
                "title": "Vendor release request",
                "department": "ICT",
                "system_or_application": "Vendor Portal",
                "change_type": self.minor_change_type.pk,
                "risk_level": ChangeRequest.RISK_LOW,
                "is_vendor_request": "on",
                "vendor_name": "Samuel",
                "vendor_company": "CG",
                "vendor_email": "samuel@cg.example",
                "process_owner_approver": "",
                "business_owner_approver": "",
                "head_of_it_approver": "",
                "implementation_acknowledger": self.implementer.pk,
                "business_justification": "Vendor initiated update.",
                "business_impact": "Minimal impact.",
                "implementation_plan": "Apply the vendor patch.",
                "test_validation_plan": "Run smoke tests.",
                "rollback_plan": "Rollback the patch.",
                "planned_start": "",
                "planned_end": "",
                "security_impact": "No material change.",
            },
        )
        self.assertEqual(response.status_code, 302)
        change_request = ChangeRequest.objects.get(title="Vendor release request")
        self.assertEqual(change_request.requester, self.admin_user)
        self.assertTrue(change_request.is_vendor_request)
        self.assertEqual(change_request.vendor_name, "Samuel")
        self.assertEqual(change_request.vendor_company, "CG")
        self.assertEqual(change_request.vendor_email, "samuel@cg.example")

    def test_superuser_vendor_request_requires_vendor_details(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.post(
            reverse("change_management:request_create"),
            {
                "title": "Vendor request without vendor details",
                "department": "ICT",
                "system_or_application": "Vendor Portal",
                "change_type": self.minor_change_type.pk,
                "risk_level": ChangeRequest.RISK_LOW,
                "is_vendor_request": "on",
                "vendor_name": "",
                "vendor_company": "",
                "vendor_email": "",
                "process_owner_approver": "",
                "business_owner_approver": "",
                "head_of_it_approver": "",
                "implementation_acknowledger": self.implementer.pk,
                "business_justification": "Vendor initiated update.",
                "business_impact": "Minimal impact.",
                "implementation_plan": "Apply the vendor patch.",
                "test_validation_plan": "Run smoke tests.",
                "rollback_plan": "Rollback the patch.",
                "planned_start": "",
                "planned_end": "",
                "security_impact": "No material change.",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter the vendor contact person name.")
        self.assertContains(response, "Enter the vendor company name.")
        self.assertContains(response, "Enter the vendor email address.")

    def test_superuser_can_create_internal_request_without_vendor_details(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.post(
            reverse("change_management:request_create"),
            {
                "title": "Internal admin request",
                "department": "ICT",
                "system_or_application": "Internal Portal",
                "change_type": self.minor_change_type.pk,
                "risk_level": ChangeRequest.RISK_LOW,
                "process_owner_approver": "",
                "business_owner_approver": "",
                "head_of_it_approver": "",
                "implementation_acknowledger": self.implementer.pk,
                "business_justification": "Internal update.",
                "business_impact": "Minimal impact.",
                "implementation_plan": "Apply update.",
                "test_validation_plan": "Run smoke tests.",
                "rollback_plan": "Rollback update.",
                "planned_start": "",
                "planned_end": "",
                "security_impact": "No material change.",
            },
        )
        self.assertEqual(response.status_code, 302)
        change_request = ChangeRequest.objects.get(title="Internal admin request")
        self.assertFalse(change_request.is_vendor_request)
        self.assertEqual(change_request.vendor_name, "")
        self.assertEqual(change_request.vendor_company, "")
        self.assertEqual(change_request.vendor_email, "")

    def test_minor_change_only_requires_it_implementation_approval(self):
        self.client.login(username="requester", password="pass12345")
        response = self.client.post(
            reverse("change_management:request_create"),
            {
                "title": "Minor config change",
                "department": "ICT",
                "system_or_application": "Express Way",
                "change_type": self.minor_change_type.pk,
                "risk_level": ChangeRequest.RISK_LOW,
                "process_owner_approver": "",
                "business_owner_approver": "",
                "head_of_it_approver": "",
                "implementation_acknowledger": self.implementer.pk,
                "business_justification": "Small non-breaking update.",
                "business_impact": "Minimal impact.",
                "implementation_plan": "Update the configuration and validate service health.",
                "test_validation_plan": "Run smoke tests.",
                "rollback_plan": "Restore previous configuration.",
                "planned_start": "",
                "planned_end": "",
                "security_impact": "No material change.",
            },
        )
        self.assertEqual(response.status_code, 302)
        change_request = ChangeRequest.objects.get(title="Minor config change")
        self.assertEqual(change_request.approval_steps.count(), 1)
        step = change_request.approval_steps.get()
        self.assertEqual(step.name, "IT Implementation Approval")
        self.assertEqual(step.assigned_user, self.implementer)

    def test_minor_change_can_include_optional_auditor(self):
        self.client.login(username="requester", password="pass12345")
        response = self.client.post(
            reverse("change_management:request_create"),
            {
                "title": "Minor config change with auditor",
                "department": "ICT",
                "system_or_application": "Express Way",
                "change_type": self.minor_change_type.pk,
                "risk_level": ChangeRequest.RISK_LOW,
                "process_owner_approver": "",
                "business_owner_approver": "",
                "head_of_it_approver": self.auditor.pk,
                "implementation_acknowledger": self.implementer.pk,
                "business_justification": "Small non-breaking update.",
                "business_impact": "Minimal impact.",
                "implementation_plan": "Update the configuration and validate service health.",
                "test_validation_plan": "Run smoke tests.",
                "rollback_plan": "Restore previous configuration.",
                "planned_start": "",
                "planned_end": "",
                "security_impact": "No material change.",
            },
        )
        self.assertEqual(response.status_code, 302)
        change_request = ChangeRequest.objects.get(title="Minor config change with auditor")
        self.assertEqual(change_request.approval_steps.count(), 2)
        self.assertEqual(change_request.approval_steps.get(name="IT Implementation Approval").assigned_user, self.implementer)
        auditor_step = change_request.approval_steps.get(name="Head of IT Approval")
        self.assertEqual(auditor_step.assigned_user, self.auditor)
        self.assertFalse(auditor_step.required)

    def test_major_change_does_not_require_auditor_selection(self):
        self.client.login(username="requester", password="pass12345")
        response = self.client.post(
            reverse("change_management:request_create"),
            {
                "title": "Major release without auditor",
                "department": "ICT",
                "system_or_application": "Express Way",
                "change_type": self.major_change_type.pk,
                "risk_level": ChangeRequest.RISK_HIGH,
                "process_owner_approver": self.reviewer.pk,
                "business_owner_approver": self.approver.pk,
                "head_of_it_approver": "",
                "implementation_acknowledger": self.implementer.pk,
                "business_justification": "Required for planned release.",
                "business_impact": "Improves service stability.",
                "implementation_plan": "Deploy the application and verify health checks.",
                "test_validation_plan": "Run smoke tests and verify dashboards.",
                "rollback_plan": "Rollback to previous container image.",
                "planned_start": "",
                "planned_end": "",
                "security_impact": "No material change.",
            },
        )
        self.assertEqual(response.status_code, 302)
        change_request = ChangeRequest.objects.get(title="Major release without auditor")
        self.assertEqual(change_request.approval_steps.count(), 3)
        self.assertFalse(change_request.approval_steps.filter(name="Head of IT Approval").exists())

    def test_requester_cannot_add_evidence_to_other_users_change(self):
        other_requester = User.objects.create_user(username="requester_two", password="pass12345")
        other_requester.groups.add(Group.objects.get(name="Requester"))
        change_request = ChangeRequest.objects.create(
            title="Infra restart",
            business_justification="Routine restart.",
            requester=other_requester,
            change_type=self.minor_change_type,
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
            change_type=self.minor_change_type,
            affected_services="API",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
        )
        other_request = ChangeRequest.objects.create(
            title="Other change",
            business_justification="Other record.",
            requester=other_requester,
            change_type=self.minor_change_type,
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
            change_type=self.minor_change_type,
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
            change_type=self.minor_change_type,
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
            change_type=self.minor_change_type,
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
            change_type=self.minor_change_type,
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
            change_type=self.minor_change_type,
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
            change_type=self.minor_change_type,
            risk_level=ChangeRequest.RISK_HIGH,
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

    def test_approval_sends_email_to_requester_and_vendor(self):
        self.admin_user.email = "admin@example.local"
        self.admin_user.save(update_fields=["email"])
        change_request = ChangeRequest.objects.create(
            title="Vendor database patch",
            business_justification="Critical fix.",
            requester=self.admin_user,
            vendor_name="Samuel",
            vendor_company="CG",
            vendor_email="samuel@cg.example",
            change_type=self.minor_change_type,
            risk_level=ChangeRequest.RISK_HIGH,
            affected_services="Primary database",
            implementation_plan="Apply patch",
            test_validation_plan="Run validation query",
            rollback_plan="Restore snapshot",
            status=ChangeRequest.STATUS_SUBMITTED,
        )
        step = ApprovalStep.objects.create(
            change_request=change_request,
            name="IT Implementation Approval",
            sequence=1,
            assigned_role=ApprovalStep.ROLE_IMPLEMENTER,
            assigned_user=self.implementer,
        )
        self.implementer.email = "implementer@example.local"
        self.implementer.save(update_fields=["email"])
        mail.outbox = []
        self.client.login(username="implementer", password="pass12345")
        response = self.client.post(
            reverse("change_management:decide_step", args=[step.pk]),
            {"outcome": ApprovalStep.STATUS_APPROVED, "comments": "Approved for execution."},
        )
        self.assertEqual(response.status_code, 302)
        recipients = {tuple(message.to) for message in mail.outbox}
        self.assertIn(("admin@example.local",), recipients)
        self.assertIn(("samuel@cg.example",), recipients)

    def test_approval_does_not_send_vendor_email_for_non_vendor_request(self):
        change_request = ChangeRequest.objects.create(
            title="Internal database patch",
            business_justification="Critical fix.",
            requester=self.admin_user,
            vendor_name="Samuel",
            vendor_company="CG",
            vendor_email="samuel@cg.example",
            is_vendor_request=False,
            change_type=self.minor_change_type,
            risk_level=ChangeRequest.RISK_HIGH,
            affected_services="Primary database",
            implementation_plan="Apply patch",
            test_validation_plan="Run validation query",
            rollback_plan="Restore snapshot",
            status=ChangeRequest.STATUS_SUBMITTED,
        )
        step = ApprovalStep.objects.create(
            change_request=change_request,
            name="IT Implementation Approval",
            sequence=1,
            assigned_role=ApprovalStep.ROLE_IMPLEMENTER,
            assigned_user=self.implementer,
        )
        self.implementer.email = "implementer@example.local"
        self.implementer.save(update_fields=["email"])
        mail.outbox = []
        self.client.login(username="implementer", password="pass12345")
        response = self.client.post(
            reverse("change_management:decide_step", args=[step.pk]),
            {"outcome": ApprovalStep.STATUS_APPROVED, "comments": "Approved for execution."},
        )
        self.assertEqual(response.status_code, 302)
        recipients = {tuple(message.to) for message in mail.outbox}
        self.assertIn(("admin@example.local",), recipients)
        self.assertNotIn(("samuel@cg.example",), recipients)

    def test_approver_can_reject_request(self):
        change_request = ChangeRequest.objects.create(
            title="Rejected request",
            business_justification="Not ready.",
            requester=self.requester,
            change_type=self.minor_change_type,
            risk_level=ChangeRequest.RISK_HIGH,
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

    def test_admin_can_create_approval_user(self):
        self.client.login(username="admin", password="pass12345")
        response = self.client.post(
            reverse("change_management:approval_user_create"),
            {
                "username": "it_approver",
                "email": "it.approver@example.local",
                "role": "Implementer",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        created_user = User.objects.get(username="it_approver")
        self.assertEqual(created_user.email, "it.approver@example.local")
        self.assertTrue(created_user.groups.filter(name="Implementer").exists())

    def test_superuser_can_delete_change_request(self):
        change_request = ChangeRequest.objects.create(
            title="Disposable request",
            business_justification="Testing delete.",
            requester=self.requester,
            change_type=self.minor_change_type,
            affected_services="API",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
        )
        self.client.login(username="admin", password="pass12345")
        response = self.client.post(reverse("change_management:request_delete", args=[change_request.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ChangeRequest.objects.filter(pk=change_request.pk).exists())

    def test_non_superuser_cannot_delete_change_request(self):
        change_request = ChangeRequest.objects.create(
            title="Protected request",
            business_justification="Testing permissions.",
            requester=self.requester,
            change_type=self.minor_change_type,
            affected_services="API",
            implementation_plan="Deploy",
            test_validation_plan="Test",
            rollback_plan="Rollback",
        )
        self.client.login(username="requester", password="pass12345")
        response = self.client.post(reverse("change_management:request_delete", args=[change_request.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ChangeRequest.objects.filter(pk=change_request.pk).exists())

    def test_submit_blocks_when_assigned_approver_has_no_email(self):
        self.implementer.email = ""
        self.implementer.save(update_fields=["email"])
        self.client.login(username="requester", password="pass12345")
        response = self.client.post(
            reverse("change_management:request_create"),
            {
                "title": "Minor config change without approver email",
                "department": "ICT",
                "system_or_application": "Express Way",
                "change_type": self.minor_change_type.pk,
                "risk_level": ChangeRequest.RISK_LOW,
                "process_owner_approver": "",
                "business_owner_approver": "",
                "head_of_it_approver": "",
                "implementation_acknowledger": self.implementer.pk,
                "business_justification": "Small non-breaking update.",
                "business_impact": "Minimal impact.",
                "implementation_plan": "Update the configuration and validate service health.",
                "test_validation_plan": "Run smoke tests.",
                "rollback_plan": "Restore previous configuration.",
                "planned_start": "",
                "planned_end": "",
                "security_impact": "No material change.",
            },
        )
        self.assertEqual(response.status_code, 302)
        change_request = ChangeRequest.objects.get(title="Minor config change without approver email")
        submit_response = self.client.post(reverse("change_management:submit_request", args=[change_request.pk]))
        self.assertEqual(submit_response.status_code, 302)
        change_request.refresh_from_db()
        self.assertEqual(change_request.status, ChangeRequest.STATUS_DRAFT)
