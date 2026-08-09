# Test guide

> Tag: [AURA-1.0-baseline]

## Layout

| Directory | Marker | Runs by default? | Requirements |
|---|---|---|---|
| `tests/` (root files) | — (unmarked) | yes | none — existing 408-test suite |
| `tests/unit/` | `unit` | yes | none |
| `tests/contract/` | `contract` | yes | none |
| `tests/integration/` | `integration` | **no** | `DATABASE_URL` (self-skips otherwise) |
| `tests/e2e/` | `e2e` | **no** | running server + LLM provider |

New tests go in `tests/unit/` (pure, no I/O) or `tests/contract/`
(cross-module invariants). Both must stay green with **zero external services**
and complete well under ~30s. `tests/integration/` is for DB-backed checks and
must self-skip when `DATABASE_URL` is missing; `tests/e2e/` is opt-in full-flow.

## Running

```powershell
.\venv\Scripts\python.exe -m pytest           # default: unit + contract + unmarked root tests
.\venv\Scripts\python.exe -m pytest tests\unit\data   # just the taxonomy canary
.\venv\Scripts\python.exe -m pytest -m integration -k "not e2e"   # DB suite (needs DATABASE_URL)
```

Run via `python -m pytest` **from the repo root**: that puts the project root on
`sys.path` so `import app` resolves (same convention the root suite relies on).

## Markers (`pytest.ini`)

`unit`, `contract`, `integration`, `db`, `llm`, `e2e`. The default
`addopts` filter is `-m "not integration and not e2e and not llm"`.

## The taxonomy canary (`tests/unit/data/test_taxonomy_integrity.py`)

Every competency id referenced by the knowledge bases (graph, role brain,
resolver, skill map) must exist in `COMPETENCY_TAXONOMY`. A documented gap is
allowed today — the four tech orphans (`tech_event_driven`, `tech_deployment`,
`tech_caching`, `tech_data_modeling`) — which Wave 1 (`[AURA-1.1][T1-taxonomy]`)
re-adds. Any *other* missing id fails the suite.
