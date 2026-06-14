#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="earnings_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

SIGNUP_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/earnings" \
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
    assert data["periods"], slug
    period = data["selected_period"]
    assert period["headline"], slug
    document_types = {document["document_type"] for document in period["document_set"]}
    assert "SEC_10_Q" in document_types, slug
    assert "EARNINGS_EXHIBIT" in document_types, slug
    assert all(document["source"]["url"] for document in period["document_set"]), slug
    assert period["measured_results"], slug
    assert period["management_explanation"], slug
    assert not any(gap["key"] == "management_explanation" for gap in data["source_gaps"]), slug
    if slug == "netflix":
        assert period["guidance_comparison"]["status"] == "available", slug
        assert len(period["guidance_comparison"]["items"]) == 4, slug
        assert all(item["forecast_source"]["url"] != item["actual_source"]["url"] for item in period["guidance_comparison"]["items"]), slug
print("Earnings Intelligence reviewed evidence baseline passed for all 20 companies")
PY
