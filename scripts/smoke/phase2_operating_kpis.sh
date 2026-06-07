#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="operatingkpi_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"

echo "Creating Operating KPI smoke user ${USERNAME}"
SIGNUP_RESPONSE="$(curl -sS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

echo "Checking Netflix Operating KPI Tracker"
STATUS="$(curl -sS -o /tmp/infodj_operating_kpis.json -w "%{http_code}" "${BASE_URL}/companies/netflix/operating-kpis?metric=paid-memberships&segment=Streaming" -H "Authorization: Token ${TOKEN}")"
test "${STATUS}" = "200"

python3 - <<'PY'
import json

with open("/tmp/infodj_operating_kpis.json", encoding="utf-8") as handle:
    data = json.load(handle)

assert data["status"] == "available"
assert data["company"]["slug"] == "netflix"
assert data["selected_metric"]["slug"] == "paid-memberships"
assert data["selected_metric"]["value_type"] == "REPORTED"
assert len(data["series"]) >= 4
assert data["coverage"]["calculated_count"] >= 1
assert data["missing_periods"] == []
assert len(data["alerts"]) >= 1
assert len(data["export_rows"]) == len(data["series"])
assert len(data["evidence"]) >= 1
print("Operating KPI Tracker ok")
PY

echo "Operating KPI smoke test passed"
