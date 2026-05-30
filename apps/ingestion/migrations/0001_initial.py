from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SourceDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_api", models.CharField(max_length=64)),
                ("url", models.URLField(max_length=2048)),
                ("canonical_url", models.URLField(blank=True, max_length=2048)),
                ("title", models.CharField(max_length=1024)),
                ("publisher", models.CharField(blank=True, max_length=255)),
                ("published_date", models.DateTimeField(blank=True, null=True)),
                ("snippet", models.TextField(blank=True)),
                ("language", models.CharField(blank=True, max_length=32)),
                ("url_hash", models.CharField(max_length=64, unique=True)),
                ("title_hash", models.CharField(blank=True, db_index=True, max_length=64)),
                ("status", models.CharField(choices=[("DISCOVERED", "Discovered"), ("APPROVED", "Approved"), ("IGNORED", "Ignored"), ("DUPLICATE", "Duplicate"), ("EXTRACTION_PENDING", "Extraction pending"), ("EXTRACTED", "Extracted"), ("EXTRACTION_FAILED", "Extraction failed")], db_index=True, default="DISCOVERED", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_documents", to="companies.company")),
                ("duplicate_of", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="duplicates", to="ingestion.sourcedocument")),
            ],
            options={
                "ordering": ["-published_date", "title"],
            },
        ),
        migrations.CreateModel(
            name="ArticleExtraction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("clean_text", models.TextField(blank=True)),
                ("word_count", models.PositiveIntegerField(default=0)),
                ("extraction_status", models.CharField(choices=[("PENDING", "Pending"), ("SUCCEEDED", "Succeeded"), ("FAILED", "Failed"), ("SKIPPED", "Skipped")], db_index=True, default="PENDING", max_length=32)),
                ("extraction_error", models.TextField(blank=True)),
                ("extractor_name", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_document", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="article_extraction", to="ingestion.sourcedocument")),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="IngestionJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_type", models.CharField(choices=[("COMPANY_METADATA_SYNC", "Company metadata sync"), ("SOURCE_DISCOVERY", "Source discovery"), ("ARTICLE_EXTRACTION", "Article extraction"), ("EVENT_EXTRACTION", "Event extraction"), ("EVENT_CLUSTERING", "Event clustering"), ("FULL_COMPANY_PIPELINE", "Full company pipeline")], max_length=64)),
                ("query", models.TextField(blank=True)),
                ("source", models.CharField(blank=True, max_length=64)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("RUNNING", "Running"), ("SUCCEEDED", "Succeeded"), ("FAILED", "Failed"), ("PARTIAL", "Partial"), ("CANCELLED", "Cancelled")], db_index=True, default="PENDING", max_length=32)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("sources_found", models.PositiveIntegerField(default=0)),
                ("sources_inserted", models.PositiveIntegerField(default=0)),
                ("duplicates_skipped", models.PositiveIntegerField(default=0)),
                ("articles_extracted", models.PositiveIntegerField(default=0)),
                ("events_extracted", models.PositiveIntegerField(default=0)),
                ("turns_created", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ingestion_jobs", to="companies.company")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="sourcedocument",
            index=models.Index(fields=["company", "published_date"], name="ingestion_s_company_844e3e_idx"),
        ),
        migrations.AddIndex(
            model_name="sourcedocument",
            index=models.Index(fields=["company", "source_api"], name="ingestion_s_company_ec43bd_idx"),
        ),
        migrations.AddIndex(
            model_name="sourcedocument",
            index=models.Index(fields=["publisher", "published_date"], name="ingestion_s_publish_5249b0_idx"),
        ),
        migrations.AddIndex(
            model_name="ingestionjob",
            index=models.Index(fields=["job_type", "status"], name="ingestion_i_job_typ_f7fd80_idx"),
        ),
        migrations.AddIndex(
            model_name="ingestionjob",
            index=models.Index(fields=["company", "created_at"], name="ingestion_i_company_88fe78_idx"),
        ),
        migrations.AddIndex(
            model_name="ingestionjob",
            index=models.Index(fields=["source", "status"], name="ingestion_i_source_620bde_idx"),
        ),
    ]
