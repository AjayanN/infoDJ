#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080/api/app}"
USERNAME="dash_$(date +%s)"
EMAIL="${USERNAME}@example.com"
PASSWORD="SmokePass123!"

echo "Creating user ${USERNAME}"
SIGNUP_RESPONSE="$(
  curl -sS -X POST "${BASE_URL}/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}"
)"
TOKEN="$(printf '%s' "${SIGNUP_RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

echo "Checking dashboard"
curl -sS "${BASE_URL}/dashboard" \
  -H "Authorization: Token ${TOKEN}" \
  | python3 -c 'import json,sys; data=json.load(sys.stdin); assert "summary" in data; assert "sector_counts" in data; assert "top_companies" in data; print("dashboard ok")'

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

echo "Checking global search"
SEARCH_STATUS="$(
  curl -sS -o /tmp/infodj_search.json -w "%{http_code}" "${BASE_URL}/search?q=netflix&language=en" \
    -H "Authorization: Token ${TOKEN}"
)"
if [ "${SEARCH_STATUS}" = "200" ]; then
  python3 -c 'import json; data=json.load(open("/tmp/infodj_search.json")); assert data["language"] == "en"; assert "results" in data; assert "companies" in data["results"]; assert "events" in data["results"]; assert "strategic_turns" in data["results"]; print("search ok")'
else
  cat /tmp/infodj_search.json
  echo "unexpected search status ${SEARCH_STATUS}" >&2
  exit 1
fi

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
