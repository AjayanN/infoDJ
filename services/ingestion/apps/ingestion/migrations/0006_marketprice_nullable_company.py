from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
        ("ingestion", "0005_marketprice_financialfact"),
    ]

    operations = [
        migrations.AlterField(
            model_name="marketprice",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="market_prices",
                to="companies.company",
            ),
        ),
    ]
