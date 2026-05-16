# Прогон anthropic/claude-3.5-haiku

**Дата завершения:** 2026-05-16T03:00:57.860743+03:00  
**Всего репозиториев:** 8  
**Всего ablation-запусков:** 144  
**Успешных запусков (≥1 валидный тест):** 90/144 (62.5 %)  
**Всего валидных тестов:** 91  
**Токенов всего:** prompt=4,106,031 + completion=813,174 = 4,919,205

## Параметры запуска

- **OpenRouter provider pin:** `amazon-bedrock`
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
| `burntsushi-toml` | `d716584e..dcb23465` | 18 | 18 | 19 | 98.4% | 99.7% |
| `etcd-io-bbolt` | `5a7468c8..36efe3ee` | 18 | 1 | 1 | 50.0% | 95.5% |
| `gin-gonic-gin` | `fb258344..472d086a` | 18 | 15 | 15 | 86.8% | 59.6% |
| `google-uuid` | `c58770eb..a2b2b323` | 18 | 15 | 15 | 100.0% | 100.0% |
| `gorilla-mux` | `de7178dc..525206d7` | 18 | 12 | 12 | 100.0% | 100.0% |
| `hashicorp-raft` | `5157c19c..91745625` | 18 | 11 | 11 | 50.0% | 50.0% |
| `restic-restic` | `f78e3f36..880b08f9` | 18 | 15 | 15 | 60.8% | 89.2% |
| `spf13-cobra` | `5c962a22..4cafa37b` | 18 | 3 | 3 | 68.6% | 77.8% |

## Состав файлов

```
anthropic-claude-3.5-haiku/
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
PROVIDER=amazon-bedrock \
  bash scripts/run-model.sh anthropic/claude-3.5-haiku 3 60
```

Подробное описание методологии — в `план.md`, §6 (выбор репозиториев), §10 (контроль воспроизводимости).
