from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ingestion", "0002_rename_ingestion_i_job_typ_f7fd80_idx_ingestion_i_job_typ_d99d2e_idx_and_more"),
    ]

    operations = [
        TrigramExtension(),
    ]
