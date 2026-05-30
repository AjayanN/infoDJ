from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0001_initial"),
        ("ingestion", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BusinessEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_date", models.DateField(blank=True, db_index=True, null=True)),
                ("event_type", models.CharField(choices=[("BUSINESS_MODEL_PIVOT", "Business model pivot"), ("PRICING_CHANGE", "Pricing change"), ("PRODUCT_EXPANSION", "Product expansion"), ("GEOGRAPHIC_EXPANSION", "Geographic expansion"), ("CUSTOMER_SEGMENT_SHIFT", "Customer segment shift"), ("DISTRIBUTION_CHANNEL_SHIFT", "Distribution channel shift"), ("FUNDING_EVENT", "Funding event"), ("ACQUISITION", "Acquisition"), ("PARTNERSHIP", "Partnership"), ("LEADERSHIP_CHANGE", "Leadership change"), ("REGULATORY_RESPONSE", "Regulatory response"), ("CRISIS_RESPONSE", "Crisis response"), ("COMPETITIVE_RESPONSE", "Competitive response"), ("BRAND_REPOSITIONING", "Brand repositioning"), ("REVENUE_MODEL_EXPANSION", "Revenue model expansion")], db_index=True, max_length=64)),
                ("lifecycle_stage", models.CharField(blank=True, choices=[("IDEA", "Idea"), ("LAUNCH", "Launch"), ("EARLY_GROWTH", "Early growth"), ("SCALE", "Scale"), ("MATURITY", "Maturity"), ("TURNAROUND", "Turnaround"), ("DECLINE", "Decline"), ("REINVENTION", "Reinvention")], db_index=True, max_length=32)),
                ("before_state", models.TextField(blank=True)),
                ("after_state", models.TextField(blank=True)),
                ("trigger", models.TextField(blank=True)),
                ("decision", models.TextField(blank=True)),
                ("outcome", models.TextField(blank=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("MERGED", "Merged")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("raw_extraction_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("article_extraction", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="business_events", to="ingestion.articleextraction")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="business_events", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="business_events", to="ingestion.sourcedocument")),
            ],
            options={
                "ordering": ["-event_date", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="StrategicTurn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=512)),
                ("turn_type", models.CharField(choices=[("BUSINESS_MODEL_PIVOT", "Business model pivot"), ("PRICING_CHANGE", "Pricing change"), ("PRODUCT_EXPANSION", "Product expansion"), ("GEOGRAPHIC_EXPANSION", "Geographic expansion"), ("CUSTOMER_SEGMENT_SHIFT", "Customer segment shift"), ("DISTRIBUTION_CHANNEL_SHIFT", "Distribution channel shift"), ("FUNDING_EVENT", "Funding event"), ("ACQUISITION", "Acquisition"), ("PARTNERSHIP", "Partnership"), ("LEADERSHIP_CHANGE", "Leadership change"), ("REGULATORY_RESPONSE", "Regulatory response"), ("CRISIS_RESPONSE", "Crisis response"), ("COMPETITIVE_RESPONSE", "Competitive response"), ("BRAND_REPOSITIONING", "Brand repositioning"), ("REVENUE_MODEL_EXPANSION", "Revenue model expansion")], db_index=True, max_length=64)),
                ("start_date", models.DateField(blank=True, db_index=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("lifecycle_stage", models.CharField(blank=True, choices=[("IDEA", "Idea"), ("LAUNCH", "Launch"), ("EARLY_GROWTH", "Early growth"), ("SCALE", "Scale"), ("MATURITY", "Maturity"), ("TURNAROUND", "Turnaround"), ("DECLINE", "Decline"), ("REINVENTION", "Reinvention")], db_index=True, max_length=32)),
                ("summary", models.TextField(blank=True)),
                ("before_state", models.TextField(blank=True)),
                ("after_state", models.TextField(blank=True)),
                ("trigger", models.TextField(blank=True)),
                ("decision", models.TextField(blank=True)),
                ("outcome", models.TextField(blank=True)),
                ("founder_lesson", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("MERGED", "Merged")], db_index=True, default="DRAFT", max_length=32)),
                ("is_published", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="strategic_turns", to="companies.company")),
            ],
            options={
                "ordering": ["-start_date", "title"],
            },
        ),
        migrations.CreateModel(
            name="StrategicTurnSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("evidence_text", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("business_event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="strategic_turn_sources", to="curation.businessevent")),
                ("source_document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="strategic_turn_sources", to="ingestion.sourcedocument")),
                ("strategic_turn", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="turn_sources", to="curation.strategicturn")),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.AddIndex(
            model_name="businessevent",
            index=models.Index(fields=["company", "event_type"], name="curation_bu_company_fa4401_idx"),
        ),
        migrations.AddIndex(
            model_name="businessevent",
            index=models.Index(fields=["company", "review_status"], name="curation_bu_company_fea114_idx"),
        ),
        migrations.AddIndex(
            model_name="strategicturn",
            index=models.Index(fields=["company", "turn_type"], name="curation_st_company_55d883_idx"),
        ),
        migrations.AddIndex(
            model_name="strategicturn",
            index=models.Index(fields=["company", "review_status"], name="curation_st_company_06c482_idx"),
        ),
        migrations.AddIndex(
            model_name="strategicturn",
            index=models.Index(fields=["company", "is_published"], name="curation_st_company_1a7ef2_idx"),
        ),
        migrations.AddConstraint(
            model_name="strategicturnsource",
            constraint=models.UniqueConstraint(fields=("strategic_turn", "source_document", "business_event"), name="unique_turn_source_event"),
        ),
    ]
