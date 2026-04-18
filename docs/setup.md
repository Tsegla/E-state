# E-State — Local Setup & Developer Handbook

> Getting from a fresh clone to a running local stack in under 10 minutes. Extends [architecture.md §2](architecture.md#2-repository-layout).

## 1. Prerequisites

| Tool | Version | Why |
|---|---|---|
| Python | 3.12+ | Backend |
| [`uv`](https://github.com/astral-sh/uv) | latest | Python env + deps (repo root is a uv workspace) |
| Node.js | 20 LTS+ | Web |
| `npm` | 10+ (ships with Node) | Web deps |
| SQLite | 3.40+ (bundled with Python) | Dev DB |
| Git LFS (optional) | | Only if source xlsx is tracked |

Install on macOS (Apple Silicon or Intel):

```bash
brew install uv node@20
```

## 2. One-time bootstrap

The repo root is a uv workspace, so all `uv run …` commands work from `BEST Hackathon/` directly — no need to `cd services/api`.

```bash
git clone <repo-url>
cd "BEST Hackathon"

# Backend (installs both runtime and dev extras into a single .venv at the repo root)
uv sync --all-extras
uv run alembic -c services/api/alembic.ini upgrade head   # init SQLite dev DB

# Web
cd apps/web
npm install
cd ..
```

## 3. Running the stack

Two terminals.

```bash
# Terminal 1 — API (from repo root)
uv run uvicorn --app-dir services/api app.main:app --reload --port 8000

# Terminal 2 — Web
cd apps/web
npm run dev                  # http://localhost:3000
```

Healthcheck: `curl http://localhost:8000/healthz` returns `{"ok": true}`.

## 4. Seeding data for the demo

The two source files provided with the hackathon live under `docs/` and are used as-is. Run from the repo root:

```bash
uv run e-state seed-from-docs \
  --zem "docs/ДРРП земля.xlsx" \
  --ner "docs/ДРРП нерухомість.xlsx" \
  --label "Сокаль demo"
```

This creates a `dataset` row, ingests both files, runs the matcher, and prints the summary. Expected output on this dataset:

```
Dataset: Сокаль demo
  zem rows: 21656
  ner rows: 20382
  persons: 11407   (in both: 10937)
Findings:
  critical:         ~38
  warning:          ~1200
  info:             5080   (TERMINATED_BUT_ACTIVE baseline)
```

Exact numbers drift as detector thresholds evolve; baseline assertions live in `services/api/tests/baselines.json`.

## 5. Environment variables

[`services/api/.env.example`](../services/api/.env.example):

```
APP_ENV=development
DATABASE_URL=sqlite:///./e_state_dev.db
JWT_SECRET=change-me-in-prod
OBJECT_STORAGE_BUCKET=e-state-dev
OBJECT_STORAGE_REGION=auto
OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_ACCESS_KEY=
OBJECT_STORAGE_SECRET_KEY=
CITIZEN_CAPTCHA_PROVIDER=turnstile
CITIZEN_CAPTCHA_SECRET=
LOG_LEVEL=INFO
```

[`apps/web/.env.example`](../apps/web/.env.example):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CAPTCHA_SITE_KEY=
```

Copy to `.env` (not checked in) before running. CI uses GitHub Actions environments, not these files.

## 6. Everyday workflows

### Mint a demo JWT

```bash
uv run e-state token --subject demo --role analyst
# paste the token into apps/web/.env.local as NEXT_PUBLIC_DEMO_TOKEN=<token>
```

### Run the matcher manually

```bash
uv run e-state run-matcher --dataset-id 3c1b...
```

### Run tests

```bash
# Backend (from repo root)
uv run pytest services/api/tests -q                                 # full suite
uv run pytest services/api/tests/test_matcher_detectors.py          # single module

# Web
cd apps/web
npm run build                                    # production build sanity check
```

### Lint & format

```bash
# Backend
uv run ruff check services/api
uv run ruff format services/api
uv run mypy services/api/app

# Web
cd apps/web
npm run lint
npx tsc --noEmit
```

## 7. Common pitfalls

- **"ModuleNotFoundError: openpyxl"** — run `uv sync --all-extras`; it's in `pyproject.toml`.
- **Excel serial dates look like small integers.** That's Excel; use the helper from [data-dictionary.md §4](data-dictionary.md#4-excel-serial--iso-date).
- **OWNER_NAME_MISMATCH never fires.** Expected on the supplied dataset (names are clean). Don't "fix" the detector; write a fixture that proves it fires.
- **`intended_use_code` is empty.** Many rows don't start with a numeric prefix (`Для індивідуального житлового…`). Treat as `None`, let downstream detectors skip.
- **Port 3000 busy.** `PORT=3001 npm run dev`.
- **`uv run e-state` says `No such file or directory`.** You're in a subdirectory that isn't part of the uv workspace, or you forgot `uv sync --all-extras`. Run either from the repo root, or `cd services/api` first.

## 8. Directory cheatsheet

```
services/api/app/main.py                 ← FastAPI entry
services/api/app/matcher/engine.py       ← pipeline orchestrator
services/api/app/matcher/detectors/      ← one file per finding_type
services/api/app/api/routers/            ← one router per domain
apps/web/src/app/(back-office)/          ← staff routes
apps/web/src/app/(inspector)/            ← inspector mobile routes
apps/web/src/app/(citizen)/              ← public citizen portal
apps/web/src/lib/api/client.ts           ← typed fetch wrapper
apps/web/src/i18n/uk.ts                  ← all UI strings
docs/                                    ← these docs
```

## 9. Committing

See [.cursor/rules/common-git-workflow.mdc](../.cursor/rules/common-git-workflow.mdc) — conventional commits, no secrets, PRs include test plan. The `e-state-*` rules in `.cursor/rules/` are enforced on every edit.
