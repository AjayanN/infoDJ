from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("curation", "0005_businessevent_source_claim_actual_change")]

    operations = [
        migrations.AddField(model_name="businessevent", name="action_date", field=models.DateField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name="businessevent", name="action_date_precision", field=models.CharField(blank=True, choices=[("DAY", "Exact day"), ("MONTH", "Month"), ("QUARTER", "Quarter"), ("YEAR", "Year")], max_length=16)),
        migrations.AddField(model_name="businessevent", name="action_date_evidence", field=models.TextField(blank=True)),
        migrations.AddField(model_name="businessevent", name="lifecycle_context_json", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="businessevent", name="lifecycle_timing_status", field=models.CharField(choices=[("PENDING", "Pending verification"), ("VERIFIED", "Verified"), ("REJECTED", "Rejected")], db_index=True, default="PENDING", max_length=16)),
    ]
