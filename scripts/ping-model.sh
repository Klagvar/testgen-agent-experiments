#!/usr/bin/env bash
# Quick direct test of Llama 70B on DeepInfra to measure response time.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
set -a; source "$ROOT/.env"; set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL:-https://openrouter.ai/api/v1}"

MODEL="${1:-meta-llama/llama-3.3-70b-instruct}"
PROV="${2:-DeepInfra}"

cat > /tmp/req.json <<EOF
{
  "model": "$MODEL",
  "messages": [{"role":"user","content":"Reply with a single word: ok"}],
  "max_tokens": 5,
  "temperature": 0,
  "provider": {"only":["$PROV"], "allow_fallbacks": false}
}
EOF

echo "=== Test $MODEL via $PROV ==="
time curl -s --max-time 60 -X POST "$TESTGEN_API_URL/chat/completions" \
  -H "Authorization: Bearer $TESTGEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/req.json | head -c 600
echo
