from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("change_management", "0008_alter_changeriskassessment_residual_risk"),
    ]

    operations = [
        migrations.AddField(
            model_name="changerequest",
            name="vendor_company",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="changerequest",
            name="vendor_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="changerequest",
            name="vendor_name",
            field=models.CharField(blank=True, max_length=160),
        ),
    ]
