from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ingestion", "0012_sourcedocument_access_scope_and_more")]

    operations = [
        migrations.AddField(model_name="extractionrun", name="budget_cents", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="extractionrun", name="extractor_version", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="extractionrun", name="prompt_version", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="extractionrun", name="provider", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="extractionrun", name="raw_candidate_response", field=models.JSONField(blank=True, default=dict)),
    ]
