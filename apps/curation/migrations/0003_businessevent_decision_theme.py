from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curation", "0002_rename_curation_bu_company_fa4401_idx_curation_bu_company_29d57b_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessevent",
            name="decision_theme",
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
    ]
