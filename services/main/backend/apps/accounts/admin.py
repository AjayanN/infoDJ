from django.contrib import admin

from apps.accounts.models import SubscriptionChangeLog, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "subscription_tier",
        "subscription_status",
        "email_updates_enabled",
        "updated_at",
    )
    list_filter = ("subscription_tier", "subscription_status", "email_updates_enabled")
    search_fields = ("user__username", "user__email", "display_name", "company_name")


@admin.register(SubscriptionChangeLog)
class SubscriptionChangeLogAdmin(admin.ModelAdmin):
    list_display = ("user", "old_tier", "new_tier", "provider", "created_at")
    list_filter = ("provider", "old_tier", "new_tier")
    search_fields = ("user__username", "user__email", "provider_order_id", "provider_payment_id")
