#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="promise_tracker_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "Creating Management Promise smoke user ${USERNAME}"
SIGNUP_RESPONSE="$(curl -sS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

echo "Checking reviewed promise coverage for all configured companies"
COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/management-promises" \
    -H "Authorization: Token ${TOKEN}" -o "${TMP_DIR}/${company}.json"
done
python3 - "${TMP_DIR}" <<'PY'
import json
from pathlib import Path
import sys

paths = sorted(Path(sys.argv[1]).glob("*.json"))
assert len(paths) == 20, len(paths)
for path in paths:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "available", data["company"]["slug"]
    assert data["coverage"]["promise_count"] >= 1, data["company"]["slug"]
    promise = data["selected_promise"]
    assert promise["source"], data["company"]["slug"]
    assert promise["original_statement"], data["company"]["slug"]
    assert promise["evidence_text"], data["company"]["slug"]
    assert promise["evaluation_rule"], data["company"]["slug"]
print("Reviewed all-company promise workflow ok")
PY

echo "Management Promise Tracker smoke test passed"
