from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0025_company_geography_semantics")]

    operations = [
        migrations.AddField(model_name="company", name="founded_date_precision", field=models.CharField(blank=True, choices=[("DAY", "Exact day"), ("MONTH", "Month"), ("YEAR", "Year")], max_length=16)),
        migrations.AddField(model_name="company", name="founded_date_evidence", field=models.TextField(blank=True)),
        migrations.AddField(model_name="company", name="founded_date_source_url", field=models.URLField(blank=True, max_length=2048)),
        migrations.AddField(model_name="company", name="founding_anchor_status", field=models.CharField(choices=[("PENDING", "Pending primary-source verification"), ("STRUCTURED", "Structured-source candidate"), ("VERIFIED", "Verified primary source"), ("REJECTED", "Rejected")], db_index=True, default="PENDING", max_length=16)),
    ]
