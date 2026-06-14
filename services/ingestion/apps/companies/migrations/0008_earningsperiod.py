import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0007_managementpromiseupdate_contradiction_review"),
        ("ingestion", "0006_marketprice_nullable_company"),
    ]

    operations = [
        migrations.CreateModel(
            name="EarningsPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accession_number", models.CharField(max_length=64)),
                ("fiscal_year", models.IntegerField(db_index=True)),
                ("fiscal_period", models.CharField(db_index=True, max_length=16)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(db_index=True)),
                ("filed_date", models.DateField(db_index=True)),
                ("headline", models.TextField()),
                ("management_explanation", models.TextField(blank=True)),
                ("infodj_interpretation", models.TextField(blank=True)),
                ("unanswered_questions", models.JSONField(blank=True, default=list)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("is_published", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="earnings_periods", to="companies.company")),
                ("source_document", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="earnings_periods", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-period_end", "-filed_date"]},
        ),
        migrations.AddConstraint(
            model_name="earningsperiod",
            constraint=models.UniqueConstraint(fields=("company", "accession_number"), name="unique_company_earnings_accession"),
        ),
        migrations.AddIndex(
            model_name="earningsperiod",
            index=models.Index(fields=["company", "period_end"], name="company_earnings_period_idx"),
        ),
    ]
