#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="promise_tracker_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"

echo "Creating Management Promise smoke user ${USERNAME}"
SIGNUP_RESPONSE="$(curl -sS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

echo "Checking reviewed Netflix promise register and detail"
curl -fsS "${BASE_URL}/companies/netflix/management-promises?status=ACHIEVED&promise=launch-basic-with-ads" \
  -H "Authorization: Token ${TOKEN}" -o /tmp/infodj_management_promises.json
python3 - <<'PY'
import json

with open("/tmp/infodj_management_promises.json", encoding="utf-8") as handle:
    data = json.load(handle)

assert data["status"] == "available"
assert data["company"]["slug"] == "netflix"
assert data["coverage"]["promise_count"] == 1
assert data["selected_promise"]["slug"] == "launch-basic-with-ads"
assert data["selected_promise"]["current_status"] == "ACHIEVED"
assert data["selected_promise"]["evaluation_rule"]
assert len(data["selected_promise"]["updates"]) == 1
assert len(data["evidence"]) >= 1
print("Reviewed promise workflow ok")
PY

echo "Checking explicit unavailable state"
curl -fsS "${BASE_URL}/companies/caterpillar/management-promises" \
  -H "Authorization: Token ${TOKEN}" -o /tmp/infodj_management_promises_unavailable.json
python3 - <<'PY'
import json

with open("/tmp/infodj_management_promises_unavailable.json", encoding="utf-8") as handle:
    data = json.load(handle)

assert data["status"] == "unavailable"
assert data["promises"] == []
assert len(data["source_gaps"]) == 1
print("Unavailable promise state ok")
PY

echo "Management Promise Tracker smoke test passed"
