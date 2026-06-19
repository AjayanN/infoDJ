from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0012_capital_allocation"),
        ("ingestion", "0005_marketprice_financialfact"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompetitivePositionSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="DRAFT", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("methodology", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="competitive_position_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="competitive_position_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="CompetitivePeer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("peer_name", models.CharField(max_length=255)),
                ("relationship_type", models.CharField(choices=[("DIRECT", "Direct competitor"), ("CATEGORY", "Category competitor"), ("SUBSTITUTE", "Substitute"), ("PLATFORM", "Platform competitor"), ("SUPPLIER_CUSTOMER", "Supplier or customer overlap"), ("PEER_BENCHMARK", "Peer benchmark")], db_index=True, max_length=32)),
                ("scope", models.CharField(blank=True, max_length=255)),
                ("geography", models.CharField(blank=True, max_length=255)),
                ("product_overlap", models.JSONField(blank=True, default=list)),
                ("customer_overlap", models.JSONField(blank=True, default=list)),
                ("evidence_text", models.TextField(blank=True)),
                ("is_in_universe", models.BooleanField(db_index=True, default=False)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("peer_company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="competitive_peer_mentions", to="companies.company")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="peers", to="companies.competitivepositionsnapshot")),
            ],
            options={"ordering": ["relationship_type", "peer_name"]},
        ),
        migrations.CreateModel(
            name="CompetitiveDimension",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dimension_type", models.CharField(choices=[("PRODUCT_OVERLAP", "Product overlap"), ("PRICING_POSITION", "Pricing position"), ("GEOGRAPHIC_OVERLAP", "Geographic overlap"), ("CUSTOMER_OVERLAP", "Customer overlap"), ("SCALE_COMPARISON", "Scale comparison"), ("COMPETITIVE_ACTION", "Competitive action"), ("MOAT_EVIDENCE", "Moat evidence"), ("OPPOSING_EVIDENCE", "Opposing evidence")], db_index=True, max_length=32)),
                ("label", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("peer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="dimensions", to="companies.competitivepeer")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dimensions", to="companies.competitivepositionsnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="competitive_dimensions", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["dimension_type", "label"]},
        ),
        migrations.AddConstraint(
            model_name="competitivepositionsnapshot",
            constraint=models.UniqueConstraint(fields=("company", "effective_date"), name="unique_competitive_position_snapshot"),
        ),
        migrations.AddIndex(
            model_name="competitivepositionsnapshot",
            index=models.Index(fields=["company", "status", "effective_date"], name="company_comp_pos_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="competitivepeer",
            constraint=models.UniqueConstraint(fields=("snapshot", "peer_name", "relationship_type", "scope"), name="unique_competitive_peer"),
        ),
        migrations.AddConstraint(
            model_name="competitivedimension",
            constraint=models.UniqueConstraint(fields=("snapshot", "peer", "dimension_type", "label"), name="unique_competitive_dimension"),
        ),
    ]
