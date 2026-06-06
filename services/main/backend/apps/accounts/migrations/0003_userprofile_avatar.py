from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_userprofile_pending_subscription_tier"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="avatar",
            field=models.FileField(blank=True, upload_to="avatars/%Y/%m/"),
        ),
    ]
