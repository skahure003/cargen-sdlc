from django.contrib.auth.hashers import make_password
from django.db import migrations


DEMO_USERS = [
    ("requester_demo", "Requester", "Requester123!"),
    ("reviewer_demo", "Reviewer", "Reviewer123!"),
    ("approver_demo", "Approver", "Approver123!"),
    ("cab_demo", "CAB", "Cab123456!"),
    ("implementer_demo", "Implementer", "Implementer123!"),
    ("auditor_demo", "Auditor/Admin", "Auditor123!"),
]


def create_demo_users(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")

    for username, group_name, password in DEMO_USERS:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.local",
                "is_staff": True,
                "password": make_password(password),
            },
        )
        if created:
            user.groups.add(Group.objects.get(name=group_name))

    admin_user, created = User.objects.get_or_create(
        username="sdlc_admin",
        defaults={
            "email": "sdlc_admin@example.local",
            "is_staff": True,
            "is_superuser": True,
            "password": make_password("Admin123!"),
        },
    )
    if created:
        admin_user.groups.add(Group.objects.get(name="Auditor/Admin"))


def remove_demo_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    usernames = [username for username, _, _ in DEMO_USERS] + ["sdlc_admin"]
    User.objects.filter(username__in=usernames).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("change_management", "0002_seed_change_management_defaults"),
    ]

    operations = [
        migrations.RunPython(create_demo_users, reverse_code=remove_demo_users),
    ]
