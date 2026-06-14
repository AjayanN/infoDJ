import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0008_earningsperiod"), ("ingestion", "0006_marketprice_nullable_company")]

    operations = [
        migrations.CreateModel(
            name="EarningsPeriodDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(db_index=True, max_length=32)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="companies.earningsperiod")),
                ("source_document", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="earnings_document_links", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["document_type", "source_document_id"]},
        ),
        migrations.AddConstraint(
            model_name="earningsperioddocument",
            constraint=models.UniqueConstraint(fields=("period", "source_document"), name="unique_earnings_period_document"),
        ),
    ]
