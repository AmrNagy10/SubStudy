#!/usr/bin/env bash
# Quick smoke checks for SubStudy local v1.
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API_KEY="${API_KEY:-}"

echo "→ GET /health"
curl -sf "${BASE_URL}/health" | grep -q '"status":"ok"'

echo "→ GET /ready"
curl -sf "${BASE_URL}/ready" | grep -q '"status"'

echo "→ GET / (frontend)"
curl -sf "${BASE_URL}/" | grep -q 'SubStudy'

if [[ -n "${API_KEY}" ]]; then
  echo "→ GET /api/v1/status (auth probe — expect 404 for fake id)"
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-API-Key: ${API_KEY}" \
    "${BASE_URL}/api/v1/status/00000000-0000-0000-0000-000000000001")
  [[ "${code}" == "404" ]] || { echo "Expected 404, got ${code}"; exit 1; }
else
  echo "→ Skipping authenticated API probe (set API_KEY to test remote access)"
fi

echo "✅ Smoke checks passed"
