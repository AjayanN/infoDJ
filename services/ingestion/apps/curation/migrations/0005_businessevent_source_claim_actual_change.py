from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curation", "0004_add_negative_event_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessevent",
            name="source_claim",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="businessevent",
            name="actual_change",
            field=models.TextField(blank=True),
        ),
    ]
