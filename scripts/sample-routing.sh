#!/usr/bin/env bash
# Делает N коротких запросов подряд без provider.only и считает,
# на каких провайдерах OpenRouter их выполнил.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
set -a; source "$ROOT/.env"; set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL:-https://openrouter.ai/api/v1}"

MODEL="${1:-qwen/qwen-2.5-7b-instruct}"
N="${2:-15}"

echo "=== sampling routing for $MODEL: $N requests ==="
TMP=$(mktemp)
: > "$TMP"
for i in $(seq 1 "$N"); do
  printf "  [%2d/%d] " "$i" "$N"
  RESP=$(curl -s --max-time 25 -X POST "$TESTGEN_API_URL/chat/completions" \
    -H "Authorization: Bearer $TESTGEN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "'"$MODEL"'",
      "temperature": 0,
      "max_tokens": 3,
      "messages": [
        {"role":"user","content":"reply: ok"}
      ]
    }')
  PROV=$(echo "$RESP" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    if "error" in d and d["error"]:
        print("ERR:" + str(d["error"].get("code",""))[:30])
    else:
        print(d.get("provider","?"))
except Exception:
    print("PARSE_ERR")
')
  echo "$PROV"
  echo "$PROV" >> "$TMP"
done

echo
echo "=== распределение ==="
sort "$TMP" | uniq -c | sort -rn
rm "$TMP"
