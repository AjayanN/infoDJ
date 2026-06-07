import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0004_business_model_map"), ("ingestion", "0006_marketprice_nullable_company")]

    operations = [
        migrations.CreateModel(
            name="KpiDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=120)), ("name", models.CharField(max_length=255)),
                ("description", models.TextField()), ("unit", models.CharField(max_length=64)),
                ("cadence", models.CharField(choices=[("MONTHLY", "Monthly"), ("QUARTERLY", "Quarterly"), ("ANNUAL", "Annual"), ("EVENT", "Event aligned")], max_length=16)),
                ("value_type", models.CharField(choices=[("REPORTED", "Reported"), ("CALCULATED", "Calculated")], default="REPORTED", max_length=16)),
                ("scope", models.CharField(blank=True, max_length=255)), ("aliases", models.JSONField(blank=True, default=list)),
                ("formula", models.TextField(blank=True)), ("is_active", models.BooleanField(default=True)),
                ("peer_comparable", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="kpi_definitions", to="companies.company")),
            ], options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="KpiDefinitionVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)), ("definition", models.TextField()),
                ("scope", models.CharField(blank=True, max_length=255)), ("change_note", models.TextField(blank=True)),
                ("kpi", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="definition_versions", to="companies.kpidefinition")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="kpi_definition_versions", to="ingestion.sourcedocument")),
            ], options={"ordering": ["-effective_date"]},
        ),
        migrations.CreateModel(
            name="KpiObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period_start", models.DateField()), ("period_end", models.DateField(db_index=True)),
                ("fiscal_year", models.PositiveIntegerField(blank=True, null=True)), ("fiscal_period", models.CharField(blank=True, max_length=16)),
                ("value", models.DecimalField(decimal_places=6, max_digits=24)), ("segment", models.CharField(blank=True, max_length=255)),
                ("geography", models.CharField(blank=True, max_length=255)), ("evidence_text", models.TextField(blank=True)),
                ("is_estimated", models.BooleanField(default=False)), ("is_restatement", models.BooleanField(default=False)),
                ("is_non_comparable", models.BooleanField(default=False)), ("definition_changed", models.BooleanField(default=False)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("kpi", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="observations", to="companies.kpidefinition")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="kpi_observations", to="ingestion.sourcedocument")),
            ], options={"ordering": ["period_end", "segment", "geography"]},
        ),
        migrations.CreateModel(
            name="KpiTarget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_date", models.DateField(db_index=True)), ("target_value", models.DecimalField(decimal_places=6, max_digits=24)),
                ("condition", models.TextField(blank=True)), ("status", models.CharField(default="IN_PROGRESS", max_length=32)),
                ("kpi", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="targets", to="companies.kpidefinition")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="kpi_targets", to="ingestion.sourcedocument")),
            ], options={"ordering": ["target_date"]},
        ),
        migrations.CreateModel(
            name="KpiComparability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_comparable", models.BooleanField(default=False)), ("rationale", models.TextField()), ("reviewed_at", models.DateField()),
                ("comparable_kpi", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="compared_by_records", to="companies.kpidefinition")),
                ("kpi", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comparability_records", to="companies.kpidefinition")),
            ],
        ),
        migrations.AddConstraint(model_name="kpidefinition", constraint=models.UniqueConstraint(fields=("company", "slug"), name="unique_company_kpi_slug")),
        migrations.AddConstraint(model_name="kpidefinitionversion", constraint=models.UniqueConstraint(fields=("kpi", "effective_date"), name="unique_kpi_definition_date")),
        migrations.AddConstraint(model_name="kpiobservation", constraint=models.UniqueConstraint(fields=("kpi", "period_end", "segment", "geography"), name="unique_kpi_observation_scope")),
        migrations.AddConstraint(model_name="kpicomparability", constraint=models.UniqueConstraint(fields=("kpi", "comparable_kpi"), name="unique_kpi_comparability_pair")),
    ]
