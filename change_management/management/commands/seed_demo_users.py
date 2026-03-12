from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


DEMO_USERS = [
    ("requester_demo", "Requester", "Requester123!"),
    ("approver_demo", "Approver", "Approver123!"),
    ("implementer_demo", "Implementer", "Implementer123!"),
    ("auditor_demo", "Auditor/Admin", "Auditor123!"),
]


class Command(BaseCommand):
    help = "Seed local demo users for change-management testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding even when DEBUG is False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Demo users can only be seeded when DEBUG=True. Use --force to override.")

        User = get_user_model()
        created_count = 0
        for username, group_name, password in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.local",
                    "is_staff": True,
                },
            )
            user.groups.add(Group.objects.get(name=group_name))
            user.set_password(password)
            user.save(update_fields=["password"])
            created_count += int(created)

        admin_user, created = User.objects.get_or_create(
            username="sdlc_admin",
            defaults={
                "email": "sdlc_admin@example.local",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin_user.groups.add(Group.objects.get(name="Auditor/Admin"))
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password("Admin123!")
        admin_user.save(update_fields=["password", "is_staff", "is_superuser"])
        created_count += int(created)

        self.stdout.write(self.style.SUCCESS(f"Seeded demo users. New users created: {created_count}"))
