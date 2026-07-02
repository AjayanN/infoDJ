from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0020_valuation_context"),
        ("curation", "0001_initial"),
        ("ingestion", "0007_sourcegapresolutioncandidate"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegulatoryLitigationSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="REVIEWED", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("methodology", models.TextField(blank=True)),
                ("legal_guardrail", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="regulatory_litigation_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="regulatory_litigation_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="RegulatoryLitigationMatter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("matter_type", models.CharField(choices=[("LITIGATION", "Litigation"), ("INVESTIGATION", "Investigation"), ("REGULATORY_REVIEW", "Regulatory review"), ("APPROVAL", "Approval"), ("COMPLIANCE_OBLIGATION", "Compliance obligation"), ("SETTLEMENT", "Settlement"), ("OTHER", "Other")], db_index=True, max_length=32)),
                ("jurisdiction", models.CharField(blank=True, max_length=128)),
                ("authority", models.CharField(blank=True, max_length=255)),
                ("business_area", models.CharField(blank=True, max_length=255)),
                ("stage", models.CharField(choices=[("IDENTIFIED", "Identified"), ("FILED", "Filed"), ("INVESTIGATION", "Investigation"), ("REVIEW", "Review"), ("HEARING", "Hearing"), ("DECISION_PENDING", "Decision pending"), ("APPEAL", "Appeal"), ("COMPLIANCE", "Compliance"), ("CLOSED", "Closed"), ("UNKNOWN", "Unknown")], db_index=True, default="UNKNOWN", max_length=32)),
                ("matter_status", models.CharField(choices=[("OPEN", "Open"), ("PENDING", "Pending"), ("APPROVED", "Approved"), ("SETTLED", "Settled"), ("DISMISSED", "Dismissed"), ("CLOSED", "Closed"), ("UNKNOWN", "Unknown")], db_index=True, default="UNKNOWN", max_length=32)),
                ("materiality", models.CharField(choices=[("MATERIAL", "Material"), ("WATCH", "Watch"), ("DISCLOSED", "Disclosed"), ("UNKNOWN", "Unknown")], db_index=True, default="UNKNOWN", max_length=32)),
                ("opened_date", models.DateField(blank=True, null=True)),
                ("next_date", models.DateField(blank=True, null=True)),
                ("next_date_type", models.CharField(blank=True, max_length=64)),
                ("allegation_or_issue", models.TextField(blank=True)),
                ("company_response", models.TextField(blank=True)),
                ("interim_decision", models.TextField(blank=True)),
                ("final_outcome", models.TextField(blank=True)),
                ("exposure_context", models.TextField(blank=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="REVIEWED", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("linked_event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="regulatory_litigation_matters", to="curation.businessevent")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="matters", to="companies.regulatorylitigationsnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="regulatory_litigation_matters", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["matter_status", "next_date", "-opened_date", "title"]},
        ),
        migrations.AddConstraint(model_name="regulatorylitigationsnapshot", constraint=models.UniqueConstraint(fields=("company", "effective_date"), name="unique_reg_lit_snapshot")),
        migrations.AddIndex(model_name="regulatorylitigationsnapshot", index=models.Index(fields=["company", "status", "effective_date"], name="company_reglit_status_idx")),
        migrations.AddConstraint(model_name="regulatorylitigationmatter", constraint=models.UniqueConstraint(fields=("snapshot", "title", "matter_type", "opened_date"), name="unique_reg_lit_matter")),
    ]
