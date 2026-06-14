from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("companies", "0009_earningsperioddocument"), ("ingestion", "0006_marketprice_nullable_company")]

    operations = [
        migrations.CreateModel(
            name="EarningsGuidanceComparison",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("metric_name", models.CharField(max_length=255)),
                ("forecast_value", models.DecimalField(decimal_places=6, max_digits=24)),
                ("actual_value", models.DecimalField(decimal_places=6, max_digits=24)),
                ("unit", models.CharField(max_length=64)),
                ("comparison_status", models.CharField(max_length=32)),
                ("forecast_evidence", models.TextField()),
                ("actual_evidence", models.TextField()),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actual_source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="earnings_guidance_actuals", to="ingestion.sourcedocument")),
                ("forecast_source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="earnings_guidance_forecasts", to="ingestion.sourcedocument")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="guidance_comparisons", to="companies.earningsperiod")),
            ],
            options={"ordering": ["metric_name"]},
        ),
        migrations.AddConstraint(
            model_name="earningsguidancecomparison",
            constraint=models.UniqueConstraint(fields=("period", "metric_name"), name="unique_earnings_guidance_metric"),
        ),
    ]
