from django.db import migrations, models


def copy_legacy_country_to_headquarters(apps, schema_editor):
    Company = apps.get_model("companies", "Company")
    Company.objects.filter(headquarters_country="").exclude(country="").update(headquarters_country=models.F("country"))


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0024_insider_transaction_filing_identity"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE companies_company ADD COLUMN IF NOT EXISTS headquarters_country varchar(255) NOT NULL DEFAULT '';",
                    "ALTER TABLE companies_company DROP COLUMN IF EXISTS headquarters_country;",
                ),
                migrations.RunSQL(
                    "ALTER TABLE companies_companyprofilesnapshot ADD COLUMN IF NOT EXISTS operating_regions jsonb NOT NULL DEFAULT '[]';",
                    "ALTER TABLE companies_companyprofilesnapshot DROP COLUMN IF EXISTS operating_regions;",
                ),
                migrations.RunSQL(
                    "ALTER TABLE companies_companyprofilesnapshot ADD COLUMN IF NOT EXISTS revenue_geographies jsonb NOT NULL DEFAULT '[]';",
                    "ALTER TABLE companies_companyprofilesnapshot DROP COLUMN IF EXISTS revenue_geographies;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="company",
                    name="headquarters_country",
                    field=models.CharField(blank=True, max_length=255),
                ),
                migrations.AddField(
                    model_name="companyprofilesnapshot",
                    name="operating_regions",
                    field=models.JSONField(blank=True, default=list),
                ),
                migrations.AddField(
                    model_name="companyprofilesnapshot",
                    name="revenue_geographies",
                    field=models.JSONField(blank=True, default=list),
                ),
            ],
        ),
        migrations.RunPython(copy_legacy_country_to_headquarters, migrations.RunPython.noop),
    ]
