from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0016_customer_supplier_dependency"),
        ("curation", "0001_initial"),
        ("ingestion", "0007_sourcegapresolutioncandidate"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeographicExpansionSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="DRAFT", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("methodology", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="geographic_expansion_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="geographic_expansion_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="GeographicExpansionMarket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("geography", models.CharField(max_length=255)),
                ("market_type", models.CharField(db_index=True, default="REGION", max_length=64)),
                ("current_status", models.CharField(choices=[("ACTIVE", "Active market"), ("ENTERED", "Entered"), ("EXPANDING", "Expanding"), ("EXITED", "Exited"), ("PAUSED", "Paused"), ("UNKNOWN", "Unknown")], db_index=True, max_length=32)),
                ("entry_date", models.DateField(blank=True, db_index=True, null=True)),
                ("exit_date", models.DateField(blank=True, db_index=True, null=True)),
                ("local_partnerships", models.JSONField(blank=True, default=list)),
                ("regulatory_barriers", models.JSONField(blank=True, default=list)),
                ("revenue_contribution", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("revenue_currency", models.CharField(blank=True, max_length=16)),
                ("revenue_period", models.CharField(blank=True, max_length=64)),
                ("expansion_rationale", models.TextField(blank=True)),
                ("outcome_summary", models.TextField(blank=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="REVIEWED", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("linked_event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="geographic_expansion_markets", to="curation.businessevent")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="markets", to="companies.geographicexpansionsnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="geographic_expansion_markets", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["geography", "market_type"]},
        ),
        migrations.AddConstraint(model_name="geographicexpansionsnapshot", constraint=models.UniqueConstraint(fields=("company", "effective_date"), name="unique_geographic_expansion_snapshot")),
        migrations.AddIndex(model_name="geographicexpansionsnapshot", index=models.Index(fields=["company", "status", "effective_date"], name="company_geo_exp_status_idx")),
        migrations.AddConstraint(model_name="geographicexpansionmarket", constraint=models.UniqueConstraint(fields=("snapshot", "geography", "market_type"), name="unique_geo_expansion_market")),
        migrations.AddIndex(model_name="geographicexpansionmarket", index=models.Index(fields=["snapshot", "current_status"], name="geo_exp_market_status_idx")),
    ]
