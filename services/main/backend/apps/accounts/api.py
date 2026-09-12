from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from secrets import compare_digest, token_urlsafe
from urllib.parse import urlencode, urljoin

import requests

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.founder_decision import build_founder_decision
from apps.accounts.founder_playbooks import FOUNDER_OBJECTIVES, FOUNDER_STAGES, playbook_for
from apps.search.api import ingestion_get
from apps.accounts.models import (
    HistoryDocumentUpload,
    SubscriptionChangeLog,
    SubscriptionStatus,
    SubscriptionTier,
    UserProfile,
)
from apps.accounts.services import (
    GoogleOAuthConfigurationError,
    RazorpayClient,
    RazorpayConfigurationError,
    TIER_PRICES_INR,
    build_google_oauth_url,
    exchange_google_code_for_profile,
    verify_razorpay_payment_signature,
)


User = get_user_model()
MAX_AVATAR_BYTES = 2 * 1024 * 1024
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class AuthenticationRateThrottle(AnonRateThrottle):
    scope = "auth"


def password_error_response(error: ValidationError) -> Response:
    return Response(
        {"error": "password does not meet security requirements", "details": error.messages},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthenticationRateThrottle])
def signup(request):
    username = (request.data.get("username") or "").strip()
    email = (request.data.get("email") or "").strip()
    password = request.data.get("password") or ""
    if not username or not email or not password:
        return Response({"error": "username, email, and password are required"}, status=400)
    try:
        validate_password(password, user=User(username=username, email=email))
    except ValidationError as exc:
        return password_error_response(exc)
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
            "user": serialize_user(user, profile, request),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthenticationRateThrottle])
