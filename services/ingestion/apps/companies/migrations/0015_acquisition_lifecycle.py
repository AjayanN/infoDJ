from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0014_product_pricing_history"),
        ("curation", "0005_businessevent_source_claim_actual_change"),
        ("ingestion", "0005_marketprice_financialfact"),
    ]

    operations = [
        migrations.CreateModel(
            name="AcquisitionLifecycleDeal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=255)),
                ("target_name", models.CharField(max_length=255)),
                ("transaction_type", models.CharField(choices=[("ACQUISITION", "Acquisition"), ("MERGER", "Merger"), ("ASSET_PURCHASE", "Asset purchase"), ("MINORITY_INVESTMENT", "Minority investment"), ("JOINT_VENTURE", "Joint venture"), ("DIVESTITURE", "Divestiture")], db_index=True, max_length=32)),
                ("current_stage", models.CharField(choices=[("RUMORED_REPORTED", "Rumored or reported"), ("ANNOUNCED", "Announced"), ("UNDER_REVIEW", "Under review"), ("APPROVED", "Approved"), ("BLOCKED_ABANDONED", "Blocked or abandoned"), ("CLOSED", "Closed"), ("INTEGRATING", "Integrating"), ("INTEGRATED", "Integrated"), ("DIVESTED", "Divested"), ("IMPAIRED_WRITTEN_DOWN", "Impaired or written down"), ("OUTCOME_REVIEWED", "Outcome reviewed")], db_index=True, max_length=32)),
                ("outcome_category", models.CharField(choices=[("TOO_EARLY", "Too early to assess"), ("ON_TRACK", "On track"), ("INTEGRATED", "Integrated"), ("DELAYED", "Delayed"), ("REVISED", "Revised"), ("IMPAIRED", "Impaired"), ("DIVESTED", "Divested"), ("ABANDONED", "Abandoned"), ("VALUE_UNCLEAR", "Value unclear")], db_index=True, max_length=32)),
                ("announcement_date", models.DateField(blank=True, db_index=True, null=True)),
                ("expected_close_date", models.DateField(blank=True, db_index=True, null=True)),
                ("close_date", models.DateField(blank=True, db_index=True, null=True)),
                ("purchase_price", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("currency", models.CharField(blank=True, max_length=16)),
                ("payment_form", models.CharField(blank=True, max_length=128)),
                ("approvals", models.JSONField(blank=True, default=list)),
                ("conditions", models.JSONField(blank=True, default=list)),
                ("management_rationale", models.TextField(blank=True)),
                ("promised_synergies", models.TextField(blank=True)),
                ("integration_summary", models.TextField(blank=True)),
                ("outcome_review", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("is_published", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acquisition_lifecycle_deals", to="companies.company")),
                ("linked_event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acquisition_lifecycle_deals", to="curation.businessevent")),
                ("linked_strategic_turn", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acquisition_lifecycle_deals", to="curation.strategicturn")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acquisition_lifecycle_deals", to="ingestion.sourcedocument")),
                ("target_company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acquisition_target_mentions", to="companies.company")),
            ],
            options={"ordering": ["-announcement_date", "target_name"]},
        ),
        migrations.CreateModel(
            name="AcquisitionLifecycleEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stage", models.CharField(choices=[("RUMORED_REPORTED", "Rumored or reported"), ("ANNOUNCED", "Announced"), ("UNDER_REVIEW", "Under review"), ("APPROVED", "Approved"), ("BLOCKED_ABANDONED", "Blocked or abandoned"), ("CLOSED", "Closed"), ("INTEGRATING", "Integrating"), ("INTEGRATED", "Integrated"), ("DIVESTED", "Divested"), ("IMPAIRED_WRITTEN_DOWN", "Impaired or written down"), ("OUTCOME_REVIEWED", "Outcome reviewed")], db_index=True, max_length=32)),
                ("event_date", models.DateField(blank=True, db_index=True, null=True)),
                ("title", models.CharField(max_length=512)),
                ("description", models.TextField(blank=True)),
                ("price_revision", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("currency", models.CharField(blank=True, max_length=16)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], default="NEEDS_REVIEW", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deal", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stage_events", to="companies.acquisitionlifecycledeal")),
                ("linked_milestone", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acquisition_lifecycle_events", to="companies.strategymilestone")),
                ("linked_product_change", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acquisition_lifecycle_events", to="companies.productchange")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acquisition_lifecycle_events", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["event_date", "created_at"]},
        ),
        migrations.AddConstraint(model_name="acquisitionlifecycledeal", constraint=models.UniqueConstraint(fields=("company", "slug"), name="unique_acquisition_lifecycle_deal")),
        migrations.AddIndex(model_name="acquisitionlifecycledeal", index=models.Index(fields=["company", "current_stage"], name="company_acq_stage_idx")),
        migrations.AddIndex(model_name="acquisitionlifecycledeal", index=models.Index(fields=["company", "outcome_category"], name="company_acq_outcome_idx")),
        migrations.AddConstraint(model_name="acquisitionlifecycleevent", constraint=models.UniqueConstraint(fields=("deal", "stage", "title", "event_date"), name="unique_acquisition_lifecycle_event")),
    ]
