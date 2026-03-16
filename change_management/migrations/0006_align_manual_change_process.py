from django.db import migrations, models


def align_change_data(apps, schema_editor):
    ChangeRequest = apps.get_model("change_management", "ChangeRequest")
    ChangeType = apps.get_model("change_management", "ChangeType")

    major_type, _ = ChangeType.objects.get_or_create(
        slug="major",
        defaults={
            "name": "Major",
            "description": "Changes requiring the full business and IT approval path.",
            "is_active": True,
            "is_preapproved": False,
            "requires_retro_review": False,
            "default_approval_mode": "sequential",
            "default_implementation_window_hours": 1,
        },
    )
    minor_type, _ = ChangeType.objects.get_or_create(
        slug="minor",
        defaults={
            "name": "Minor",
            "description": "Lower-impact changes using the same approval chain with lighter operational scope.",
            "is_active": True,
            "is_preapproved": False,
            "requires_retro_review": False,
            "default_approval_mode": "sequential",
            "default_implementation_window_hours": 1,
        },
    )

    ChangeType.objects.filter(slug__in=["major", "minor"]).update(is_active=True)
    ChangeType.objects.filter(slug__in=["standard", "normal", "emergency"]).update(is_active=False)

    for change_request in ChangeRequest.objects.select_related("change_type").all():
        if change_request.risk_level == "medium":
            change_request.risk_level = "high"

        current_slug = getattr(change_request.change_type, "slug", "")
        if current_slug in {"emergency", "major"}:
            change_request.change_type = major_type
        else:
            change_request.change_type = minor_type

        change_request.template = None
        change_request.save(update_fields=["risk_level", "change_type", "template", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("change_management", "0005_changenotification"),
    ]

    operations = [
        migrations.AddField(
            model_name="changerequest",
            name="business_impact",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="changerequest",
            name="department",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="changerequest",
            name="system_or_application",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RemoveField(
            model_name="changerequest",
            name="privacy_impact",
        ),
        migrations.RunPython(align_change_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="changerequest",
            name="business_justification",
            field=models.TextField(verbose_name="Reason for change"),
        ),
        migrations.AlterField(
            model_name="changerequest",
            name="risk_level",
            field=models.CharField(
                choices=[("low", "Low"), ("high", "High"), ("critical", "Critical")],
                default="low",
                max_length=20,
            ),
        ),
    ]
