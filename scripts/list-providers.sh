#!/usr/bin/env bash
# Печатает список провайдеров OpenRouter для указанной модели.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
set -a; source "$ROOT/.env"; set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL:-https://openrouter.ai/api/v1}"

MODEL="${1:-qwen/qwen-2.5-7b-instruct}"
echo "=== providers for $MODEL ==="

JSON=$(curl -s --max-time 15 "$TESTGEN_API_URL/models/$MODEL/endpoints" \
  -H "Authorization: Bearer $TESTGEN_API_KEY")

if [ -z "$JSON" ]; then
  echo "❌ пустой ответ"
  exit 1
fi

echo "$JSON" | python3 -c '
import json, sys
d = json.load(sys.stdin)
data = d.get("data", d)
eps = data.get("endpoints", []) if isinstance(data, dict) else []
print(f"найдено: {len(eps)} endpoint-ов\n")
for ep in eps:
    n = ep.get("provider_name", "?")
    ctx = ep.get("context_length", "?")
    pricing = ep.get("pricing", {}) or {}
    p_in = pricing.get("prompt", "?")
    p_out = pricing.get("completion", "?")
    status = ep.get("status", "")
    print(f"  - {n:25s}  ctx={str(ctx):>7s}  in={p_in}  out={p_out}  {status}")
'
