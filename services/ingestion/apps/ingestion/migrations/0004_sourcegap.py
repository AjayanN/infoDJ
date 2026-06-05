# Generated for dashboard ingestion quality gates.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
        ("ingestion", "0003_enable_pg_trgm"),
    ]

    operations = [
        migrations.CreateModel(
            name="SourceGap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dashboard", models.CharField(db_index=True, max_length=96)),
                ("gap_type", models.CharField(db_index=True, max_length=96)),
                ("provider", models.CharField(blank=True, db_index=True, max_length=96)),
                ("reason", models.TextField()),
                ("next_ingestion_task", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Open"),
                            ("IN_PROGRESS", "In progress"),
                            ("RESOLVED", "Resolved"),
                            ("WONT_FIX", "Won't fix"),
                        ],
                        db_index=True,
                        default="OPEN",
                        max_length=32,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="source_gaps",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "ordering": ["dashboard", "gap_type", "company_id", "provider"],
            },
        ),
        migrations.AddConstraint(
            model_name="sourcegap",
            constraint=models.UniqueConstraint(
                fields=("company", "dashboard", "gap_type", "provider"),
                name="unique_source_gap_scope",
            ),
        ),
        migrations.AddIndex(
            model_name="sourcegap",
            index=models.Index(fields=["dashboard", "status"], name="ingestion_s_dashboa_5e8c75_idx"),
        ),
        migrations.AddIndex(
            model_name="sourcegap",
            index=models.Index(fields=["gap_type", "status"], name="ingestion_s_gap_typ_4077af_idx"),
        ),
        migrations.AddIndex(
            model_name="sourcegap",
            index=models.Index(fields=["company", "dashboard"], name="ingestion_s_company_bac0f3_idx"),
        ),
    ]
