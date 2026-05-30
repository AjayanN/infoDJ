from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curation", "0003_businessevent_decision_theme"),
    ]

    operations = [
        migrations.AlterField(
            model_name="businessevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("BUSINESS_MODEL_PIVOT", "Business model pivot"),
                    ("PRICING_CHANGE", "Pricing change"),
                    ("PRODUCT_EXPANSION", "Product expansion"),
                    ("GEOGRAPHIC_EXPANSION", "Geographic expansion"),
                    ("CUSTOMER_SEGMENT_SHIFT", "Customer segment shift"),
                    ("DISTRIBUTION_CHANNEL_SHIFT", "Distribution channel shift"),
                    ("FUNDING_EVENT", "Funding event"),
                    ("ACQUISITION", "Acquisition"),
                    ("PARTNERSHIP", "Partnership"),
                    ("LEADERSHIP_CHANGE", "Leadership change"),
                    ("REGULATORY_RESPONSE", "Regulatory response"),
                    ("CRISIS_RESPONSE", "Crisis response"),
                    ("COMPETITIVE_RESPONSE", "Competitive response"),
                    ("BRAND_REPOSITIONING", "Brand repositioning"),
                    ("REVENUE_MODEL_EXPANSION", "Revenue model expansion"),
                    ("PERFORMANCE_DECLINE", "Performance decline"),
                    ("COST_RESTRUCTURING", "Cost restructuring"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="strategicturn",
            name="turn_type",
            field=models.CharField(
                choices=[
                    ("BUSINESS_MODEL_PIVOT", "Business model pivot"),
                    ("PRICING_CHANGE", "Pricing change"),
                    ("PRODUCT_EXPANSION", "Product expansion"),
                    ("GEOGRAPHIC_EXPANSION", "Geographic expansion"),
                    ("CUSTOMER_SEGMENT_SHIFT", "Customer segment shift"),
                    ("DISTRIBUTION_CHANNEL_SHIFT", "Distribution channel shift"),
                    ("FUNDING_EVENT", "Funding event"),
                    ("ACQUISITION", "Acquisition"),
                    ("PARTNERSHIP", "Partnership"),
                    ("LEADERSHIP_CHANGE", "Leadership change"),
                    ("REGULATORY_RESPONSE", "Regulatory response"),
                    ("CRISIS_RESPONSE", "Crisis response"),
                    ("COMPETITIVE_RESPONSE", "Competitive response"),
                    ("BRAND_REPOSITIONING", "Brand repositioning"),
                    ("REVENUE_MODEL_EXPANSION", "Revenue model expansion"),
                    ("PERFORMANCE_DECLINE", "Performance decline"),
                    ("COST_RESTRUCTURING", "Cost restructuring"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
    ]
