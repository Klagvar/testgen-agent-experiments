# Прогон qwen/qwen-2.5-7b-instruct

**Дата завершения:** 2026-05-10T16:49:31.075649+03:00  
**Всего репозиториев:** 8  
**Всего ablation-запусков:** 144  
**Запусков с валидным тестом:** 22/144 (15.3 %)  
**Токенов всего:** prompt=3,137,664 + completion=641,522 = 3,779,186

## Параметры запуска

- **OpenRouter provider pin:** `Phala`
- **provider.allow_fallbacks:** (default)
- **temperature:** `[0]`
- **seed:** `[42, 43, 44]` (seed-base + run_index - 1)
- **ablation-конфиги:** full, no-coverage, no-pruning, no-smart-diff, no-structured-feedback, no-types
- **runs/config:** 3 (различаются seed)
- **окружение:** WSL2 / Ubuntu, Go 1.24, Clash Verge TUN

## Сводка по репозиториям

| repo | base..head | конфигов | runs | val/total | средн. branch% (где есть) | средн. diff% (где есть) |
|------|-----------|----------|------|-----------|---------------------------|-------------------------|
| `burntsushi-toml` | `d716584e..dcb23465` | 6 | 18 | 3/18 | 92.6% | 100.0% |
| `etcd-io-bbolt` | `5a7468c8..36efe3ee` | 6 | 18 | 4/18 | 25.0% | 43.2% |
| `gin-gonic-gin` | `fb258344..472d086a` | 6 | 18 | 0/18 | — | — |
| `google-uuid` | `c58770eb..a2b2b323` | 6 | 18 | 0/18 | — | — |
| `gorilla-mux` | `de7178dc..525206d7` | 6 | 18 | 0/18 | — | — |
| `hashicorp-raft` | `5157c19c..91745625` | 6 | 18 | 14/18 | 94.4% | 80.9% |
| `restic-restic` | `f78e3f36..880b08f9` | 6 | 18 | 0/18 | — | — |
| `spf13-cobra` | `5c962a22..4cafa37b` | 6 | 18 | 1/18 | — | — |

## Состав файлов

```
qwen-qwen-2.5-7b-instruct/
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
PROVIDER=Phala \
  bash scripts/run-model.sh qwen/qwen-2.5-7b-instruct 3 60
```

Подробное описание методологии — в `план.md`, §6 (выбор репозиториев), §10 (контроль воспроизводимости).
