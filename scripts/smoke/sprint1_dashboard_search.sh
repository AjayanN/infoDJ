#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="dash_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "Creating user ${USERNAME}"
SIGNUP_RESPONSE="$(
  curl -sS -X POST "${BASE_URL}/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
)"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

echo "Checking dashboard"
curl -fsS "${BASE_URL}/dashboard?limit=50" \
  -H "Authorization: Token ${TOKEN}" -o "${TMP_DIR}/dashboard.json"
python3 - "${TMP_DIR}/dashboard.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["summary"]["company_count"] == 20
scorecards = data["dashboards"]["sections"]["scorecards"]
assert scorecards["status"] == "available"
assert len({row["company_slug"] for row in scorecards["items"]}) == 20
comparisons = data["dashboards"]["sections"]["compare"]
assert comparisons["status"] == "available"
assert comparisons["items"]
assert all(row["company_count"] >= 2 for row in comparisons["items"])
print("all-company dashboard ok")
PY

echo "Checking categories"
curl -sS "${BASE_URL}/categories" \
  -H "Authorization: Token ${TOKEN}" \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); assert "categories" in data; print("categories ok")'

echo "Checking search validation"
STATUS="$(
  curl -sS -o /tmp/infodj_search_missing_q.json -w "%{http_code}" "${BASE_URL}/search" \
    -H "Authorization: Token ${TOKEN}"
)"
test "${STATUS}" = "400"
echo "search validation ok"

echo "Checking company search for all configured businesses"
COMPANIES=("apple|Apple" "microsoft|Microsoft" "jpmorgan-chase|JPMorgan Chase" "visa|Visa" "unitedhealth-group|UnitedHealth Group" "pfizer|Pfizer" "amazon|Amazon" "walmart|Walmart" "exxonmobil|ExxonMobil" "nextera-energy|NextEra Energy" "ford-motor-company|Ford Motor Company" "tesla|Tesla" "caterpillar|Caterpillar" "general-electric|General Electric" "disney|Disney" "netflix|Netflix" "prologis|Prologis" "american-tower|American Tower" "freeport-mcmoran|Freeport-McMoRan" "newmont|Newmont")
for entry in "${COMPANIES[@]}"; do
  slug="${entry%%|*}"
  query="${entry#*|}"
  curl -fsS --get "${BASE_URL}/search" \
    --data-urlencode "q=${query}" --data "language=en" --data "limit=5" \
    -H "Authorization: Token ${TOKEN}" -o "${TMP_DIR}/search_${slug}.json"
done
python3 - "${TMP_DIR}" <<'PY'
import json
from pathlib import Path
import sys

paths = sorted(Path(sys.argv[1]).glob("search_*.json"))
assert len(paths) == 20
for path in paths:
    expected = path.stem.removeprefix("search_")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["language"] == "en"
    assert expected in {row["slug"] for row in data["results"]["companies"]}, expected
print("all-company search ok")
PY

echo "Checking search suggestions"
SUGGEST_STATUS="$(
  curl -sS -o /tmp/infodj_suggest.json -w "%{http_code}" "${BASE_URL}/search/suggest?q=net&language=en" \
    -H "Authorization: Token ${TOKEN}"
)"
if [ "${SUGGEST_STATUS}" = "200" ]; then
  python3 -c 'import json; data=json.load(open("/tmp/infodj_suggest.json")); assert "suggestions" in data; print("suggest ok")'
else
  cat /tmp/infodj_suggest.json
  echo "unexpected suggest status ${SUGGEST_STATUS}" >&2
  exit 1
fi

echo "Dashboard/search smoke test passed"
