#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="leadership_decisions_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

SIGNUP_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/leadership-decisions" \
    -H "Authorization: Token ${TOKEN}" -o "${TMP_DIR}/${company}.json"
done

python3 - "${TMP_DIR}" <<'PY'
import json
from pathlib import Path
import sys

paths = sorted(Path(sys.argv[1]).glob("*.json"))
assert len(paths) == 20
expected_gaps = {"tenure_dates", "transition_events", "leadership_records", "leadership_decisions", "tenure_performance_context"}
for path in paths:
    data = json.loads(path.read_text(encoding="utf-8"))
    slug = data["company"]["slug"]
    assert data["status"] in {"available", "partial"}, slug
    assert data["snapshot"], slug
    assert data["coverage"]["role_count"] == len(data["roles"]), slug
    assert data["coverage"]["decision_count"] == len(data["decisions"]), slug
    assert data["performance_context"]["status"] == "unavailable", slug
    assert "does not claim" in data["performance_context"]["non_causation_note"], slug
    gap_keys = {gap["key"] for gap in data["source_gaps"]}
    assert expected_gaps & gap_keys, slug
    for role in data["roles"]:
        assert role["leader_name"], slug
        assert role["transition_type"], slug
        assert role["evidence_text"], slug
    for gap in data["source_gaps"]:
        assert gap["reason"], slug
        assert gap["next_action"], slug
print("Leadership Decision Record baseline passed for all 20 companies")
PY
