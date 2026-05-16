#!/usr/bin/env bash
# Quick progress check for the running mutation micro-experiment.
set -eu

cd ~/exp
echo "─── process count ───"
pgrep -fc "testgen-bench|testgen-agent" || true
echo

echo "─── per-model progress ───"
for m in qwen-qwen-2.5-7b-instruct qwen-qwen3-coder-30b-a3b-instruct \
         meta-llama-llama-3.3-70b-instruct deepseek-deepseek-chat \
         openai-gpt-4o-mini anthropic-claude-3.5-haiku \
         google-gemini-3-flash-preview; do
  log="логи/mutation-${m}.log"
  if [[ ! -f "$log" ]]; then
    echo "  $m: no log"
    continue
  fi
  gen=$(grep -c "Generating tests via" "$log" 2>/dev/null || echo 0)
  err=$(grep -c "LLM error" "$log" 2>/dev/null || echo 0)
  jsons=$(find "результаты/mutation-microexp/$m" -name "full.json" 2>/dev/null | wc -l)
  done_=""
  if grep -q "═══ Summary ═══" "$log" 2>/dev/null; then
    done_=" [FINISHED]"
  fi
  printf "  %-40s gen=%-3s err=%-3s json=%s%s\n" "$m" "$gen" "$err" "$jsons" "$done_"
done

echo
echo "─── disk size of latest results ───"
du -sh результаты/mutation-microexp 2>/dev/null || true
