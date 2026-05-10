# Прогон qwen/qwen3-coder-30b-a3b-instruct

**Дата завершения:** 2026-05-10T22:25:26.751031+03:00  
**Всего репозиториев:** 8  
**Всего ablation-запусков:** 144  
**Успешных запусков (≥1 валидный тест):** 72/144 (50.0 %)  
**Всего валидных тестов:** 79  
**Токенов всего:** prompt=3,762,106 + completion=1,425,087 = 5,187,193

## Параметры запуска

- **OpenRouter provider pin:** `Novita`
- **provider.allow_fallbacks:** (default)
- **temperature:** `[0]`
- **seed:** `[42, 43, 44]` (seed-base + run_index - 1)
- **ablation-конфиги:** full, no-coverage, no-pruning, no-smart-diff, no-structured-feedback, no-types
- **runs/config:** 3 (различаются seed)
- **окружение:** WSL2 / Ubuntu, Go 1.24, Clash Verge TUN

## Сводка по репозиториям

Колонки:
- **успешных runs** — число запусков (из 18), где агент сгенерил ≥1 валидный тест
- **валидных тестов** — суммарное число валидных тестов по всем 18 запускам
- **средн. branch% / diff%** — среднее по тем запускам, где coverage был посчитан

| repo | base..head | runs | успешных runs | валидных тестов | средн. branch% | средн. diff% |
|------|-----------|-----:|--------------:|----------------:|---------------:|-------------:|
| `burntsushi-toml` | `d716584e..dcb23465` | 18 | 5 | 6 | 96.7% | 100.0% |
| `etcd-io-bbolt` | `5a7468c8..36efe3ee` | 18 | 10 | 10 | 43.1% | 77.8% |
| `gin-gonic-gin` | `fb258344..472d086a` | 18 | 8 | 8 | 86.8% | 59.6% |
| `google-uuid` | `c58770eb..a2b2b323` | 18 | 3 | 3 | 100.0% | 66.7% |
| `gorilla-mux` | `de7178dc..525206d7` | 18 | 18 | 24 | 98.6% | 98.1% |
| `hashicorp-raft` | `5157c19c..91745625` | 18 | 12 | 12 | 100.0% | 88.9% |
| `restic-restic` | `f78e3f36..880b08f9` | 18 | 13 | 13 | 62.7% | 89.2% |
| `spf13-cobra` | `5c962a22..4cafa37b` | 18 | 3 | 3 | 82.9% | 77.8% |

## Состав файлов

```
qwen-qwen3-coder-30b-a3b-instruct/
├─ benchmark-index.json       # сводный индекс по всем 8 репо
├─ RUN-INFO.md                # этот файл
├─ burntsushi-toml/
│  ├─ repo.json               # сводка по репо (18 ablation-runs)
│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента
├─ etcd-io-bbolt/
│  ├─ repo.json               # сводка по репо (18 ablation-runs)
│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента
├─ gin-gonic-gin/
│  ├─ repo.json               # сводка по репо (18 ablation-runs)
│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента
├─ google-uuid/
│  ├─ repo.json               # сводка по репо (18 ablation-runs)
│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента
├─ gorilla-mux/
│  ├─ repo.json               # сводка по репо (18 ablation-runs)
│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента
├─ hashicorp-raft/
│  ├─ repo.json               # сводка по репо (18 ablation-runs)
│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента
├─ restic-restic/
│  ├─ repo.json               # сводка по репо (18 ablation-runs)
│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента
├─ spf13-cobra/
│  ├─ repo.json               # сводка по репо (18 ablation-runs)
│  └─ <config>-run<N>.json    # 6×3 = 18 отчётов агента
```

## Воспроизведение

```bash
PROVIDER=Novita \
  bash scripts/run-model.sh qwen/qwen3-coder-30b-a3b-instruct 3 60
```

Подробное описание методологии — в `план.md`, §6 (выбор репозиториев), §10 (контроль воспроизводимости).
