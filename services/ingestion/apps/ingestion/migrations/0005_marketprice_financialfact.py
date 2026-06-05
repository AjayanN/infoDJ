# Generated for dashboard market and financial fact ingestion.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
        ("ingestion", "0004_sourcegap"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinancialFact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("taxonomy", models.CharField(db_index=True, max_length=64)),
                ("concept", models.CharField(db_index=True, max_length=128)),
                ("label", models.CharField(blank=True, max_length=255)),
                ("unit", models.CharField(db_index=True, max_length=64)),
                ("fy", models.IntegerField(blank=True, db_index=True, null=True)),
                ("fp", models.CharField(blank=True, db_index=True, max_length=16)),
                ("filed", models.DateField(blank=True, db_index=True, null=True)),
                ("frame", models.CharField(blank=True, db_index=True, max_length=64)),
                ("value", models.DecimalField(decimal_places=3, max_digits=24)),
                ("accession_number", models.CharField(blank=True, max_length=64)),
                ("raw", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="financial_facts",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "ordering": ["company", "concept", "-fy", "-filed"],
            },
        ),
        migrations.CreateModel(
            name="MarketPrice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ticker", models.CharField(db_index=True, max_length=32)),
                ("provider", models.CharField(db_index=True, default="STOOQ", max_length=64)),
                ("price_date", models.DateField(db_index=True)),
                ("open_price", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("high_price", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("low_price", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("close_price", models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ("volume", models.BigIntegerField(blank=True, null=True)),
                ("raw", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="market_prices",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "ordering": ["company", "-price_date"],
            },
        ),
        migrations.AddConstraint(
            model_name="financialfact",
            constraint=models.UniqueConstraint(
                fields=("company", "taxonomy", "concept", "unit", "fy", "fp", "frame", "filed", "accession_number"),
                name="unique_financial_fact_period",
            ),
        ),
        migrations.AddIndex(
            model_name="financialfact",
            index=models.Index(fields=["company", "concept", "fy"], name="ingestion_f_company_084884_idx"),
        ),
        migrations.AddIndex(
            model_name="financialfact",
            index=models.Index(fields=["company", "filed"], name="ingestion_f_company_c533d2_idx"),
        ),
        migrations.AddIndex(
            model_name="financialfact",
            index=models.Index(fields=["concept", "unit"], name="ingestion_f_concept_6edade_idx"),
        ),
        migrations.AddConstraint(
            model_name="marketprice",
            constraint=models.UniqueConstraint(
                fields=("company", "ticker", "provider", "price_date"),
                name="unique_market_price_day",
            ),
        ),
        migrations.AddIndex(
            model_name="marketprice",
            index=models.Index(fields=["company", "price_date"], name="ingestion_m_company_845a6e_idx"),
        ),
        migrations.AddIndex(
            model_name="marketprice",
            index=models.Index(fields=["ticker", "price_date"], name="ingestion_m_ticker_61d7e0_idx"),
        ),
        migrations.AddIndex(
            model_name="marketprice",
            index=models.Index(fields=["provider", "price_date"], name="ingestion_m_provide_7482b0_idx"),
        ),
    ]
