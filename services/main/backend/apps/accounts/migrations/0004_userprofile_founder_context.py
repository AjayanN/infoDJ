from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_userprofile_avatar"),
    ]

    operations = [
        migrations.AddField(model_name="userprofile", name="founder_sector", field=models.CharField(blank=True, max_length=128)),
        migrations.AddField(model_name="userprofile", name="founder_business_type", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="userprofile", name="founder_stage", field=models.CharField(blank=True, max_length=32)),
        migrations.AddField(model_name="userprofile", name="founder_objective", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="userprofile", name="founder_geography", field=models.CharField(blank=True, max_length=128)),
        migrations.AddField(model_name="userprofile", name="founder_target_customer", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="userprofile", name="founder_revenue_model", field=models.CharField(blank=True, max_length=128)),
        migrations.AddField(model_name="userprofile", name="founder_constraints", field=models.TextField(blank=True)),
    ]
