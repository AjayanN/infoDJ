from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0017_geographic_expansion"),
        ("ingestion", "0007_sourcegapresolutioncandidate"),
    ]

    operations = [
        migrations.CreateModel(
            name="OwnershipInsiderSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="DRAFT", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("methodology", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ownership_insider_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ownership_insider_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="OwnershipPosition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("holder_name", models.CharField(max_length=255)),
                ("holder_type", models.CharField(choices=[("FOUNDER", "Founder"), ("EXECUTIVE", "Executive"), ("DIRECTOR", "Director"), ("INSTITUTIONAL", "Institutional"), ("STRATEGIC", "Strategic holder"), ("GOVERNMENT", "Government"), ("PUBLIC_MARKET", "Public market"), ("UNKNOWN", "Unknown")], db_index=True, max_length=32)),
                ("position_type", models.CharField(choices=[("INSIDER_CONTEXT", "Insider context"), ("BENEFICIAL_OWNERSHIP", "Beneficial ownership"), ("VOTING_CONTROL", "Voting control"), ("INSTITUTIONAL_POSITION", "Institutional position"), ("STRATEGIC_STAKE", "Strategic stake")], db_index=True, max_length=32)),
                ("economic_ownership_pct", models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ("voting_power_pct", models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ("shares_owned", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("share_class", models.CharField(blank=True, max_length=128)),
                ("filing_date", models.DateField(blank=True, db_index=True, null=True)),
                ("report_period", models.CharField(blank=True, max_length=64)),
                ("disclosure_form", models.CharField(blank=True, max_length=64)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="REVIEWED", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="positions", to="companies.ownershipinsidersnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ownership_positions", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["holder_type", "holder_name"]},
        ),
        migrations.CreateModel(
            name="InsiderTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("insider_name", models.CharField(max_length=255)),
                ("insider_role", models.CharField(blank=True, max_length=255)),
                ("transaction_type", models.CharField(choices=[("PURCHASE", "Purchase"), ("SALE", "Sale"), ("GRANT", "Grant"), ("EXERCISE", "Exercise"), ("PLANNED_SALE", "Planned sale"), ("OTHER", "Other")], db_index=True, max_length=32)),
                ("transaction_date", models.DateField(blank=True, db_index=True, null=True)),
                ("shares", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("price", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("value", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("planned_sale", models.BooleanField(db_index=True, default=False)),
                ("plan_reference", models.CharField(blank=True, max_length=255)),
                ("ownership_after", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="REVIEWED", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="insider_transactions", to="companies.ownershipinsidersnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="insider_transactions", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-transaction_date", "insider_name"]},
        ),
        migrations.AddConstraint(model_name="ownershipinsidersnapshot", constraint=models.UniqueConstraint(fields=("company", "effective_date"), name="unique_ownership_insider_snapshot")),
        migrations.AddIndex(model_name="ownershipinsidersnapshot", index=models.Index(fields=["company", "status", "effective_date"], name="company_owner_status_idx")),
        migrations.AddConstraint(model_name="ownershipposition", constraint=models.UniqueConstraint(fields=("snapshot", "holder_name", "holder_type", "position_type"), name="unique_ownership_position")),
        migrations.AddConstraint(model_name="insidertransaction", constraint=models.UniqueConstraint(fields=("snapshot", "insider_name", "transaction_type", "transaction_date"), name="unique_insider_transaction")),
    ]
