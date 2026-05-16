# Прогон deepseek/deepseek-chat

**Дата завершения:** 2026-05-14T04:00:47.362231+03:00  
**Всего репозиториев:** 8  
**Всего ablation-запусков:** 144  
**Успешных запусков (≥1 валидный тест):** 80/144 (55.6 %)  
**Всего валидных тестов:** 88  
**Токенов всего:** prompt=3,241,133 + completion=554,861 = 3,795,994

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
| `burntsushi-toml` | `d716584e..dcb23465` | 18 | 10 | 15 | 94.4% | 97.7% |
| `etcd-io-bbolt` | `5a7468c8..36efe3ee` | 18 | 17 | 17 | 44.6% | 78.9% |
| `gin-gonic-gin` | `fb258344..472d086a` | 18 | 14 | 14 | 86.8% | 59.6% |
| `google-uuid` | `c58770eb..a2b2b323` | 18 | 7 | 7 | 100.0% | 100.0% |
| `gorilla-mux` | `de7178dc..525206d7` | 18 | 8 | 9 | 98.8% | 95.2% |
| `hashicorp-raft` | `5157c19c..91745625` | 18 | 11 | 12 | 87.5% | 42.5% |
| `restic-restic` | `f78e3f36..880b08f9` | 18 | 13 | 14 | 66.4% | 89.7% |
| `spf13-cobra` | `5c962a22..4cafa37b` | 18 | 0 | 0 | — | — |

## Состав файлов

```
/
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
  bash scripts/run-model.sh deepseek/deepseek-chat 3 60
```

Подробное описание методологии — в `план.md`, §6 (выбор репозиториев), §10 (контроль воспроизводимости).
