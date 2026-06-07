from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_companyprofilesnapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyprofilesnapshot",
            name="brands",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="companyprofilesnapshot",
            name="segments",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="companyprofilesnapshot",
            name="subsidiaries",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
