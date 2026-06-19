from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0013_competitive_position"),
        ("curation", "0005_businessevent_source_claim_actual_change"),
        ("ingestion", "0005_marketprice_financialfact"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductCatalogSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="DRAFT", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("chronology_note", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_catalog_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="product_catalog_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="ProductOffering",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("offering_type", models.CharField(choices=[("FAMILY", "Product family"), ("PRODUCT", "Product"), ("EDITION", "Edition"), ("PLAN", "Plan"), ("FEATURE", "Feature"), ("ADD_ON", "Add-on")], db_index=True, max_length=16)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("availability", models.CharField(blank=True, max_length=255)),
                ("geography", models.CharField(blank=True, max_length=255)),
                ("customer_segment", models.CharField(blank=True, max_length=255)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="companies.productoffering")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offerings", to="companies.productcatalogsnapshot")),
            ],
            options={"ordering": ["offering_type", "name"]},
        ),
        migrations.CreateModel(
            name="ProductChange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("change_type", models.CharField(choices=[("LAUNCH", "Launch"), ("UPDATE", "Update"), ("RENAME", "Rename"), ("BUNDLE", "Bundle"), ("DISCONTINUATION", "Discontinuation"), ("MIGRATION", "Migration"), ("PRICE_CHANGE", "Price change"), ("PACKAGING_CHANGE", "Packaging change")], db_index=True, max_length=32)),
                ("title", models.CharField(max_length=512)),
                ("announcement_date", models.DateField(blank=True, db_index=True, null=True)),
                ("effective_date", models.DateField(blank=True, db_index=True, null=True)),
                ("before_state", models.TextField(blank=True)),
                ("after_state", models.TextField(blank=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("linked_event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="product_changes", to="curation.businessevent")),
                ("offering", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="changes", to="companies.productoffering")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="changes", to="companies.productcatalogsnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="product_changes", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-announcement_date", "title"]},
        ),
        migrations.CreateModel(
            name="PriceObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("observed_date", models.DateField(db_index=True)),
                ("effective_date", models.DateField(blank=True, db_index=True, null=True)),
                ("amount", models.DecimalField(decimal_places=6, max_digits=18)),
                ("currency", models.CharField(max_length=16)),
                ("billing_period", models.CharField(blank=True, max_length=32)),
                ("geography", models.CharField(blank=True, max_length=255)),
                ("customer_segment", models.CharField(blank=True, max_length=255)),
                ("tax_treatment", models.CharField(blank=True, max_length=255)),
                ("is_promotional", models.BooleanField(db_index=True, default=False)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="price_observations", to="companies.productoffering")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="price_observations", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-observed_date"]},
        ),
        migrations.AddConstraint(model_name="productcatalogsnapshot", constraint=models.UniqueConstraint(fields=("company", "effective_date"), name="unique_product_catalog_snapshot")),
        migrations.AddIndex(model_name="productcatalogsnapshot", index=models.Index(fields=["company", "status", "effective_date"], name="company_prod_cat_status_idx")),
        migrations.AddConstraint(model_name="productoffering", constraint=models.UniqueConstraint(fields=("snapshot", "offering_type", "name"), name="unique_product_offering")),
        migrations.AddConstraint(model_name="productchange", constraint=models.UniqueConstraint(fields=("snapshot", "title", "change_type", "announcement_date"), name="unique_product_change")),
        migrations.AddConstraint(model_name="priceobservation", constraint=models.UniqueConstraint(fields=("offering", "observed_date", "currency", "geography", "customer_segment", "billing_period"), name="unique_price_observation")),
    ]
