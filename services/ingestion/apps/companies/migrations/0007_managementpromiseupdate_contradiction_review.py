from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0006_managementpromise_managementpromiseupdate_and_more")]

    operations = [
        migrations.AddField(
            model_name="managementpromiseupdate",
            name="is_contradiction_candidate",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="managementpromiseupdate",
            name="contradiction_note",
            field=models.TextField(blank=True),
        ),
    ]
