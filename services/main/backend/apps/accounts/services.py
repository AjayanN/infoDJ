from __future__ import annotations

import hmac
from dataclasses import dataclass
from hashlib import sha256

import requests
from django.conf import settings

from apps.accounts.models import SubscriptionTier


TIER_PRICES_INR = {
    SubscriptionTier.PRO: 999,
    SubscriptionTier.ANALYST: 2499,
}


@dataclass(frozen=True)
class RazorpayOrder:
    id: str
    amount: int
    currency: str
    receipt: str
    raw: dict


class RazorpayConfigurationError(RuntimeError):
    pass


class RazorpayClient:
    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.base_url = settings.RAZORPAY_API_BASE_URL.rstrip("/")
        if not self.key_id or not self.key_secret:
            raise RazorpayConfigurationError("Razorpay credentials are not configured.")

    def create_order(self, *, user_id: int, tier: str) -> RazorpayOrder:
        if tier not in TIER_PRICES_INR:
            raise ValueError("Unsupported paid subscription tier.")
        amount_paise = TIER_PRICES_INR[tier] * 100
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"infodj-u{user_id}-{tier.lower()}",
            "notes": {
                "user_id": str(user_id),
                "subscription_tier": tier,
                "service": "InfoDJ",
            },
        }
        response = requests.post(
            f"{self.base_url}/orders",
            json=payload,
            auth=(self.key_id, self.key_secret),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return RazorpayOrder(
            id=str(data["id"]),
            amount=int(data["amount"]),
            currency=str(data["currency"]),
            receipt=str(data.get("receipt") or payload["receipt"]),
            raw=data,
        )


def verify_razorpay_payment_signature(*, order_id: str, payment_id: str, signature: str) -> bool:
    secret = settings.RAZORPAY_KEY_SECRET
    if not secret:
        raise RazorpayConfigurationError("Razorpay credentials are not configured.")
    message = f"{order_id}|{payment_id}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message, sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