def login(request):
    username = request.data.get("username") or request.data.get("email") or ""
    password = request.data.get("password") or ""
    user = authenticate(username=username, password=password)
    if user is None:
        return Response({"error": "invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
    profile = ensure_profile(user)
    token, _created = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": serialize_user(user, profile, request)})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthenticationRateThrottle])
def password_reset_request(request):
    email = (request.data.get("email") or "").strip()
    if email:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?{urlencode({'uid': uid, 'token': token})}"
            send_mail(
                subject="Reset your InfoDJ password",
                message=(
                    "Use this link to reset your InfoDJ password:\n\n"
                    f"{reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
    return Response({"status": "ok"})


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthenticationRateThrottle])
def password_reset_confirm(request):
    uid = request.data.get("uid") or ""
    token = request.data.get("token") or ""
    password = request.data.get("password") or ""
    if not uid or not token or not password:
        return Response({"error": "uid, token, and password are required"}, status=400)
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except Exception:
        return Response({"error": "invalid password reset link"}, status=400)
    if not default_token_generator.check_token(user, token):
        return Response({"error": "invalid password reset link"}, status=400)
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return password_error_response(exc)
    user.set_password(password)
    user.save(update_fields=["password"])
    Token.objects.filter(user=user).delete()
    return Response({"status": "password_updated"})


@api_view(["GET"])
@permission_classes([AllowAny])
def google_auth_url(request):
    try:
        state = token_urlsafe(32)
        request.session["google_oauth_state"] = state
        return Response({"auth_url": build_google_oauth_url(state)})
    except GoogleOAuthConfigurationError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(["GET"])
@permission_classes([AllowAny])
def google_callback(request):
    code = request.query_params.get("code") or ""
    state = request.query_params.get("state") or ""
    expected_state = request.session.pop("google_oauth_state", "")
    if not code:
        return Response({"error": "Google authorization code is required"}, status=400)
    if not expected_state or not state or not compare_digest(state, expected_state):
        return Response({"error": "invalid Google OAuth state"}, status=400)
    try:
        google_profile = exchange_google_code_for_profile(code)
    except GoogleOAuthConfigurationError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as exc:
        return Response({"error": "Google login failed", "detail": str(exc)}, status=502)

    email = google_profile["email"].strip().lower()
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        username = unique_username_from_email(email)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,
            first_name=google_profile.get("given_name", ""),
            last_name=google_profile.get("family_name", ""),
        )
    profile = ensure_profile(user)
    if google_profile.get("name") and not profile.display_name:
        profile.display_name = google_profile["name"][:255]
        profile.save(update_fields=["display_name"])
    token, _created = Token.objects.get_or_create(user=user)
    redirect_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/auth/callback#{urlencode({'token': token.key})}"
    return redirect(redirect_url)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"status": "logged_out"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    profile = ensure_profile(request.user)
    return Response({"user": serialize_user(request.user, profile, request)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def founder_decision(request):
    profile = ensure_profile(request.user)
    context = serialize_founder_context(profile)
    companies_payload, companies_error = ingestion_get("companies")
    dashboard_payload, dashboard_error = ingestion_get("dashboard-data", {"limit": 50})
    if companies_error or dashboard_error:
        return Response(
            {
                "status": "unavailable",
                "context": context,
                "directions": [],
                "journey": [],
                "risk_radar": [],
                "coverage": {"comparable_event_count": 0, "risk_event_count": 0, "sector_company_count": 0},
                "source_gaps": [
                    {
                        "key": "founder_decision_ingestion",
                        "reason": companies_error or dashboard_error,
                        "next_action": "Restore the ingestion API before generating evidence-backed founder directions.",
                    }
                ],
            },
            status=503,
        )
    return Response(build_founder_decision(context, companies_payload.get("companies", []), dashboard_payload or {}))


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def founder_context(request):
    profile = ensure_profile(request.user)
    if request.method == "PATCH":
        context_fields = {
            "company_name": ("company_name",),
            "founder_sector": ("sector", "founder_sector"),
            "founder_business_type": ("business_type", "founder_business_type"),
            "founder_stage": ("stage", "founder_stage"),
            "founder_objective": ("objective", "founder_objective"),
            "founder_geography": ("geography", "founder_geography"),
            "founder_target_customer": ("target_customer", "founder_target_customer"),
            "founder_revenue_model": ("revenue_model", "founder_revenue_model"),
            "founder_constraints": ("constraints", "founder_constraints"),
        }
        updates = {}
        for profile_field, request_fields in context_fields.items():
            for request_field in request_fields:
                if request_field in request.data:
                    updates[profile_field] = str(request.data.get(request_field) or "").strip()
                    break
        if updates.get("founder_stage") and updates["founder_stage"] not in FOUNDER_STAGES:
            return Response({"error": "invalid founder_stage"}, status=400)
        if updates.get("founder_objective") and updates["founder_objective"] not in FOUNDER_OBJECTIVES:
            return Response({"error": "invalid founder_objective"}, status=400)
        for field, value in updates.items():
            setattr(profile, field, value)
        if updates:
            profile.save(update_fields=[*updates.keys(), "updated_at"])
    return Response({"founder_context": serialize_founder_context(profile), "playbook": playbook_for(profile.founder_sector, profile.founder_stage)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def founder_playbook(request):
    profile = ensure_profile(request.user)
    sector = (request.query_params.get("sector") or profile.founder_sector).strip()
    stage = (request.query_params.get("stage") or profile.founder_stage).strip()
    if stage and stage not in FOUNDER_STAGES:
        return Response({"error": "invalid stage"}, status=400)
    return Response({"playbook": playbook_for(sector, stage)})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def profile_avatar(request):
    profile = ensure_profile(request.user)

    if request.method == "DELETE":
        delete_avatar_file(profile)
        return Response({"user": serialize_user(request.user, profile, request)})

    avatar = request.FILES.get("avatar")
    if avatar is None:
        return Response({"error": "avatar file is required"}, status=400)

    validation_error = validate_avatar_upload(avatar)
    if validation_error:
        return Response({"error": validation_error}, status=400)

    delete_avatar_file(profile, save=False)
    profile.avatar = avatar
    profile.save(update_fields=["avatar", "updated_at"])
    return Response({"user": serialize_user(request.user, profile, request)})


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

    profile.pending_subscription_tier = requested_tier
    profile.razorpay_order_id = order.id
    profile.razorpay_payment_id = ""
    profile.save(update_fields=["pending_subscription_tier", "razorpay_order_id", "razorpay_payment_id", "updated_at"])
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

    pending_tier = profile.pending_subscription_tier
    if not pending_tier:
        latest_checkout = SubscriptionChangeLog.objects.filter(
            user=request.user,
            provider="RAZORPAY",
            provider_order_id=order_id,
            reason="razorpay_checkout_created",
        ).order_by("-created_at", "-id").first()
        pending_tier = latest_checkout.new_tier if latest_checkout else ""
    if pending_tier not in TIER_PRICES_INR:
        return Response({"error": "no pending paid subscription tier found for this order"}, status=400)

    old_tier = profile.subscription_tier
    old_status = profile.subscription_status
    profile.subscription_tier = pending_tier
    profile.subscription_status = SubscriptionStatus.ACTIVE
    profile.pending_subscription_tier = ""
    profile.razorpay_payment_id = payment_id
    profile.save(
        update_fields=[
            "subscription_tier",
            "subscription_status",
            "pending_subscription_tier",
            "razorpay_payment_id",
            "updated_at",
        ]
    )
    log_subscription_change(
        user=request.user,
        old_tier=old_tier,
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


def unique_username_from_email(email: str) -> str:
    base = email.split("@", 1)[0].replace(".", "_").replace("+", "_") or "google_user"
    candidate = base[:140]
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base[:130]}_{suffix}"
    return candidate


def validate_avatar_upload(avatar) -> str:
    extension = Path(avatar.name).suffix.lower()
    content_type = getattr(avatar, "content_type", "")
    if extension not in ALLOWED_AVATAR_EXTENSIONS:
        return "avatar must be a jpg, jpeg, png, or webp image"
    if content_type and content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        return "avatar content type must be jpeg, png, or webp"
    if avatar.size > MAX_AVATAR_BYTES:
        return "avatar must be 2 MB or smaller"
    return ""


def delete_avatar_file(profile: UserProfile, *, save: bool = True) -> None:
    if not profile.avatar:
        return
    profile.avatar.delete(save=False)
    profile.avatar = ""
    if save:
        profile.save(update_fields=["avatar", "updated_at"])


def serialize_user(user, profile: UserProfile, request=None) -> dict:
    avatar_url = ""
    if profile.avatar:
        avatar_url = profile.avatar.url
        if settings.MEDIA_PUBLIC_BASE_URL:
            avatar_url = f"{settings.MEDIA_PUBLIC_BASE_URL.rstrip('/')}{avatar_url}"
        elif request is not None:
            avatar_url = request.build_absolute_uri(avatar_url)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "profile": {
            "display_name": profile.display_name,
            "company_name": profile.company_name,
            "role": profile.role,
            "avatar_url": avatar_url,
            "email_updates_enabled": profile.email_updates_enabled,
            "product_updates_enabled": profile.product_updates_enabled,
            "research_digest_enabled": profile.research_digest_enabled,
            "founder_context": serialize_founder_context(profile),
        },
        "subscription": serialize_subscription(profile),
    }


def serialize_founder_context(profile: UserProfile) -> dict:
    return {
        "company_name": profile.company_name,
        "sector": profile.founder_sector,
        "business_type": profile.founder_business_type,
        "stage": profile.founder_stage,
        "objective": profile.founder_objective,
        "geography": profile.founder_geography,
        "target_customer": profile.founder_target_customer,
        "revenue_model": profile.founder_revenue_model,
        "constraints": profile.founder_constraints,
    }


def serialize_subscription(profile: UserProfile) -> dict:
    return {
        "tier": profile.subscription_tier,
        "status": profile.subscription_status,
        "pending_tier": profile.pending_subscription_tier,
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def history_document_upload(request):
    """Authenticated upload proxy; files never cause public arbitrary URL fetches."""
    uploaded = request.FILES.get("file")
    company_slug = (request.data.get("company_slug") or "").strip()
    rights_scope = (request.data.get("rights_scope") or "").strip()
    access_scope = (request.data.get("access_scope") or "private").strip()
    if not uploaded or not company_slug or not rights_scope:
        return Response({"error": "file, company_slug, and rights_scope are required"}, status=400)
    if access_scope not in {"private", "public"}:
        return Response({"error": "access_scope must be private or public"}, status=400)
    if uploaded.size > 20 * 1024 * 1024:
        return Response({"error": "uploaded document exceeds 20 MiB"}, status=413)
    media_type = (uploaded.content_type or "application/octet-stream").split(";", 1)[0].lower()
    if media_type not in {"application/pdf", "text/plain", "text/html", "application/xhtml+xml"}:
        return Response({"error": "unsupported uploaded document type"}, status=415)
    content = uploaded.read()
    upload = HistoryDocumentUpload.objects.create(owner=request.user, company_slug=company_slug, rights_scope=rights_scope, access_scope=access_scope, filename=uploaded.name[:512], content_sha256=sha256(content).hexdigest(), status="FORWARDING")
    token = settings.INGESTION_INTERNAL_WRITE_TOKEN
    if not token:
        upload.status = "BLOCKED"
        upload.error = "INGESTION_INTERNAL_WRITE_TOKEN is not configured"
        upload.save(update_fields=["status", "error", "updated_at"])
        return Response({"error": "history document intake is not configured", "upload_id": upload.id}, status=503)
    endpoint = urljoin(settings.INGESTION_API_URL.rstrip("/") + "/", "internal/history/documents")
    try:
        response = requests.post(endpoint, data={"company_slug": company_slug, "rights_scope": rights_scope, "access_scope": access_scope, "tenant_key": f"user:{request.user.pk}"}, files={"file": (uploaded.name, content, media_type)}, headers={"X-InfoDJ-Internal-Token": token}, timeout=30)
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        upload.status = "FAILED"
        upload.error = str(exc)
        upload.save(update_fields=["status", "error", "updated_at"])
        return Response({"error": "history intake unavailable", "upload_id": upload.id}, status=503)
    upload.ingestion_job_id = payload.get("job_id")
    upload.status = "ACCEPTED" if response.status_code == 202 else "FAILED"
    upload.error = "" if response.status_code == 202 else str(payload)
    upload.save(update_fields=["ingestion_job_id", "status", "error", "updated_at"])
    return Response({"upload_id": upload.id, "job_id": upload.ingestion_job_id, "status": upload.status}, status=response.status_code)
