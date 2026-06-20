from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0016_customer_supplier_dependency"),
        ("ingestion", "0006_marketprice_nullable_company"),
    ]

    operations = [
        migrations.CreateModel(
            name="SourceGapResolutionCandidate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dashboard", models.CharField(db_index=True, max_length=96)),
                ("gap_type", models.CharField(db_index=True, max_length=96)),
                ("candidate_type", models.CharField(db_index=True, max_length=96)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("extraction_status", models.CharField(db_index=True, default="CANDIDATE", max_length=32)),
                ("review_status", models.CharField(db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("next_action", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="source_gap_resolution_candidates",
                        to="companies.company",
                    ),
                ),
                (
                    "source_document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="source_gap_resolution_candidates",
                        to="ingestion.sourcedocument",
                    ),
                ),
                (
                    "source_gap",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resolution_candidates",
                        to="ingestion.sourcegap",
                    ),
                ),
            ],
            options={
                "ordering": ["dashboard", "gap_type", "company_id", "-confidence_score"],
                "indexes": [
                    models.Index(fields=["dashboard", "gap_type"], name="ingestion_s_dashboa_6107ef_idx"),
                    models.Index(fields=["company", "review_status"], name="ingestion_s_company_3d90e0_idx"),
                    models.Index(fields=["source_gap", "review_status"], name="ingestion_s_source__4dd603_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("company", "dashboard", "gap_type", "source_document", "candidate_type"),
                        name="unique_source_gap_resolution_candidate",
                    )
                ],
            },
        ),
    ]
