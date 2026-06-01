from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import (
    SubscriptionChangeLog,
    SubscriptionStatus,
    SubscriptionTier,
    UserProfile,
)
from apps.accounts.services import (
    RazorpayClient,
    RazorpayConfigurationError,
    TIER_PRICES_INR,
    verify_razorpay_payment_signature,
)


User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    username = (request.data.get("username") or "").strip()
    email = (request.data.get("email") or "").strip()
    password = request.data.get("password") or ""
    if not username or not email or not password:
        return Response({"error": "username, email, and password are required"}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({"error": "username already exists"}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({"error": "email already exists"}, status=400)
    user = User.objects.create_user(username=username, email=email, password=password)
    profile = ensure_profile(user)
    token, _created = Token.objects.get_or_create(user=user)
    return Response(
        {
            "token": token.key,
            "user": serialize_user(user, profile),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username") or request.data.get("email") or ""
    password = request.data.get("password") or ""
    user = authenticate(username=username, password=password)
    if user is None:
        return Response({"error": "invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
    profile = ensure_profile(user)
    token, _created = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": serialize_user(user, profile)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"status": "logged_out"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    profile = ensure_profile(request.user)
    return Response({"user": serialize_user(request.user, profile)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription(request):
    profile = ensure_profile(request.user)
    return Response({"subscription": serialize_subscription(profile)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscription_change(request):
    requested_tier = (request.data.get("tier") or "").strip().upper()
    if requested_tier not in SubscriptionTier.values:
        return Response({"error": "invalid subscription tier"}, status=400)
    profile = ensure_profile(request.user)
    old_tier = profile.subscription_tier
    old_status = profile.subscription_status
    profile.subscription_tier = requested_tier
    profile.subscription_status = (
        SubscriptionStatus.FREE if requested_tier == SubscriptionTier.FREE else SubscriptionStatus.ACTIVE
    )
    profile.save()
    log_subscription_change(
        user=request.user,
        old_tier=old_tier,
        new_tier=profile.subscription_tier,
        old_status=old_status,
        new_status=profile.subscription_status,
        reason=request.data.get("reason") or "manual_change",
        provider="INTERNAL",
    )
    return Response({"subscription": serialize_subscription(profile)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscription_checkout(request):
    requested_tier = (request.data.get("tier") or "").strip().upper()
    if requested_tier not in TIER_PRICES_INR:
        return Response({"error": "checkout is available for paid tiers only"}, status=400)
    profile = ensure_profile(request.user)
    old_tier = profile.subscription_tier
    old_status = profile.subscription_status
    try:
        order = RazorpayClient().create_order(user_id=request.user.id, tier=requested_tier)
    except RazorpayConfigurationError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as exc:
        return Response({"error": "razorpay order creation failed", "detail": str(exc)}, status=502)

    profile.subscription_tier = requested_tier
    profile.subscription_status = SubscriptionStatus.PENDING_PAYMENT
    profile.razorpay_order_id = order.id
    profile.save()
    log_subscription_change(
        user=request.user,
        old_tier=old_tier,
        new_tier=requested_tier,
        old_status=old_status,
        new_status=SubscriptionStatus.PENDING_PAYMENT,
        reason="razorpay_checkout_created",
        provider="RAZORPAY",
        provider_order_id=order.id,
        metadata=order.raw,
    )
    return Response(
        {
            "razorpay": {
                "key_id": RazorpayClient().key_id,
                "order_id": order.id,
                "amount": order.amount,
                "currency": order.currency,
                "receipt": order.receipt,
            },
            "subscription": serialize_subscription(profile),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subscription_verify_payment(request):
    order_id = request.data.get("razorpay_order_id") or ""
    payment_id = request.data.get("razorpay_payment_id") or ""
    signature = request.data.get("razorpay_signature") or ""
    if not order_id or not payment_id or not signature:
        return Response({"error": "razorpay_order_id, razorpay_payment_id, and razorpay_signature are required"}, status=400)

    profile = ensure_profile(request.user)
    if profile.razorpay_order_id != order_id:
        return Response({"error": "order does not match current subscription checkout"}, status=400)
    try:
        is_valid = verify_razorpay_payment_signature(
            order_id=order_id,
            payment_id=payment_id,
            signature=signature,
        )
    except RazorpayConfigurationError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if not is_valid:
        return Response({"error": "invalid payment signature"}, status=400)

    old_status = profile.subscription_status
    profile.subscription_status = SubscriptionStatus.ACTIVE
    profile.razorpay_payment_id = payment_id
    profile.save()
    log_subscription_change(
        user=request.user,
        old_tier=profile.subscription_tier,
        new_tier=profile.subscription_tier,
        old_status=old_status,
        new_status=SubscriptionStatus.ACTIVE,
        reason="razorpay_payment_verified",
        provider="RAZORPAY",
        provider_order_id=order_id,
        provider_payment_id=payment_id,
    )
    return Response({"subscription": serialize_subscription(profile)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_history(request):
    rows = [
        {
            "id": change.id,
            "old_tier": change.old_tier,
            "new_tier": change.new_tier,
            "old_status": change.old_status,
            "new_status": change.new_status,
            "reason": change.reason,
            "provider": change.provider,
            "provider_order_id": change.provider_order_id,
            "provider_payment_id": change.provider_payment_id,
            "created_at": change.created_at.isoformat(),
        }
        for change in SubscriptionChangeLog.objects.filter(user=request.user)[:100]
    ]
    return Response({"history": rows})


def ensure_profile(user) -> UserProfile:
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return profile


def serialize_user(user, profile: UserProfile) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "profile": {
            "display_name": profile.display_name,
            "company_name": profile.company_name,
            "role": profile.role,
            "email_updates_enabled": profile.email_updates_enabled,
            "product_updates_enabled": profile.product_updates_enabled,
            "research_digest_enabled": profile.research_digest_enabled,
        },
        "subscription": serialize_subscription(profile),
    }


def serialize_subscription(profile: UserProfile) -> dict:
    return {
        "tier": profile.subscription_tier,
        "status": profile.subscription_status,
        "razorpay_order_id": profile.razorpay_order_id,
        "razorpay_payment_id": profile.razorpay_payment_id,
        "razorpay_subscription_id": profile.razorpay_subscription_id,
    }


def log_subscription_change(
    *,
    user,
    old_tier: str,
    new_tier: str,
    old_status: str,
    new_status: str,
    reason: str,
    provider: str,
    provider_order_id: str = "",
    provider_payment_id: str = "",
    metadata: dict | None = None,
) -> SubscriptionChangeLog:
    return SubscriptionChangeLog.objects.create(
        user=user,
        old_tier=old_tier,
        new_tier=new_tier,
        old_status=old_status,
        new_status=new_status,
        reason=reason,
        provider=provider,
        provider_order_id=provider_order_id,
        provider_payment_id=provider_payment_id,
        metadata=metadata or {},
    )
