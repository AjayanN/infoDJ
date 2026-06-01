from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import SubscriptionChangeLog, SubscriptionStatus, SubscriptionTier, UserProfile
from apps.accounts.services import RazorpayOrder


class AccountAuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_signup_creates_user_profile_and_token(self):
        response = self.client.post(
            "/api/app/auth/signup",
            {
                "username": "founder1",
                "email": "founder1@example.com",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["subscription"]["tier"], SubscriptionTier.FREE)
        user = get_user_model().objects.get(username="founder1")
        self.assertEqual(user.profile.subscription_status, SubscriptionStatus.FREE)

    def test_login_returns_token_and_me_requires_token(self):
        user = get_user_model().objects.create_user(
            username="founder2",
            email="founder2@example.com",
            password="StrongPass123!",
        )

        login_response = self.client.post(
            "/api/app/auth/login",
            {"username": "founder2", "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)
        token = login_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        me_response = self.client.get("/api/app/auth/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["user"]["email"], user.email)


class SubscriptionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="subscriber",
            email="subscriber@example.com",
            password="StrongPass123!",
        )
        UserProfile.objects.create(user=self.user)
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_manual_subscription_change_writes_history(self):
        response = self.client.post(
            "/api/app/subscription/change",
            {"tier": "PRO", "reason": "test_upgrade"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["subscription"]["tier"], SubscriptionTier.PRO)
        self.assertEqual(response.data["subscription"]["status"], SubscriptionStatus.ACTIVE)
        change = SubscriptionChangeLog.objects.get(user=self.user)
        self.assertEqual(change.old_tier, SubscriptionTier.FREE)
        self.assertEqual(change.new_tier, SubscriptionTier.PRO)
        self.assertEqual(change.provider, "INTERNAL")

    def test_invalid_subscription_tier_is_rejected(self):
        response = self.client.post(
            "/api/app/subscription/change",
            {"tier": "ENTERPRISE_PLUS"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(SubscriptionChangeLog.objects.count(), 0)

    @override_settings(RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="secret")
    @patch("apps.accounts.api.RazorpayClient.create_order")
    def test_checkout_creates_pending_razorpay_subscription(self, create_order):
        create_order.return_value = RazorpayOrder(
            id="order_test123",
            amount=99900,
            currency="INR",
            receipt="infodj-u1-pro",
            raw={"id": "order_test123", "amount": 99900, "currency": "INR"},
        )

        response = self.client.post(
            "/api/app/subscription/checkout",
            {"tier": "PRO"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["razorpay"]["order_id"], "order_test123")
        self.assertEqual(response.data["razorpay"]["key_id"], "rzp_test_key")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.subscription_status, SubscriptionStatus.PENDING_PAYMENT)
        self.assertEqual(self.user.profile.razorpay_order_id, "order_test123")

    @override_settings(RAZORPAY_KEY_SECRET="secret")
    def test_verify_payment_rejects_invalid_signature(self):
        profile = self.user.profile
        profile.subscription_tier = SubscriptionTier.PRO
        profile.subscription_status = SubscriptionStatus.PENDING_PAYMENT
        profile.razorpay_order_id = "order_test123"
        profile.save()

        response = self.client.post(
            "/api/app/subscription/verify-payment",
            {
                "razorpay_order_id": "order_test123",
                "razorpay_payment_id": "pay_test123",
                "razorpay_signature": "bad-signature",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid payment signature")
        profile.refresh_from_db()
        self.assertEqual(profile.subscription_status, SubscriptionStatus.PENDING_PAYMENT)
