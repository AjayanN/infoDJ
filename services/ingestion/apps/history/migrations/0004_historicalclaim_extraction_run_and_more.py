from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("history", "0003_alter_sourceconnectorconfig_coverage_tracks_and_more"), ("ingestion", "0012_sourcedocument_access_scope_and_more")]

    operations = [
        migrations.AddField(model_name="historicalclaim", name="extraction_run", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="historical_claims", to="ingestion.extractionrun")),
        migrations.AddField(model_name="claimreview", name="resolution_options", field=models.JSONField(blank=True, default=list)),
    ]
