from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0001_initial"),
        ("ingestion", "0006_marketprice_nullable_company"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyProfileSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="DRAFT", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("business_model", models.TextField(blank=True)),
                ("products", models.JSONField(blank=True, default=list)),
                ("customer_groups", models.JSONField(blank=True, default=list)),
                ("revenue_sources", models.JSONField(blank=True, default=list)),
                ("geographies", models.JSONField(blank=True, default=list)),
                ("leadership", models.JSONField(blank=True, default=list)),
                ("competitors", models.JSONField(blank=True, default=list)),
                ("strategic_priorities", models.JSONField(blank=True, default=list)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profile_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="company_profile_snapshots", to="ingestion.sourcedocument")),
            ],
            options={
                "ordering": ["-effective_date", "-created_at"],
                "indexes": [models.Index(fields=["company", "status", "effective_date"], name="company_prof_status_date_idx")],
                "constraints": [models.UniqueConstraint(fields=("company", "effective_date", "source_document"), name="unique_company_profile_snapshot_source")],
            },
        ),
    ]
