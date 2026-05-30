from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(blank=True, max_length=255, unique=True)),
                ("aliases", models.JSONField(blank=True, default=list)),
                ("industry", models.CharField(blank=True, max_length=255)),
                ("country", models.CharField(blank=True, max_length=255)),
                ("wikidata_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("sec_cik", models.CharField(blank=True, db_index=True, max_length=32)),
                ("website", models.URLField(blank=True)),
                ("founded_date", models.DateField(blank=True, null=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name_plural": "companies",
                "ordering": ["name"],
            },
        ),
    ]
