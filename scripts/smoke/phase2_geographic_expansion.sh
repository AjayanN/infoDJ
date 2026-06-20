#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="geo_expansion_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

SIGNUP_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/geographic-expansion" \
    -H "Authorization: Token ${TOKEN}" -o "${TMP_DIR}/${company}.json"
done

python3 - "${TMP_DIR}" <<'PY'
import json
from pathlib import Path
import sys

paths = sorted(Path(sys.argv[1]).glob("*.json"))
assert len(paths) == 20
for path in paths:
    data = json.loads(path.read_text(encoding="utf-8"))
    slug = data["company"]["slug"]
    assert data["status"] in {"available", "partial"}, slug
    assert data["snapshot"], slug
    assert data["markets"], slug
    assert data["coverage"]["market_count"] == len(data["markets"]), slug
    assert any(gap["key"] in {"market_entry_dates", "revenue_contribution", "local_partnerships", "regulatory_barriers", "expansion_outcomes"} for gap in data["source_gaps"]), slug
    for market in data["markets"]:
        assert market["geography"], slug
        assert market["current_status"], slug
        assert market["expansion_rationale"], slug
        assert market["revenue_contribution"] is None or market["revenue_currency"], slug
    for gap in data["source_gaps"]:
        assert gap["reason"], slug
        assert gap["next_action"], slug
print("Geographic Expansion Map baseline passed for all 20 companies")
PY
