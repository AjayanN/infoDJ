#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="competition_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

SIGNUP_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/competitive-position" \
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
    assert "does not imply causation" in data["snapshot"]["methodology"], slug
    assert data["peer_map"], slug
    assert data["coverage"]["peer_count"] >= 1, slug
    assert data["comparison"].get("PRODUCT_OVERLAP"), slug
    assert data["comparison"].get("GEOGRAPHIC_OVERLAP"), slug
    assert data["market_share"]["status"] == "unavailable", slug
    assert any(gap["key"] == "competitive_market_share" for gap in data["source_gaps"]), slug
    for peer in data["peer_map"]:
        assert peer["peer_name"], slug
        assert peer["relationship_type"], slug
        assert peer["evidence_text"], slug
print("Competitive Position Dashboard baseline passed for all 20 companies")
PY
