from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0011_strategy_milestones"),
        ("ingestion", "0005_marketprice_financialfact"),
    ]

    operations = [
        migrations.CreateModel(
            name="CapitalAllocationPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fiscal_year", models.IntegerField(db_index=True)),
                ("fiscal_period", models.CharField(db_index=True, max_length=16)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(db_index=True)),
                ("filed_date", models.DateField(blank=True, db_index=True, null=True)),
                ("accession_number", models.CharField(blank=True, max_length=64)),
                ("cadence", models.CharField(choices=[("MONTHLY", "Monthly"), ("QUARTERLY", "Quarterly"), ("ANNUAL", "Annual"), ("EVENT", "Event aligned")], default="QUARTERLY", max_length=16)),
                ("headline", models.TextField(blank=True)),
                ("total_deployment", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("operating_cash_flow", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("cash_balance", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("free_cash_flow", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("calculation_note", models.TextField(blank=True)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("is_published", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="capital_allocation_periods", to="companies.company")),
            ],
            options={"ordering": ["-period_end", "-filed_date"]},
        ),
        migrations.CreateModel(
            name="CapitalAllocationItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("ACQUISITION_INVESTMENT", "Acquisitions and investments"), ("CAPEX", "Capital expenditure"), ("R_AND_D", "Research and development"), ("BUYBACK", "Share repurchases"), ("DIVIDEND", "Dividends"), ("DEBT_ISSUANCE", "Debt issuance"), ("DEBT_REPAYMENT", "Debt repayment"), ("RESTRUCTURING", "Restructuring"), ("CONTENT_INVENTORY", "Content and inventory investment"), ("INTERNAL_PROGRAM", "Internal strategic programs"), ("OPERATING_CASH_FLOW", "Operating cash flow context"), ("CASH_CONTEXT", "Cash balance context"), ("FREE_CASH_FLOW", "Free cash flow context")], db_index=True, max_length=32)),
                ("label", models.CharField(max_length=255)),
                ("value", models.DecimalField(decimal_places=6, max_digits=24)),
                ("unit", models.CharField(default="USD", max_length=64)),
                ("concept", models.CharField(blank=True, db_index=True, max_length=255)),
                ("evidence_text", models.TextField(blank=True)),
                ("is_context", models.BooleanField(db_index=True, default=False)),
                ("is_calculated", models.BooleanField(default=False)),
                ("calculation_method", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="companies.capitalallocationperiod")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="capital_allocation_items", to="ingestion.sourcedocument")),
                ("source_fact", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="capital_allocation_items", to="ingestion.financialfact")),
            ],
            options={"ordering": ["is_context", "category", "label"]},
        ),
        migrations.AddConstraint(
            model_name="capitalallocationperiod",
            constraint=models.UniqueConstraint(fields=("company", "fiscal_year", "fiscal_period", "period_end"), name="unique_capital_allocation_period"),
        ),
        migrations.AddIndex(
            model_name="capitalallocationperiod",
            index=models.Index(fields=["company", "period_end"], name="company_cap_alloc_period_idx"),
        ),
        migrations.AddConstraint(
            model_name="capitalallocationitem",
            constraint=models.UniqueConstraint(fields=("period", "category", "label", "concept"), name="unique_capital_allocation_item"),
        ),
    ]
