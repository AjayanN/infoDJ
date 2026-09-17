from django.urls import path

from apps.accounts import api


urlpatterns = [
    path("auth/signup", api.signup, name="auth-signup"),
    path("auth/login", api.login, name="auth-login"),
    path("auth/logout", api.logout, name="auth-logout"),
    path("auth/me", api.me, name="auth-me"),
    path("auth/password-reset/request", api.password_reset_request, name="auth-password-reset-request"),
    path("auth/password-reset/confirm", api.password_reset_confirm, name="auth-password-reset-confirm"),
    path("auth/google/url", api.google_auth_url, name="auth-google-url"),
    path("auth/google/callback", api.google_callback, name="auth-google-callback"),
    path("founder-decision", api.founder_decision, name="founder-decision"),
    path("founder-story-brackets", api.founder_story_brackets, name="founder-story-brackets"),
    path("founder-context", api.founder_context, name="founder-context"),
    path("founder-playbook", api.founder_playbook, name="founder-playbook"),
    path("profile/avatar", api.profile_avatar, name="profile-avatar"),
    path("subscription", api.subscription, name="subscription"),
    path("subscription/change", api.subscription_change, name="subscription-change"),
    path("subscription/checkout", api.subscription_checkout, name="subscription-checkout"),
    path("subscription/verify-payment", api.subscription_verify_payment, name="subscription-verify-payment"),
    path("subscription/history", api.subscription_history, name="subscription-history"),
    path("history/documents", api.history_document_upload, name="history-document-upload"),
]
