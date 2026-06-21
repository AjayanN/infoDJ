from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0018_ownership_insider_activity"),
        ("curation", "0001_initial"),
        ("ingestion", "0007_sourcegapresolutioncandidate"),
    ]

    operations = [
        migrations.CreateModel(
            name="LeadershipDecisionSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("effective_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("REVIEWED", "Reviewed"), ("PUBLISHED", "Published")], db_index=True, default="DRAFT", max_length=16)),
                ("summary", models.TextField(blank=True)),
                ("methodology", models.TextField(blank=True)),
                ("non_causation_note", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="leadership_decision_snapshots", to="companies.company")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="leadership_decision_snapshots", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="LeadershipRoleRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("leader_name", models.CharField(max_length=255)),
                ("role_title", models.CharField(blank=True, max_length=255)),
                ("role_type", models.CharField(choices=[("CEO", "Chief executive"), ("CFO", "Chief financial"), ("COO", "Chief operating"), ("CHAIR", "Board chair"), ("DIRECTOR", "Director"), ("EXECUTIVE", "Executive"), ("BOARD", "Board"), ("UNKNOWN", "Unknown")], db_index=True, max_length=32)),
                ("transition_type", models.CharField(choices=[("CURRENT_ROLE", "Current role"), ("APPOINTMENT", "Appointment"), ("DEPARTURE", "Departure"), ("ROLE_CHANGE", "Role change"), ("BOARD_CHANGE", "Board change"), ("SUCCESSION_PLAN", "Succession plan")], db_index=True, max_length=32)),
                ("start_date", models.DateField(blank=True, db_index=True, null=True)),
                ("end_date", models.DateField(blank=True, db_index=True, null=True)),
                ("interim_status", models.BooleanField(db_index=True, default=False)),
                ("co_leadership", models.BooleanField(db_index=True, default=False)),
                ("stated_priorities", models.JSONField(blank=True, default=list)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="REVIEWED", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("linked_event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="leadership_role_records", to="curation.businessevent")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="roles", to="companies.leadershipdecisionsnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="leadership_role_records", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["leader_name", "role_title"]},
        ),
        migrations.CreateModel(
            name="LeadershipDecisionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("decision_type", models.CharField(choices=[("STRATEGIC_PRIORITY", "Strategic priority"), ("MATERIAL_DECISION", "Material decision"), ("SUCCESSION", "Succession"), ("CAPITAL_ALLOCATION", "Capital allocation"), ("ACQUISITION", "Acquisition"), ("MILESTONE", "Milestone"), ("PROMISE", "Promise"), ("OTHER", "Other")], db_index=True, max_length=32)),
                ("decision_date", models.DateField(blank=True, db_index=True, null=True)),
                ("leader_name", models.CharField(blank=True, max_length=255)),
                ("summary", models.TextField(blank=True)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("review_status", models.CharField(choices=[("DRAFT", "Draft"), ("NEEDS_REVIEW", "Needs review"), ("REVIEWED", "Reviewed"), ("REJECTED", "Rejected")], db_index=True, default="REVIEWED", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("linked_event", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="leadership_decision_records", to="curation.businessevent")),
                ("linked_strategic_turn", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="leadership_decision_records", to="curation.strategicturn")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="decisions", to="companies.leadershipdecisionsnapshot")),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="leadership_decision_records", to="ingestion.sourcedocument")),
            ],
            options={"ordering": ["-decision_date", "title"]},
        ),
        migrations.AddConstraint(model_name="leadershipdecisionsnapshot", constraint=models.UniqueConstraint(fields=("company", "effective_date"), name="unique_leadership_decision_snapshot")),
        migrations.AddIndex(model_name="leadershipdecisionsnapshot", index=models.Index(fields=["company", "status", "effective_date"], name="company_leader_status_idx")),
        migrations.AddConstraint(model_name="leadershiprolerecord", constraint=models.UniqueConstraint(fields=("snapshot", "leader_name", "role_title", "transition_type"), name="unique_leadership_role_record")),
        migrations.AddConstraint(model_name="leadershipdecisionrecord", constraint=models.UniqueConstraint(fields=("snapshot", "title", "decision_type", "decision_date"), name="unique_leadership_decision_record")),
    ]
