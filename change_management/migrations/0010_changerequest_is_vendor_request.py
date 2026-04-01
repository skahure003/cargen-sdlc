from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("change_management", "0009_changerequest_vendor_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="changerequest",
            name="is_vendor_request",
            field=models.BooleanField(default=False),
        ),
    ]
