from django.db import migrations


DEMO_USERNAMES = [
    "requester_demo",
    "reviewer_demo",
    "approver_demo",
    "cab_demo",
    "implementer_demo",
    "auditor_demo",
    "sdlc_admin",
]


def remove_demo_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.filter(username__in=DEMO_USERNAMES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("change_management", "0003_create_demo_users"),
    ]

    operations = [
        migrations.RunPython(remove_demo_users, reverse_code=migrations.RunPython.noop),
    ]
