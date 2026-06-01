# Generated for Sprint 1 auth/subscription models.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionChangeLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "old_tier",
                    models.CharField(
                        choices=[
                            ("FREE", "Free"),
                            ("PRO", "Pro"),
                            ("ANALYST", "Analyst"),
                            ("ADMIN", "Admin"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "new_tier",
                    models.CharField(
                        choices=[
                            ("FREE", "Free"),
                            ("PRO", "Pro"),
                            ("ANALYST", "Analyst"),
                            ("ADMIN", "Admin"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "old_status",
                    models.CharField(
                        choices=[
                            ("FREE", "Free"),
                            ("PENDING_PAYMENT", "Pending payment"),
                            ("ACTIVE", "Active"),
                            ("PAST_DUE", "Past due"),
                            ("CANCELLED", "Cancelled"),
                            ("DOWNGRADED", "Downgraded"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "new_status",
                    models.CharField(
                        choices=[
                            ("FREE", "Free"),
                            ("PENDING_PAYMENT", "Pending payment"),
                            ("ACTIVE", "Active"),
                            ("PAST_DUE", "Past due"),
                            ("CANCELLED", "Cancelled"),
                            ("DOWNGRADED", "Downgraded"),
                        ],
                        max_length=32,
                    ),
                ),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("provider", models.CharField(default="INTERNAL", max_length=64)),
                ("provider_order_id", models.CharField(blank=True, max_length=128)),
                ("provider_payment_id", models.CharField(blank=True, max_length=128)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(blank=True, max_length=255)),
                ("company_name", models.CharField(blank=True, max_length=255)),
                ("role", models.CharField(blank=True, max_length=255)),
                (
                    "subscription_tier",
                    models.CharField(
                        choices=[
                            ("FREE", "Free"),
                            ("PRO", "Pro"),
                            ("ANALYST", "Analyst"),
                            ("ADMIN", "Admin"),
                        ],
                        db_index=True,
                        default="FREE",
                        max_length=32,
                    ),
                ),
                (
                    "subscription_status",
                    models.CharField(
                        choices=[
                            ("FREE", "Free"),
                            ("PENDING_PAYMENT", "Pending payment"),
                            ("ACTIVE", "Active"),
                            ("PAST_DUE", "Past due"),
                            ("CANCELLED", "Cancelled"),
                            ("DOWNGRADED", "Downgraded"),
                        ],
                        db_index=True,
                        default="FREE",
                        max_length=32,
                    ),
                ),
                ("razorpay_order_id", models.CharField(blank=True, max_length=128)),
                ("razorpay_payment_id", models.CharField(blank=True, max_length=128)),
                ("razorpay_subscription_id", models.CharField(blank=True, max_length=128)),
                ("email_updates_enabled", models.BooleanField(default=True)),
                ("product_updates_enabled", models.BooleanField(default=True)),
                ("research_digest_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
