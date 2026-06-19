#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="capital_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

SIGNUP_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/capital-allocation" \
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
    assert data["periods"], slug
    period = data["selected_period"]
    assert period, slug
    assert period["headline"], slug
    context = period["cash_flow_context"]
    assert context["operating_cash_flow"] is not None, slug
    assert context["total_deployment"] is None or context["total_deployment"] >= 0, slug
    assert isinstance(period["deployment_items"], list), slug
    assert isinstance(period["context_items"], list), slug
    assert data["coverage"]["missing_category_count"] >= 0, slug
    for gap in data["source_gaps"]:
        assert gap["reason"], slug
        assert gap["next_action"], slug
    if not period["deployment_items"]:
        assert any(gap["key"] == "capital_deployment_items" for gap in data["source_gaps"]), slug
    for item in period["deployment_items"]:
        assert item["value"] >= 0, slug
        assert item["concept"], slug
        assert item["evidence_text"], slug
print("Capital Allocation Dashboard SEC-backed baseline passed for all 20 companies")
PY
