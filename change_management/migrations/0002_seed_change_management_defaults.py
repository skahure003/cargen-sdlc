from django.db import migrations


def seed_defaults(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    ChangeType = apps.get_model("change_management", "ChangeType")
    ChangeTemplate = apps.get_model("change_management", "ChangeTemplate")
    for group_name in ["Requester", "Reviewer", "Approver", "CAB", "Implementer", "Auditor/Admin"]:
        Group.objects.get_or_create(name=group_name)

    change_types = {
        "standard": {
            "name": "Standard Change",
            "description": "Pre-approved low-risk operational changes with a lightweight review path.",
            "is_preapproved": True,
            "requires_retro_review": False,
        },
        "normal": {
            "name": "Normal Change",
            "description": "Planned changes that require standard review and approval before implementation.",
            "is_preapproved": False,
            "requires_retro_review": False,
        },
        "emergency": {
            "name": "Emergency Change",
            "description": "Urgent changes that may bypass normal lead time but require retrospective CAB review.",
            "is_preapproved": False,
            "requires_retro_review": True,
        },
    }

    seeded_types = {}
    for slug, payload in change_types.items():
        seeded_types[slug], _ = ChangeType.objects.get_or_create(slug=slug, defaults=payload)

    templates = [
        {
            "slug": "standard-service-patch",
            "name": "Standard Service Patch",
            "change_type": seeded_types["standard"],
            "description": "Template for routine service patches with low outage risk.",
            "default_risk_level": "low",
            "default_approval_steps": [
                {"name": "Peer Review", "sequence": 1, "assigned_role": "reviewer"},
            ],
        },
        {
            "slug": "normal-release",
            "name": "Normal Release Change",
            "change_type": seeded_types["normal"],
            "description": "Template for planned application or infrastructure releases.",
            "default_risk_level": "medium",
            "default_approval_steps": [
                {"name": "Peer Review", "sequence": 1, "assigned_role": "reviewer"},
                {"name": "Change Approval", "sequence": 2, "assigned_role": "approver"},
            ],
        },
        {
            "slug": "emergency-remediation",
            "name": "Emergency Remediation",
            "change_type": seeded_types["emergency"],
            "description": "Template for critical production fixes with retrospective CAB review.",
            "default_risk_level": "high",
            "default_approval_steps": [
                {"name": "Peer Review", "sequence": 1, "assigned_role": "reviewer"},
                {"name": "Change Approval", "sequence": 2, "assigned_role": "approver"},
                {"name": "CAB Review", "sequence": 3, "assigned_role": "cab"},
            ],
        },
    ]
    for payload in templates:
        ChangeTemplate.objects.get_or_create(slug=payload["slug"], defaults=payload)


def unseed_defaults(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    ChangeType = apps.get_model("change_management", "ChangeType")
    ChangeTemplate = apps.get_model("change_management", "ChangeTemplate")

    Group.objects.filter(name__in=["Requester", "Reviewer", "Approver", "CAB", "Implementer", "Auditor/Admin"]).delete()
    ChangeTemplate.objects.filter(
        slug__in=["standard-service-patch", "normal-release", "emergency-remediation"]
    ).delete()
    ChangeType.objects.filter(slug__in=["standard", "normal", "emergency"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("change_management", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_defaults, reverse_code=unseed_defaults),
    ]
