from django.urls import path

from apps.accounts import api


urlpatterns = [
    path("auth/signup", api.signup, name="auth-signup"),
    path("auth/login", api.login, name="auth-login"),
    path("auth/logout", api.logout, name="auth-logout"),
    path("auth/me", api.me, name="auth-me"),
    path("subscription", api.subscription, name="subscription"),
    path("subscription/change", api.subscription_change, name="subscription-change"),
    path("subscription/checkout", api.subscription_checkout, name="subscription-checkout"),
    path("subscription/verify-payment", api.subscription_verify_payment, name="subscription-verify-payment"),
    path("subscription/history", api.subscription_history, name="subscription-history"),
]
