# testgen-agent-experiments

Артефакты экспериментальной оценки [`testgen-agent`][agent] из главы 5
ВКР. Сюда входят: дизайн эксперимента, датасет (8 Go-репозиториев с
зафиксированными парами коммитов `base..head`), скрипты orchestration,
сырые JSON-отчёты по 864 запускам и итоговые таблицы/графики.

[agent]: https://github.com/Klagvar/testgen-agent

## Структура

```
testgen-agent-experiments/
├── план.md             # дизайн эксперимента (источник истины)
├── кандидаты-репо.md   # шорт-лист рассмотренных репо + критерии отбора
├── dataset.yaml        # финальный набор репо/PR для прогона
├── scripts/            # PowerShell-скрипты orchestration
├── workdir/            # клоны тестируемых репо (в .gitignore)
├── результаты/
│   ├── raw/            # JSON-отчёты по каждой ячейке куба
│   └── агрегированные/ # CSV-сводки и графики
└── анализ/             # Jupyter-ноуты с финальными таблицами
```

## Запуск

Предусловия: установлены Go 1.26+, git, доступ к OpenRouter API.

```powershell
$env:TESTGEN_API_URL = "https://openrouter.ai/api/v1"
$env:TESTGEN_API_KEY = "<openrouter-key>"
$env:TESTGEN_MODEL   = "openai/gpt-4o-mini"

# Smoke-тест на одном репо
./scripts/smoke.ps1

# Полный прогон по всем моделям
./scripts/run-all.ps1
```

## Связь с агентом

Версия `testgen-agent`, на которой получены результаты, фиксируется
тегом и подключается как git submodule в `agent/`. Перед прогоном:

```powershell
git submodule update --init
go install ./agent/cmd/agent
go install ./agent/cmd/benchmark
go install ./agent/cmd/ablate-report
```

## Воспроизводимость

- `--temperature 0`, `--seed = 42 + run_index − 1` (т.е. 42, 43, 44 для
  трёх повторов).
- Между каждым прогоном агент получает чистую рабочую копию через
  `git reset --hard <head> && git clean -fdx` (см. `план.md` §10.5).
- Все параметры (модель, seed, run_index, конфигурация ablation,
  коммиты репозитория) сохраняются в JSON-отчёте каждого прогона.
