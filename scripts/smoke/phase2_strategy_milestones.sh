#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="milestones_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

SIGNUP_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/strategy-milestones" \
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
    assert data["status"] == "available", slug
    assert data["coverage"]["milestone_count"] >= 1, slug
    assert data["coverage"]["source_count"] >= 1, slug
    milestone = data["selected_milestone"]
    assert milestone, slug
    assert milestone["origin"] in {"MANAGEMENT_ANNOUNCED", "REGULATOR_DEFINED", "CONTRACTUAL", "ANALYST_INFERRED"}, slug
    assert milestone["source"]["url"], slug
    assert milestone["success_condition"], slug
    assert milestone["evidence_text"], slug
    assert milestone["status_history"], slug
    if milestone["expected_end_date"] is None:
        assert milestone["date_precision"] == "UNKNOWN", slug
    if slug == "netflix":
        assert milestone["current_status"] == "COMPLETED", slug
        assert [(row["status_date"], row["status"]) for row in milestone["status_history"]] == [
            ("2022-10-13", "EXPECTED"),
            ("2022-11-03", "COMPLETED"),
        ], slug
print("Strategy Milestone reviewed baseline passed for all 20 companies")
PY
