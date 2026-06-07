#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="businessmodel_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"

echo "Creating Business Model smoke user ${USERNAME}"
SIGNUP_RESPONSE="$(
  curl -sS -X POST "${BASE_URL}/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
)"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

echo "Checking Netflix Business Model Map"
STATUS="$(
  curl -sS -o /tmp/infodj_business_model.json -w "%{http_code}" \
    "${BASE_URL}/companies/netflix/business-model?as_of=2022-12-31&compare_to=2011-12-31" \
    -H "Authorization: Token ${TOKEN}"
)"
test "${STATUS}" = "200"

python3 - <<'PY'
import json

with open("/tmp/infodj_business_model.json", encoding="utf-8") as handle:
    data = json.load(handle)

assert data["status"] == "available"
assert data["company"]["slug"] == "netflix"
assert data["snapshot"]["effective_date"] == "2022-12-31"
assert data["comparison_snapshot"]["effective_date"] == "2011-12-31"
assert data["coverage"]["completeness_percent"] == 100
assert len(data["snapshot"]["components"]) > 0
assert len(data["snapshot"]["relationships"]) > 0
assert "components_added" in data["changes"]
assert "evidence" in data
assert "source_gaps" in data
print("Business Model Map ok")
PY

echo "Business Model smoke test passed"
