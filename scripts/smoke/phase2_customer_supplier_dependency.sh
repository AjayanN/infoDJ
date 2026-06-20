#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="dependencies_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

SIGNUP_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/auth/signup" -H "Content-Type: application/json" -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

COMPANIES=(apple microsoft jpmorgan-chase visa unitedhealth-group pfizer amazon walmart exxonmobil nextera-energy ford-motor-company tesla caterpillar general-electric disney netflix prologis american-tower freeport-mcmoran newmont)
for company in "${COMPANIES[@]}"; do
  curl -fsS "${BASE_URL}/companies/${company}/customer-supplier-dependency" \
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
    assert data["dependencies"], slug
    assert data["coverage"]["dependency_count"] == len(data["dependencies"]), slug
    assert data["coverage"]["category_only_count"] >= 1, slug
    assert any(gap["key"] in {"named_counterparties", "concentration_percentages", "dependency_contract_terms"} for gap in data["source_gaps"]), slug
    for dependency in data["dependencies"]:
        assert dependency["counterparty_name"], slug
        assert dependency["dependency_type"], slug
        assert dependency["relationship_summary"], slug
        if not dependency["is_named_counterparty"]:
            assert dependency["disclosure_confidence"] == "CATEGORY_ONLY", slug
    for gap in data["source_gaps"]:
        assert gap["reason"], slug
        assert gap["next_action"], slug
print("Customer and Supplier Dependency baseline passed for all 20 companies")
PY
