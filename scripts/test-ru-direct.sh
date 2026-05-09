#!/usr/bin/env bash
# Безопасный тест: работает ли OpenRouter с прямого RU-IP.
# Алгоритм:
#   1. Ставит запущенный testgen-bench/testgen-agent на SIGSTOP (заморозка).
#   2. Ждёт пока ты переключишь Clash в DIRECT/выключишь.
#   3. Делает реальный chat-completion запрос к Qwen 2.5 7B.
#   4. Ждёт пока ты вернёшь Clash в TUN.
#   5. Снимает SIGSTOP -> прогон продолжается.
#
# В момент пауз TCP-keep-alive обычно живёт >2 минут, так что in-flight запросы
# скорее всего переживут. В худшем случае retry-логика агента (3 попытки с 1-4с
# backoff) дотянет, либо потеряем 1 файл (~$0.0001 на Qwen 7B).

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

echo "═══════════════════════════════════════════════════════"
echo "  Тест прямого подключения к OpenRouter с RU-IP"
echo "═══════════════════════════════════════════════════════"
echo

PIDS=$(pgrep -f 'testgen-bench|testgen-agent' || true)
if [ -n "$PIDS" ]; then
  echo "Найдены процессы прогона:"
  for p in $PIDS; do
    echo "  pid=$p $(ps -p "$p" -o args= 2>/dev/null | head -c 80)"
  done
else
  echo "Процессы прогона не найдены (это ок, если хочешь просто протестировать)."
fi
echo

read -r -p "Шаг 1/4: нажми Enter чтобы заморозить прогон (kill -STOP) ..."
if [ -n "$PIDS" ]; then
  for p in $PIDS; do kill -STOP "$p" 2>/dev/null || true; done
  echo "✓ Прогон заморожен."
fi
echo

cat <<'TXT'
Шаг 2/4: переключи Clash Verge в режим DIRECT (или выключи).
   Самый простой способ: правый клик по иконке -> Outbound mode -> Direct.
   Или в GUI: System Proxy / TUN — выключить.

Не торопись, секунд 5-10 на переключение нормально.
TXT
read -r -p "Готово? Нажми Enter чтобы запустить тест с RU-IP ..."
echo

echo "── текущий внешний IP (должен быть RU) ──"
IP=$(curl -s --max-time 10 https://api.ipify.org || echo "(ошибка)")
echo "  IP: $IP"
GEO=$(curl -s --max-time 10 https://ipinfo.io/json || echo '{}')
COUNTRY=$(echo "$GEO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('country','?'))" 2>/dev/null || echo "?")
ORG=$(echo "$GEO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('org','?'))" 2>/dev/null || echo "?")
echo "  страна: $COUNTRY"
echo "  оператор: $ORG"
echo

echo "── проверка доступа к openrouter.ai (HEAD) ──"
HEAD_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$TESTGEN_API_URL/models" || echo "ERR")
echo "  GET $TESTGEN_API_URL/models -> HTTP $HEAD_CODE"
echo

echo "── реальный inference-запрос к qwen/qwen-2.5-7b-instruct ──"
RESP=$(curl -s --max-time 30 -X POST "$TESTGEN_API_URL/chat/completions" \
  -H "Authorization: Bearer $TESTGEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen/qwen-2.5-7b-instruct",
    "temperature": 0,
    "max_tokens": 20,
    "messages": [
      {"role":"system","content":"You answer with one short word only."},
      {"role":"user","content":"Reply with the single word: alive"}
    ]
  }' || echo '{"error":"curl-failed"}')

echo
echo "Ответ от OpenRouter:"
echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"
echo

echo "── вердикт ──"
CONTENT=$(echo "$RESP" | python3 -c "import sys,json
try:
    d = json.load(sys.stdin)
    if 'error' in d:
        print('ERROR:', d['error'].get('message') if isinstance(d['error'], dict) else d['error'])
    elif 'choices' in d and d['choices']:
        print('OK:', d['choices'][0]['message']['content'].strip())
    else:
        print('UNKNOWN_FORMAT')
except Exception as e:
    print('PARSE_ERROR:', e)
" 2>/dev/null || echo "(не распарсилось)")
echo "  $CONTENT"
echo

cat <<'TXT'
Шаг 3/4: верни Clash в режим TUN (или включи обратно).
TXT
read -r -p "Готово? Нажми Enter чтобы разморозить прогон (kill -CONT) ..."
if [ -n "$PIDS" ]; then
  for p in $PIDS; do kill -CONT "$p" 2>/dev/null || true; done
  echo "✓ Прогон возобновлён."
fi
echo

echo "Шаг 4/4: проверь логи прогона:"
echo "  wsl -d Ubuntu -e bash -lc 'tail -f \"/mnt/d/Дз/4 семестр/НИР/эксперимент/логи/qwen-qwen-2.5-7b-instruct.log\"'"
echo
echo "Если в шаге 2 был получен content='alive' (или похожее непустое слово) -"
echo "значит из RU-IP всё работает и Clash можно вообще выключить."
echo "Если был 'error' с упоминанием 'forbidden region' / 401 / 403 -"
echo "OpenRouter блокирует RU, нужно держать Clash включённым."
