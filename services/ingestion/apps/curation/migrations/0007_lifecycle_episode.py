from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("curation", "0006_verified_lifecycle_timing")]

    operations = [
        migrations.CreateModel(
            name="LifecycleEpisode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope", models.CharField(choices=[("COMPANY", "Company lifecycle"), ("PRODUCT", "Product lifecycle"), ("BUSINESS_LINE", "Business-line lifecycle")], default="COMPANY", max_length=32)),
                ("subject_name", models.CharField(blank=True, max_length=255)),
                ("stage", models.CharField(choices=[("IDEA", "Idea"), ("LAUNCH", "Launch"), ("EARLY_GROWTH", "Early growth"), ("SCALE", "Scale"), ("MATURITY", "Maturity"), ("TURNAROUND", "Turnaround"), ("DECLINE", "Decline"), ("REINVENTION", "Reinvention")], db_index=True, max_length=32)),
                ("start_date", models.DateField(db_index=True)),
                ("start_date_precision", models.CharField(choices=[("DAY", "Exact day"), ("MONTH", "Month"), ("QUARTER", "Quarter"), ("YEAR", "Year")], max_length=16)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("evidence_text", models.TextField()),
                ("source_url", models.URLField(max_length=2048)),
                ("verification_status", models.CharField(choices=[("PENDING", "Pending verification"), ("VERIFIED", "Verified"), ("REJECTED", "Rejected")], db_index=True, default="PENDING", max_length=16)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lifecycle_episodes", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lifecycle_episodes", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["company_id", "start_date", "id"]},
        ),
        migrations.AddField(
            model_name="businessevent",
            name="lifecycle_episode",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="business_events", to="curation.lifecycleepisode"),
        ),
        migrations.AddIndex(
            model_name="lifecycleepisode",
            index=models.Index(fields=["company", "stage", "start_date"], name="curation_li_company_afe944_idx"),
        ),
        migrations.AddIndex(
            model_name="lifecycleepisode",
            index=models.Index(fields=["verification_status", "stage"], name="curation_li_verif_7129a4_idx"),
        ),
    ]

