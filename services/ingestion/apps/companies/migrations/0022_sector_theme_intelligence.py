from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0021_regulatory_litigation_calendar"),
        ("curation", "0001_initial"),
        ("ingestion", "0007_sourcegapresolutioncandidate"),
    ]

    operations = [
        migrations.CreateModel(
            name="SectorTheme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=160, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("taxonomy_type", models.CharField(choices=[("SECTOR", "Sector"), ("INDUSTRY", "Industry"), ("THEME", "Theme"), ("SUBTHEME", "Subtheme")], db_index=True, max_length=32)),
                ("description", models.TextField(blank=True)),
                ("aliases", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="companies.sectortheme")),
            ],
            options={"ordering": ["taxonomy_type", "name"]},
        ),
        migrations.CreateModel(
            name="SectorThemeSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="REVIEWED", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("methodology", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sector_theme_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sector_theme_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="CompanyThemeExposure",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("exposure_type", models.CharField(choices=[("REVENUE", "Revenue"), ("COST", "Cost"), ("CAPEX", "Capital expenditure"), ("PRODUCT", "Product"), ("CUSTOMER", "Customer"), ("SUPPLY_CHAIN", "Supply chain"), ("REGULATORY", "Regulatory"), ("NARRATIVE", "Narrative")], db_index=True, max_length=32)),
                ("materiality", models.CharField(choices=[("MATERIAL_OPERATING", "Material operating exposure"), ("OPERATING", "Operating exposure"), ("WATCH", "Watch"), ("NARRATIVE_ONLY", "Narrative only"), ("UNKNOWN", "Unknown")], db_index=True, max_length=32)),
                ("source_key", models.CharField(max_length=255)),
                ("evidence_date", models.DateField(blank=True, db_index=True, null=True)),
                ("evidence_summary", models.TextField(blank=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("exposure_rationale", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="REVIEWED", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("linked_capital_allocation_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="theme_exposures", to="companies.capitalallocationitem")),
                ("linked_event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="theme_exposures", to="curation.businessevent")),
                ("linked_kpi", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="theme_exposures", to="companies.kpidefinition")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="exposures", to="companies.sectorthemesnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="theme_exposures", to="ingestion.sourcedocument")),
                ("theme", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="company_exposures", to="companies.sectortheme")),
            ],
            options={"ordering": ["theme__name", "exposure_type", "-evidence_date"]},
        ),
        migrations.AddIndex(model_name="sectortheme", index=models.Index(fields=["taxonomy_type", "is_active"], name="theme_tax_type_active_idx")),
        migrations.AddConstraint(model_name="sectorthemesnapshot", constraint=models.UniqueConstraint(fields=("company", "effective_date"), name="unique_sector_theme_snapshot")),
        migrations.AddIndex(model_name="sectorthemesnapshot", index=models.Index(fields=["company", "status", "effective_date"], name="company_theme_status_idx")),
        migrations.AddConstraint(model_name="companythemeexposure", constraint=models.UniqueConstraint(fields=("snapshot", "source_key"), name="unique_theme_exposure_source")),
    ]
