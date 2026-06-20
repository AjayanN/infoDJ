from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0015_acquisition_lifecycle"),
        ("ingestion", "0005_marketprice_financialfact"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerSupplierDependencySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="DRAFT", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("methodology", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dependency_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dependency_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="CustomerSupplierDependency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dependency_type", models.CharField(choices=[("CUSTOMER", "Named customer"), ("CUSTOMER_SEGMENT", "Customer segment"), ("SUPPLIER", "Supplier"), ("MANUFACTURER", "Manufacturer"), ("PLATFORM", "Platform"), ("DISTRIBUTOR", "Distributor"), ("LICENSOR", "Licensor"), ("INFRASTRUCTURE", "Infrastructure provider"), ("CONTRACT", "Contractual dependency"), ("PARTNER", "Partner")], db_index=True, max_length=32)),
                ("counterparty_name", models.CharField(max_length=255)),
                ("is_named_counterparty", models.BooleanField(db_index=True, default=False)),
                ("materiality_band", models.CharField(choices=[("DISCLOSED_MATERIAL", "Disclosed material"), ("CONCENTRATION_DISCLOSED", "Concentration disclosed"), ("IMPORTANT", "Important"), ("CONTEXT", "Context"), ("UNKNOWN", "Unknown")], db_index=True, max_length=32)),
                ("disclosure_confidence", models.CharField(choices=[("NAMED", "Named counterparty"), ("UNNAMED", "Unnamed disclosed counterparty"), ("CATEGORY_ONLY", "Category only"), ("REVIEWED_INFERENCE", "Reviewed inference")], db_index=True, max_length=32)),
                ("concentration_percent", models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ("geography", models.CharField(blank=True, max_length=255)),
                ("product_scope", models.CharField(blank=True, max_length=255)),
                ("relationship_summary", models.TextField(blank=True)),
                ("risk_summary", models.TextField(blank=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("counterparty_company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dependency_counterparty_mentions", to="companies.company")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dependencies", to="companies.customersupplierdependencysnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_supplier_dependencies", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["dependency_type", "counterparty_name"]},
        ),
        migrations.CreateModel(
            name="DependencyContractTerm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term_type", models.CharField(choices=[("CONCENTRATION", "Concentration disclosure"), ("RENEWAL", "Renewal"), ("EXPIRATION", "Expiration"), ("EXCLUSIVITY", "Exclusivity"), ("MINIMUM_COMMITMENT", "Minimum commitment"), ("TERMINATION", "Termination"), ("OTHER", "Other contract term")], db_index=True, max_length=32)),
                ("effective_date", models.DateField(blank=True, db_index=True, null=True)),
                ("expiration_date", models.DateField(blank=True, db_index=True, null=True)),
                ("description", models.TextField()),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="NEEDS_REVIEW", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("dependency", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contract_terms", to="companies.customersupplierdependency")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dependency_contract_terms", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["term_type", "expiration_date", "effective_date"]},
        ),
        migrations.AddConstraint(model_name="customersupplierdependencysnapshot", constraint=models.UniqueConstraint(fields=("company", "effective_date"), name="unique_dependency_snapshot")),
        migrations.AddIndex(model_name="customersupplierdependencysnapshot", index=models.Index(fields=["company", "status", "effective_date"], name="company_dep_status_idx")),
        migrations.AddConstraint(model_name="customersupplierdependency", constraint=models.UniqueConstraint(fields=("snapshot", "dependency_type", "counterparty_name", "product_scope"), name="unique_dependency_relationship")),
        migrations.AddConstraint(model_name="dependencycontractterm", constraint=models.UniqueConstraint(fields=("dependency", "term_type", "description"), name="unique_dependency_contract_term")),
    ]
