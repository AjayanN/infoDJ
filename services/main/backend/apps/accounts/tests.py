from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import SubscriptionChangeLog, SubscriptionStatus, SubscriptionTier, UserProfile
from apps.accounts.services import RazorpayOrder


TEST_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01"
    b"\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
)


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

    def test_signup_rejects_weak_password(self):
        response = self.client.post(
            "/api/app/auth/signup",
            {"username": "weak-password", "email": "weak@example.com", "password": "short"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "password does not meet security requirements")

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


class PasswordResetApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="resetme",
            email="resetme@example.com",
            password="OldPass123!",
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FRONTEND_BASE_URL="http://localhost:4200",
    )
    def test_password_reset_request_sends_email_for_existing_user(self):
        response = self.client.post(
            "/api/app/auth/password-reset/request",
            {"email": "resetme@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/reset-password?", mail.outbox[0].body)

    def test_password_reset_confirm_changes_password_and_invalidates_tokens(self):
        Token.objects.create(user=self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            "/api/app/auth/password-reset/confirm",
            {"uid": uid, "token": token, "password": "NewSecurePass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePass123!"))
        self.assertEqual(Token.objects.filter(user=self.user).count(), 0)


class GoogleOAuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET="")
    def test_google_auth_url_requires_configuration(self):
        response = self.client.get("/api/app/auth/google/url")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Google OAuth credentials", response.data["error"])

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
        GOOGLE_OAUTH_REDIRECT_URI="http://localhost:8080/api/app/auth/google/callback",
        FRONTEND_BASE_URL="http://localhost:4200",
    )
    @patch("apps.accounts.api.exchange_google_code_for_profile")
    def test_google_callback_creates_user_and_redirects_with_token(self, exchange_profile):
        exchange_profile.return_value = {
            "email": "googleuser@example.com",
            "name": "Google User",
            "given_name": "Google",
            "family_name": "User",
        }

        auth_response = self.client.get("/api/app/auth/google/url")
        state = parse_qs(urlparse(auth_response.data["auth_url"]).query)["state"][0]
        response = self.client.get(f"/api/app/auth/google/callback?code=test-code&state={state}")

        self.assertEqual(response.status_code, 302)
        self.assertIn("http://localhost:4200/auth/callback#token=", response["Location"])
        user = get_user_model().objects.get(email="googleuser@example.com")
        self.assertEqual(user.profile.display_name, "Google User")

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="client-id", GOOGLE_OAUTH_CLIENT_SECRET="client-secret")
    def test_google_callback_rejects_missing_or_invalid_state(self):
        response = self.client.get("/api/app/auth/google/callback?code=test-code")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid Google OAuth state")


class FounderContextApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="founder-context",
            email="context@example.com",
            password="StrongPass123!",
        )
        UserProfile.objects.create(user=self.user)
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_founder_context_persists_and_returns_sector_stage_playbook(self):
        response = self.client.patch(
            "/api/app/founder-context",
            {
                "company_name": "Northstar Energy",
                "founder_sector": "Energy",
                "founder_business_type": "Carbon management software",
                "founder_stage": "build",
                "founder_objective": "build_product",
                "founder_geography": "United States",
                "founder_target_customer": "Industrial operators",
                "founder_revenue_model": "Subscription",
                "founder_constraints": "Limited engineering capacity",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["founder_context"]["company_name"], "Northstar Energy")
        self.assertEqual(response.data["founder_context"]["stage"], "build")
        self.assertEqual(response.data["playbook"]["stage_question"], "What is the smallest workflow customers will repeatedly use?")
        self.assertIn("Commodity exposure", response.data["playbook"]["risks"])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.company_name, "Northstar Energy")
        self.assertEqual(self.user.profile.founder_sector, "Energy")

    def test_founder_context_rejects_invalid_stage(self):
        response = self.client.patch("/api/app/founder-context", {"founder_stage": "hypergrowth"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid founder_stage")

    def test_founder_playbook_uses_requested_pilot_sector(self):
        response = self.client.get("/api/app/founder-playbook?sector=Communication%20Services&stage=launch")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["playbook"]["sector_label"], "Communication")
        self.assertIn("Advertising", response.data["playbook"]["monetisation_models"])

    def test_founder_playbook_covers_each_supported_sector(self):
        expected_labels = {
            "Financials": "Financial services",
            "Health Care": "Health care",
            "Consumer Discretionary": "Consumer",
            "Consumer Staples": "Consumer staples",
            "Industrials": "Industrials",
            "Materials": "Materials",
            "Real Estate": "Real estate",
            "Utilities": "Utilities",
        }

        for sector, label in expected_labels.items():
            response = self.client.get("/api/app/founder-playbook", {"sector": sector, "stage": "validate"})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["playbook"]["sector_label"], label)
            self.assertTrue(response.data["playbook"]["questions"])
            self.assertTrue(response.data["playbook"]["source_requirements"])


class FounderDecisionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="founder-decisions",
            email="decisions@example.com",
            password="StrongPass123!",
        )
        UserProfile.objects.create(user=self.user, founder_sector="Energy", founder_stage="build")
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    @patch("apps.accounts.api.ingestion_get")
    def test_founder_decision_returns_only_source_linked_sector_evidence(self, ingestion_get):
        ingestion_get.side_effect = [
            ({"companies": [
                {"slug": "exxonmobil", "sector": "Energy"},
                {"slug": "netflix", "sector": "Communication Services"},
            ]}, ""),
            ({"latest_events": [
                {
                    "id": 1, "company": "ExxonMobil", "company_slug": "exxonmobil",
                    "event_date": "2026-02-18", "event_type": "PRODUCT_EXPANSION",
                    "actual_change": "Expanded a source-backed project.",
                    "confidence_score": 0.9,
                    "source": {"title": "ExxonMobil 10-K", "url": "https://example.com/exxon", "published_date": "2026-02-18"},
                    "quality": {"eligible": True},
                    "lifecycle_timing": {"eligible": True, "action_date": "2014-04-03", "action_date_precision": "DAY", "action_date_evidence": "The project began on April 3, 2014.", "founded_date": "2013-07-01", "company_age_days": 276, "company_lifecycle_stage": "LAUNCH", "company_lifecycle_stage_evidence": "The project launched in its first year.", "company_lifecycle_stage_source_url": "https://example.com/exxon", "context": {"as_of_date": "2014-12-31", "source_url": "https://example.com/exxon", "metrics": [{"label": "Revenue", "value": "$394bn"}]}},
                },
                {
                    "id": 2, "company": "Chevron", "company_slug": "chevron",
                    "event_date": "2026-02-18", "event_type": "PRODUCT_EXPANSION",
                    "actual_change": "Same-sector event without lifecycle proof.",
                    "confidence_score": 0.9,
                    "source": {"title": "Chevron 10-K", "url": "https://example.com/chevron", "published_date": "2026-02-18"},
                    "quality": {"eligible": True},
                    "lifecycle_timing": {"eligible": False, "reasons": ["missing_actual_action_date"]},
                },
                {
                    "id": 3, "company": "Netflix", "company_slug": "netflix",
                    "event_date": "2026-02-18", "event_type": "REVENUE_MODEL_EXPANSION",
                    "actual_change": "Irrelevant sector event.",
                    "confidence_score": 0.9,
                    "source": {"title": "Netflix 10-K", "url": "https://example.com/netflix", "published_date": "2026-02-18"},
                    "quality": {"eligible": True},
                },
            ], "risk_signals": []}, ""),
        ]

        response = self.client.get("/api/app/founder-decision")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "available")
        self.assertEqual(response.data["coverage"]["comparable_event_count"], 1)
        self.assertEqual(response.data["journey"][0]["company_slug"], "exxonmobil")
        self.assertEqual(response.data["journey"][0]["lifecycle_timing"]["action_date"], "2014-04-03")
        self.assertEqual(response.data["journey"][0]["lifecycle_timing"]["action_date_precision"], "DAY")
        self.assertEqual(response.data["journey"][0]["lifecycle_timing"]["company_age_days"], 276)
        self.assertEqual(response.data["directions"][0]["claim_type"], "founder_hypothesis")
        self.assertEqual(response.data["directions"][0]["evidence"][0]["claim_type"], "reported_fact")
        self.assertEqual(response.data["directions"][0]["company_names"], ["ExxonMobil"])
        self.assertIn("source-linked moves", response.data["directions"][0]["reasoning"])
        passport = {item["label"]: item for item in response.data["coverage_passport"]}
        self.assertEqual(passport["Comparable moves"]["count"], 1)
        self.assertEqual(passport["Comparable moves"]["last_observed_on"], "2026-02-18")
        self.assertEqual(passport["Source diversity"]["evidence_strength"], "weak")

    @patch("apps.accounts.api.ingestion_get")
    def test_founder_decision_uses_historical_events_outside_latest_feed(self, ingestion_get):
        ingestion_get.side_effect = [
            ({"companies": [{"slug": "exxonmobil", "sector": "Energy"}]}, ""),
            ({"latest_events": [], "historical_events": [{
                "id": 8, "company": "ExxonMobil", "company_slug": "exxonmobil",
                "event_date": "2014-04-03", "event_type": "PRODUCT_EXPANSION",
                "actual_change": "Launched a source-backed product.",
                "source": {"title": "Primary announcement", "url": "https://example.com/exxon"},
                "quality": {"eligible": True},
                "lifecycle_timing": {
                    "eligible": True, "action_date": "2014-04-03", "action_date_precision": "DAY",
                    "company_age_days": 276, "company_lifecycle_stage": "LAUNCH",
                },
            }], "risk_signals": []}, ""),
        ]

        response = self.client.get("/api/app/founder-decision")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "available")
        self.assertEqual(response.data["coverage"]["comparable_event_count"], 1)
        self.assertEqual(response.data["journey"][0]["id"], 8)

    @patch("apps.accounts.api.ingestion_get")
    def test_founder_decision_rejects_a_mature_company_move_for_build_stage(self, ingestion_get):
        ingestion_get.side_effect = [
            ({"companies": [{"slug": "microsoft", "sector": "Energy"}]}, ""),
            ({"latest_events": [{
                "id": 9, "company": "Microsoft", "company_slug": "microsoft",
                "event_date": "2026-07-21", "event_type": "PARTNERSHIP",
                "actual_change": "Expanded a strategic partnership.",
                "source": {"title": "Microsoft announcement", "url": "https://example.com/microsoft"},
                "quality": {"eligible": True},
                "lifecycle_timing": {
                    "eligible": True, "action_date": "2026-07-21", "company_age_days": 18736,
                    "company_lifecycle_stage": "MATURITY",
                    "company_lifecycle_stage_evidence": "The company was an established global business.",
                    "company_lifecycle_stage_source_url": "https://example.com/microsoft",
                    "context": {"as_of_date": "2026-06-30", "source_url": "https://example.com/microsoft", "metrics": [{"label": "Revenue", "value": "$241.8bn"}]},
                },
            }], "risk_signals": []}, ""),
        ]

        response = self.client.get("/api/app/founder-decision")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "insufficient_evidence")
        self.assertEqual(response.data["coverage"]["comparable_event_count"], 0)
        self.assertIn("stage-matched", response.data["source_gaps"][0]["reason"])


    @patch("apps.accounts.api.ingestion_get")
    def test_founder_decision_abstains_when_sector_evidence_is_missing(self, ingestion_get):
        ingestion_get.side_effect = [
            ({"companies": [{"slug": "netflix", "sector": "Communication Services"}]}, ""),
            ({"latest_events": [], "risk_signals": []}, ""),
        ]

        response = self.client.get("/api/app/founder-decision")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "insufficient_evidence")
        self.assertEqual(response.data["directions"][0]["evidence_status"], "unavailable")
        self.assertTrue(response.data["source_gaps"])

    def test_founder_context_accepts_frontend_field_names(self):
        response = self.client.patch(
            "/api/app/founder-context",
            {
                "company_name": "Northstar Energy",
                "sector": "Energy",
                "business_type": "Carbon management software",
                "stage": "build",
                "objective": "build_product",
                "geography": "United States",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["founder_context"]["sector"], "Energy")
        self.assertEqual(response.data["founder_context"]["stage"], "build")
        self.assertEqual(response.data["founder_context"]["objective"], "build_product")
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.founder_business_type, "Carbon management software")


class ProfileAvatarApiTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root, MEDIA_URL="/media/")
        self.override.enable()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="avataruser",
            email="avataruser@example.com",
            password="StrongPass123!",
        )
        UserProfile.objects.create(user=self.user)
        token, _created = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_avatar_upload_persists_and_me_returns_url(self):
        response = self.client.post(
            "/api/app/profile/avatar",
            {"avatar": SimpleUploadedFile("avatar.png", TEST_PNG_BYTES, content_type="image/png")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        avatar_url = response.data["user"]["profile"]["avatar_url"]
        self.assertIn("/media/avatars/", avatar_url)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar.name.startswith("avatars/"))

        me_response = self.client.get("/api/app/auth/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["user"]["profile"]["avatar_url"], avatar_url)

    def test_avatar_upload_rejects_non_image_extension(self):
        response = self.client.post(
            "/api/app/profile/avatar",
            {"avatar": SimpleUploadedFile("avatar.txt", b"not an image", content_type="text/plain")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("avatar must be", response.data["error"])
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)

    def test_avatar_delete_clears_profile_and_file(self):
        upload_response = self.client.post(
            "/api/app/profile/avatar",
            {"avatar": SimpleUploadedFile("avatar.png", TEST_PNG_BYTES, content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, 200)
        self.user.profile.refresh_from_db()
        saved_path = self.user.profile.avatar.path

        response = self.client.delete("/api/app/profile/avatar")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["profile"]["avatar_url"], "")
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)
        self.assertFalse(Path(saved_path).exists())


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
        self.assertEqual(self.user.profile.subscription_tier, SubscriptionTier.FREE)
        self.assertEqual(self.user.profile.subscription_status, SubscriptionStatus.FREE)
        self.assertEqual(self.user.profile.pending_subscription_tier, SubscriptionTier.PRO)
        self.assertEqual(self.user.profile.razorpay_order_id, "order_test123")

    @override_settings(RAZORPAY_KEY_SECRET="secret")
    def test_verify_payment_rejects_invalid_signature(self):
        profile = self.user.profile
        profile.subscription_tier = SubscriptionTier.FREE
        profile.subscription_status = SubscriptionStatus.FREE
        profile.pending_subscription_tier = SubscriptionTier.PRO
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
        self.assertEqual(profile.subscription_tier, SubscriptionTier.FREE)
        self.assertEqual(profile.subscription_status, SubscriptionStatus.FREE)
        self.assertEqual(profile.pending_subscription_tier, SubscriptionTier.PRO)

    @override_settings(RAZORPAY_KEY_SECRET="secret")
    def test_verify_payment_promotes_pending_tier_only_after_signature_passes(self):
        profile = self.user.profile
        profile.subscription_tier = SubscriptionTier.FREE
        profile.subscription_status = SubscriptionStatus.FREE
        profile.pending_subscription_tier = SubscriptionTier.PRO
        profile.razorpay_order_id = "order_test123"
        profile.save()
        signature = "8645d0ec07e3574862b139c4524ea5518ba0e49ad552ec84b14c897c727100c6"

        response = self.client.post(
            "/api/app/subscription/verify-payment",
            {
                "razorpay_order_id": "order_test123",
                "razorpay_payment_id": "pay_test123",
                "razorpay_signature": signature,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.subscription_tier, SubscriptionTier.PRO)
        self.assertEqual(profile.subscription_status, SubscriptionStatus.ACTIVE)
        self.assertEqual(profile.pending_subscription_tier, "")
        change = SubscriptionChangeLog.objects.filter(reason="razorpay_payment_verified").get()
        self.assertEqual(change.old_tier, SubscriptionTier.FREE)
        self.assertEqual(change.new_tier, SubscriptionTier.PRO)
