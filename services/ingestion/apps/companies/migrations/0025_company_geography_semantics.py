from django.db import migrations, models


def copy_legacy_country_to_headquarters(apps, schema_editor):
    Company = apps.get_model("companies", "Company")
    Company.objects.filter(headquarters_country="").exclude(country="").update(headquarters_country=models.F("country"))


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0024_insider_transaction_filing_identity"),
    ]

    operations = [
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
        migrations.RunPython(copy_legacy_country_to_headquarters, migrations.RunPython.noop),
    ]
