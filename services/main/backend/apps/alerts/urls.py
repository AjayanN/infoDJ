from django.urls import path

from apps.alerts import api


urlpatterns = [
    path("watchlists", api.watchlists, name="app-watchlists"),
    path("watchlists/follow-company", api.follow_company, name="app-watchlist-follow-company"),
    path("watchlists/<int:watchlist_id>", api.watchlist_detail, name="app-watchlist-detail"),
    path("watchlists/<int:watchlist_id>/items", api.watchlist_items, name="app-watchlist-items"),
    path("watchlists/<int:watchlist_id>/rules/<str:category>", api.watchlist_rule, name="app-watchlist-rule"),
    path("notifications", api.notifications, name="app-notifications"),
    path("notifications/refresh", api.refresh_notifications, name="app-notifications-refresh"),
    path("notifications/<int:notification_id>", api.notification_detail, name="app-notification-detail"),
    path("notifications/<int:notification_id>/feedback", api.notification_feedback, name="app-notification-feedback"),
    path("notifications/delivery-preference", api.delivery_preference, name="app-alert-delivery-preference"),
    path("briefings", api.briefings, name="app-briefings"),
    path("briefings/<int:briefing_id>", api.briefing_detail, name="app-briefing-detail"),
    path("briefings/<int:briefing_id>/feedback", api.briefing_feedback_view, name="app-briefing-feedback"),
]
