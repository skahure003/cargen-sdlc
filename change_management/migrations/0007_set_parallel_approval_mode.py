from django.db import migrations


def set_parallel_mode(apps, schema_editor):
    ChangeType = apps.get_model("change_management", "ChangeType")
    ChangeType.objects.filter(slug__in=["major", "minor"]).update(default_approval_mode="parallel")


class Migration(migrations.Migration):
    dependencies = [
        ("change_management", "0006_align_manual_change_process"),
    ]

    operations = [
        migrations.RunPython(set_parallel_mode, migrations.RunPython.noop),
    ]
