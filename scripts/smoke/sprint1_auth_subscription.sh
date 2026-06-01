#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="smoke_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"

echo "Creating user ${USERNAME}"
SIGNUP_RESPONSE="$(
  curl -sS -X POST "${BASE_URL}/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
)"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

echo "Checking /auth/me"
curl -sS "${BASE_URL}/auth/me" \
  -H "Authorization: Token ${TOKEN}" \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["user"]["subscription"]["tier"] == "FREE"; print("me ok")'

echo "Checking password reset request"
curl -sS -X POST "${BASE_URL}/auth/password-reset/request" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\"}" \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["status"] == "ok"; print("password reset request ok")'

echo "Checking Google OAuth URL endpoint"
GOOGLE_STATUS="$(
  curl -sS -o /tmp/infodj_google_url.json -w "%{http_code}" "${BASE_URL}/auth/google/url"
)"
case "${GOOGLE_STATUS}" in
  200)
    python3 -c 'import json; data=json.load(open("/tmp/infodj_google_url.json")); assert data["auth_url"].startswith("https://accounts.google.com/"); print("google url ok")'
    ;;
  503)
    python3 -c 'import json; data=json.load(open("/tmp/infodj_google_url.json")); assert "Google OAuth credentials" in data["error"]; print("google url skipped: credentials not configured")'
    ;;
  *)
    cat /tmp/infodj_google_url.json
    echo "unexpected google url status ${GOOGLE_STATUS}" >&2
    exit 1
    ;;
esac

echo "Attempting Razorpay checkout"
CHECKOUT_STATUS="$(
  curl -sS -o /tmp/infodj_checkout.json -w "%{http_code}" -X POST "${BASE_URL}/subscription/checkout" \
    -H "Authorization: Token ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"tier":"PRO"}'
)"
case "${CHECKOUT_STATUS}" in
  201)
    python3 -c 'import json,sys; data=json.load(open("/tmp/infodj_checkout.json")); assert data["razorpay"]["order_id"]; print("checkout ok")'
    ;;
  503)
    python3 -c 'import json; data=json.load(open("/tmp/infodj_checkout.json")); assert "Razorpay credentials" in data["error"]; print("checkout skipped: credentials not configured")'
    ;;
  *)
    cat /tmp/infodj_checkout.json
    echo "unexpected checkout status ${CHECKOUT_STATUS}" >&2
    exit 1
    ;;
esac

echo "Changing subscription tier internally"
curl -sS -X POST "${BASE_URL}/subscription/change" \
  -H "Authorization: Token ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"tier":"PRO","reason":"smoke_test"}' \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["subscription"]["tier"] == "PRO"; print("change ok")'

echo "Verifying invalid Razorpay payment signature is rejected"
STATUS="$(
  curl -sS -o /tmp/infodj_invalid_payment.json -w "%{http_code}" -X POST "${BASE_URL}/subscription/verify-payment" \
    -H "Authorization: Token ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"razorpay_order_id":"missing_order","razorpay_payment_id":"pay_test","razorpay_signature":"bad"}'
)"
test "${STATUS}" = "400"
echo "invalid signature rejected"

echo "Auth/subscription smoke test passed"
