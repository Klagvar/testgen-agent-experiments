#!/usr/bin/env bash
# Тестирует каждого провайдера OpenRouter для модели с прямого RU-IP.
# Алгоритм:
#   1. Получаем список endpoints (провайдеров) для модели.
#   2. Ставим прогон на SIGSTOP.
#   3. Ждём пока ты переключишь Clash в DIRECT.
#   4. По очереди шлём inference-запрос с явным provider.only=[X], allow_fallbacks=false.
#   5. Печатаем сводку: какие провайдеры пускают RU, какие — нет.
#   6. Ждём пока ты вернёшь Clash в TUN, снимаем SIGSTOP.

set -e
set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE not found"
  exit 1
fi
# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a
TESTGEN_API_KEY="${TESTGEN_API_KEY%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL%$'\r'}"
TESTGEN_API_URL="${TESTGEN_API_URL:-https://openrouter.ai/api/v1}"

if [ -z "${TESTGEN_API_KEY:-}" ]; then
  echo "❌ TESTGEN_API_KEY missing"
  exit 1
fi

MODEL="${1:-qwen/qwen-2.5-7b-instruct}"

echo "═══════════════════════════════════════════════════════"
echo "  Тест всех провайдеров за $MODEL с RU-IP"
echo "═══════════════════════════════════════════════════════"
echo

echo "── получаем список endpoints через openrouter ──"
ENDPOINTS_JSON=$(curl -s --max-time 15 "$TESTGEN_API_URL/models/$MODEL/endpoints" \
  -H "Authorization: Bearer $TESTGEN_API_KEY")

if [ -z "$ENDPOINTS_JSON" ]; then
  echo "❌ пустой ответ от openrouter"
  exit 1
fi

PROVIDERS=$(echo "$ENDPOINTS_JSON" | python3 -c '
import json, sys
d = json.load(sys.stdin)
data = d.get("data", d)
eps = data.get("endpoints", []) if isinstance(data, dict) else []
for ep in eps:
    print(ep.get("provider_name", "?"))
')

if [ -z "$PROVIDERS" ]; then
  echo "❌ не удалось распарсить провайдеров. Сырой ответ:"
  echo "$ENDPOINTS_JSON" | head -c 600
  exit 1
fi

NUM_PROVIDERS=$(echo "$PROVIDERS" | wc -l | tr -d ' ')
echo "найдено провайдеров: $NUM_PROVIDERS"
echo "$PROVIDERS" | nl -ba
echo

PIDS=$(pgrep -f 'testgen-bench|testgen-agent' || true)
if [ -n "$PIDS" ]; then
  echo "Найдены процессы прогона: $PIDS"
fi

read -r -p "Шаг 1/4: нажми Enter чтобы заморозить прогон (kill -STOP) ..."
if [ -n "$PIDS" ]; then
  for p in $PIDS; do kill -STOP "$p" 2>/dev/null || true; done
  echo "✓ Прогон заморожен."
fi
echo

echo "Шаг 2/4: переключи Clash Verge в DIRECT (или выключи)."
read -r -p "Готово? Нажми Enter чтобы запустить тесты с RU-IP ..."
echo

echo "── проверка текущего IP ──"
IP=$(curl -s --max-time 8 https://api.ipify.org || echo "?")
GEO_JSON=$(curl -s --max-time 8 https://ipinfo.io/json 2>/dev/null || echo "{}")
COUNTRY=$(echo "$GEO_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('country','?'))" 2>/dev/null || echo "?")
ORG=$(echo "$GEO_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('org','?'))" 2>/dev/null || echo "?")
echo "  IP=$IP  страна=$COUNTRY  оператор=$ORG"
if [ "$COUNTRY" != "RU" ]; then
  echo "  ⚠️  страна не RU — ты точно переключил Clash в DIRECT?"
  read -r -p "  всё равно продолжить? (y/n) " yn
  if [ "$yn" != "y" ]; then
    echo "отмена"
    if [ -n "$PIDS" ]; then for p in $PIDS; do kill -CONT "$p" 2>/dev/null || true; done; fi
    exit 1
  fi
fi
echo

RESULTS_FILE="/tmp/ru-providers-$$.txt"
: > "$RESULTS_FILE"

echo "── тестируем по одному провайдеру ──"
i=0
while IFS= read -r PROV; do
  [ -z "$PROV" ] && continue
  i=$((i+1))
  printf "  [%d/%d] %-25s ... " "$i" "$NUM_PROVIDERS" "$PROV"

  REQ_BODY=$(MODEL="$MODEL" PROV="$PROV" python3 -c '
import json, os
print(json.dumps({
  "model": os.environ["MODEL"],
  "temperature": 0,
  "max_tokens": 5,
  "messages": [
    {"role": "system", "content": "Reply with one short word."},
    {"role": "user", "content": "Reply with: ok"}
  ],
  "provider": {"only": [os.environ["PROV"]], "allow_fallbacks": False}
}))
')

  RESP=$(curl -s --max-time 25 -w "\n__HTTP_STATUS__:%{http_code}" \
    -X POST "$TESTGEN_API_URL/chat/completions" \
    -H "Authorization: Bearer $TESTGEN_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$REQ_BODY" 2>&1 || echo "")

  STATUS=$(echo "$RESP" | tail -n1 | sed 's/.*__HTTP_STATUS__://')
  BODY=$(echo "$RESP" | sed '$d')
  VERDICT=$(echo "$BODY" | python3 -c '
import json, sys
try:
    txt = sys.stdin.read().strip()
    if not txt:
        print("EMPTY")
    else:
        d = json.loads(txt)
        if "error" in d and d["error"]:
            err = d["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            code = err.get("code") if isinstance(err, dict) else ""
            print(f"FAIL [{code}] {msg[:120]}")
        elif "choices" in d and d["choices"]:
            c = d["choices"][0]["message"]["content"].strip()
            prov = d.get("provider", "?")
            usage = d.get("usage", {})
            cost = usage.get("cost", 0)
            try:
                cost_s = f"${cost:.6f}"
            except Exception:
                cost_s = str(cost)
            print(f"OK provider={prov} content={c[:30]!r} cost={cost_s}")
        else:
            print(f"UNKNOWN: {str(d)[:120]}")
except Exception as e:
    print(f"PARSE_ERROR: {e}")
')
  printf "HTTP=%s | %s\n" "$STATUS" "$VERDICT"
  echo "$PROV|$STATUS|$VERDICT" >> "$RESULTS_FILE"
done <<< "$PROVIDERS"

echo
echo "── сводка ──"
OK_COUNT=$(grep -c "|OK " "$RESULTS_FILE" || true)
FAIL_COUNT=$(grep -c "|FAIL" "$RESULTS_FILE" || true)
echo "OK: $OK_COUNT  FAIL: $FAIL_COUNT  total: $i"
echo
echo "пропускают RU:"
grep "|OK " "$RESULTS_FILE" | awk -F'|' '{print "  + " $1}' || true
echo
echo "блокируют RU:"
grep "|FAIL" "$RESULTS_FILE" | awk -F'|' '{printf "  - %-25s -- %s\n", $1, $3}' || true
echo

read -r -p "Шаг 3/4: верни Clash в TUN. Нажми Enter чтобы разморозить прогон ..."
if [ -n "$PIDS" ]; then
  for p in $PIDS; do kill -CONT "$p" 2>/dev/null || true; done
  echo "✓ Прогон возобновлён."
fi

echo
echo "Шаг 4/4: лог сохранён в $RESULTS_FILE (пропадёт при перезагрузке)"
