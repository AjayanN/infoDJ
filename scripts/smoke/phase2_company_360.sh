#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="company360_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"

echo "Creating Company 360 smoke user ${USERNAME}"
SIGNUP_RESPONSE="$(
  curl -sS -X POST "${BASE_URL}/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
)"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

echo "Checking Netflix Company 360 profile"
STATUS="$(
  curl -sS -o /tmp/infodj_company_360.json -w "%{http_code}" \
    "${BASE_URL}/companies/netflix/profile" \
    -H "Authorization: Token ${TOKEN}"
)"
test "${STATUS}" = "200"

python3 - <<'PY'
import json

with open("/tmp/infodj_company_360.json", encoding="utf-8") as handle:
    data = json.load(handle)

assert data["company"]["slug"] == "netflix"
assert data["status"] in {"available", "partial"}
assert "business_model" in data["sections"]
assert "strategic_priorities" in data["sections"]
assert "coverage" in data
assert "completeness_percent" in data["coverage"]
assert "latest_events" in data["highlights"]
assert "latest_turns" in data["highlights"]
assert "evidence" in data
assert "source_gaps" in data
print("Company 360 profile ok")
PY

echo "Company 360 smoke test passed"
