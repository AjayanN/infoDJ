from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("companies", "0010_earningsguidancecomparison"), ("curation", "0005_businessevent_source_claim_actual_change")]

    operations = [
        migrations.CreateModel(
            name="StrategyMilestone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=180)),
                ("title", models.CharField(max_length=512)),
                ("milestone_type", models.CharField(choices=[("LAUNCH", "Launch"), ("REGULATORY_APPROVAL", "Regulatory approval"), ("MARKET_ENTRY", "Market entry"), ("CUSTOMER_TARGET", "Customer or user target"), ("CAPACITY_TARGET", "Capacity or production target"), ("INTEGRATION", "Integration step"), ("COST_SYNERGY", "Cost or synergy target"), ("PROFITABILITY", "Profitability or cash-flow target"), ("HIRING_RESTRUCTURING", "Hiring or restructuring step"), ("PARTNERSHIP", "Partnership delivery"), ("PRODUCT_ADOPTION", "Product adoption target"), ("STRATEGIC_EXECUTION", "Strategic execution")], db_index=True, max_length=32)),
                ("origin", models.CharField(choices=[("MANAGEMENT_ANNOUNCED", "Management announced"), ("REGULATOR_DEFINED", "Regulator defined"), ("CONTRACTUAL", "Contractual"), ("ANALYST_INFERRED", "Analyst inferred")], db_index=True, max_length=32)),
                ("current_status", models.CharField(choices=[("EXPECTED", "Expected"), ("STARTED", "Started"), ("COMPLETED", "Completed"), ("DELAYED", "Delayed"), ("CHANGED", "Changed"), ("CANCELLED", "Cancelled"), ("FAILED", "Failed"), ("UNKNOWN", "Unknown")], db_index=True, max_length=32)),
                ("expected_start_date", models.DateField(blank=True, null=True)),
                ("expected_end_date", models.DateField(blank=True, db_index=True, null=True)),
                ("date_precision", models.CharField(default="UNKNOWN", max_length=16)),
                ("owner", models.CharField(blank=True, max_length=255)),
                ("success_condition", models.TextField()),
                ("blocker", models.TextField(blank=True)),
                ("outcome_review", models.TextField(blank=True)),
                ("evidence_text", models.TextField()),
                ("related_entities", models.JSONField(blank=True, default=list)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("is_published", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="strategy_milestones", to="companies.company")),
                ("linked_kpi", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="strategy_milestones", to="companies.kpidefinition")),
                ("linked_promise", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="strategy_milestones", to="companies.managementpromise")),
                ("linked_strategic_turn", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="milestones", to="curation.strategicturn")),
                ("source_document", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="strategy_milestones", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["expected_end_date", "title"]},
        ),
        migrations.CreateModel(
            name="StrategyMilestoneStatusUpdate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("EXPECTED", "Expected"), ("STARTED", "Started"), ("COMPLETED", "Completed"), ("DELAYED", "Delayed"), ("CHANGED", "Changed"), ("CANCELLED", "Cancelled"), ("FAILED", "Failed"), ("UNKNOWN", "Unknown")], max_length=32)),
                ("summary", models.TextField()),
                ("blocker", models.TextField(blank=True)),
                ("evidence_text", models.TextField()),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], default="NEEDS_REVIEW", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("milestone", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_updates", to="companies.strategymilestone")),
                ("source_document", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="milestone_status_updates", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["status_date", "created_at"]},
        ),
        migrations.CreateModel(
            name="StrategyMilestoneDependency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("relationship", models.CharField(default="REQUIRES", max_length=32)),
                ("description", models.TextField(blank=True)),
                ("depends_on", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dependents", to="companies.strategymilestone")),
                ("milestone", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dependencies", to="companies.strategymilestone")),
            ],
        ),
        migrations.AddConstraint(model_name="strategymilestone", constraint=models.UniqueConstraint(fields=("company", "slug"), name="unique_company_milestone_slug")),
        migrations.AddIndex(model_name="strategymilestone", index=models.Index(fields=["company", "current_status"], name="company_milestone_status_idx")),
        migrations.AddIndex(model_name="strategymilestone", index=models.Index(fields=["company", "expected_end_date"], name="company_milestone_due_idx")),
        migrations.AddConstraint(model_name="strategymilestonestatusupdate", constraint=models.UniqueConstraint(fields=("milestone", "status_date", "status", "source_document"), name="unique_milestone_status_update")),
        migrations.AddConstraint(model_name="strategymilestonedependency", constraint=models.UniqueConstraint(fields=("milestone", "depends_on"), name="unique_milestone_dependency")),
    ]
