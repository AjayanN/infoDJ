#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="ownership_insider_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

SIGNUP_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/ownership-insider" \
    -H "Authorization: Token ${TOKEN}" -o "${TMP_DIR}/${company}.json"
done

python3 - "${TMP_DIR}" <<'PY'
import json
from pathlib import Path
import sys

paths = sorted(Path(sys.argv[1]).glob("*.json"))
assert len(paths) == 20
required_gap_keys = {"ownership_positions", "ownership_percentages", "voting_control", "institutional_positions", "insider_transactions"}
for path in paths:
    data = json.loads(path.read_text(encoding="utf-8"))
    slug = data["company"]["slug"]
    assert data["status"] in {"available", "partial"}, slug
    assert data["snapshot"], slug
    assert data["coverage"]["position_count"] == len(data["positions"]), slug
    assert data["coverage"]["transaction_count"] == len(data["insider_transactions"]), slug
    assert data["control_context"]["status"] in {"available", "unavailable"}, slug
    gap_keys = {gap["key"] for gap in data["source_gaps"]}
    assert required_gap_keys & gap_keys, slug
    for position in data["positions"]:
        assert position["holder_name"], slug
        assert position["holder_type"], slug
        assert position["position_type"], slug
        assert position["evidence_text"], slug
    for gap in data["source_gaps"]:
        assert gap["reason"], slug
        assert gap["next_action"], slug
print("Ownership and Insider Activity baseline passed for all 20 companies")
PY
