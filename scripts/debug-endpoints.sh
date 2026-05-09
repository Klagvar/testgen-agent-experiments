#!/usr/bin/env bash
set -a; source "$(cd "$(dirname "$0")/.." && pwd)/.env"; set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"
echo "URL=$TESTGEN_API_URL"
echo
echo "=== /api/v1/models/qwen/qwen-2.5-7b-instruct/endpoints ==="
curl -s -w "\nHTTP=%{http_code}\n" --max-time 15 \
  "$TESTGEN_API_URL/models/qwen/qwen-2.5-7b-instruct/endpoints" \
  -H "Authorization: Bearer $TESTGEN_API_KEY" | head -c 600
echo
echo
echo "=== /api/frontend/stats/endpoint (no auth) ==="
curl -s -w "\nHTTP=%{http_code}\n" --max-time 15 \
  "https://openrouter.ai/api/frontend/stats/endpoint?permaslug=qwen/qwen-2.5-7b-instruct" | head -c 600
echo
echo
echo "=== alternative path ==="
curl -s -w "\nHTTP=%{http_code}\n" --max-time 15 \
  "https://openrouter.ai/api/v1/models/qwen/qwen-2.5-7b-instruct" \
  -H "Authorization: Bearer $TESTGEN_API_KEY" | head -c 600
echo
