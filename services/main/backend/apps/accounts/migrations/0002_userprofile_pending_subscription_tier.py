from django.db import migrations, models


def repair_unverified_pending_checkouts(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    SubscriptionChangeLog = apps.get_model("accounts", "SubscriptionChangeLog")

    pending_profiles = UserProfile.objects.filter(
        subscription_status="PENDING_PAYMENT",
        razorpay_order_id__gt="",
        razorpay_payment_id="",
    )
    for profile in pending_profiles:
        checkout = (
            SubscriptionChangeLog.objects.filter(
                user_id=profile.user_id,
                provider="RAZORPAY",
                provider_order_id=profile.razorpay_order_id,
                reason="razorpay_checkout_created",
            )
            .order_by("-created_at", "-id")
            .first()
        )
        profile.pending_subscription_tier = profile.subscription_tier
        if checkout:
            profile.subscription_tier = checkout.old_tier
            profile.subscription_status = checkout.old_status
        elif profile.subscription_tier != "FREE":
            profile.subscription_tier = "FREE"
            profile.subscription_status = "FREE"
        profile.save(
            update_fields=[
                "subscription_tier",
                "subscription_status",
                "pending_subscription_tier",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="pending_subscription_tier",
            field=models.CharField(
                blank=True,
                choices=[
                    ("FREE", "Free"),
                    ("PRO", "Pro"),
                    ("ANALYST", "Analyst"),
                    ("ADMIN", "Admin"),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
        migrations.RunPython(repair_unverified_pending_checkouts, migrations.RunPython.noop),
    ]
