from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0003_companyprofilesnapshot_profile_dimensions"),
        ("ingestion", "0006_marketprice_nullable_company"),
    ]

    operations = [
        migrations.CreateModel(
            name="BusinessModelSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="DRAFT", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="business_model_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="business_model_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="BusinessModelComponent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("component_type", models.CharField(choices=[("PAYER", "Payer"), ("USER", "User"), ("OFFERING", "Product or service"), ("REVENUE", "Revenue mechanism"), ("CHANNEL", "Sales or distribution channel"), ("GEOGRAPHY", "Geographic market"), ("PARTNER", "Partner"), ("COST", "Cost driver"), ("ASSET", "Key asset")], db_index=True, max_length=16)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("scope", models.CharField(blank=True, max_length=255)),
                ("evidence_text", models.TextField(blank=True)),
                ("is_inferred", models.BooleanField(default=False)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="components", to="companies.businessmodelsnapshot")),
            ],
            options={"ordering": ["component_type", "name"]},
        ),
        migrations.CreateModel(
            name="BusinessModelRelationship",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("relationship_type", models.CharField(db_index=True, max_length=64)),
                ("description", models.TextField(blank=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("is_inferred", models.BooleanField(default=False)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("from_component", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_relationships", to="companies.businessmodelcomponent")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="relationships", to="companies.businessmodelsnapshot")),
                ("to_component", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_relationships", to="companies.businessmodelcomponent")),
            ],
            options={"ordering": ["relationship_type", "id"]},
        ),
        migrations.AddConstraint(model_name="businessmodelsnapshot", constraint=models.UniqueConstraint(fields=("company", "effective_date", "source_document"), name="unique_business_model_snapshot_source")),
        migrations.AddConstraint(model_name="businessmodelcomponent", constraint=models.UniqueConstraint(fields=("snapshot", "component_type", "name", "scope"), name="unique_business_model_component")),
        migrations.AddConstraint(model_name="businessmodelrelationship", constraint=models.UniqueConstraint(fields=("snapshot", "from_component", "to_component", "relationship_type"), name="unique_business_model_relationship")),
    ]
