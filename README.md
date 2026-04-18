# E-State

**Прозорість у кожному квадратному метрі.** A GovTech SaaS that automates the audit of communal assets for Ukrainian ОТГ by cross-checking the ДЗК (land cadaster) and ДРРП (real-estate registry).

> BEST Hackathon 2026 project — see [docs/PRD.md](docs/PRD.md) for the full product brief and the index to all implementation docs.

## Stack

- **Backend** — FastAPI + Pandas (data core) + SQLAlchemy + SQLite (dev) / Postgres (prod)
- **Web** — Next.js 15 App Router + Tailwind CSS + Shadcn/ui
- **Tooling** — `uv` for Python, `npm` for JS

## Repo layout

```
apps/web/                 Next.js 15 (back-office, inspector, citizen portal)
services/api/             FastAPI data service
docs/                     All authoritative docs (architecture, matcher spec, etc.)
.cursor/                  Cursor rules + skills (ECC bundle)
```

## Quick start

```bash
# Backend — run from the repo root (uv workspace picks up services/api automatically)
uv sync --all-extras
uv run e-state seed-from-docs          # ingest + match on sample data (~40s)
uv run uvicorn --app-dir services/api app.main:app --reload --port 8000

# Web (in another terminal)
cd apps/web
npm install
npm run dev
```

Full setup and seeding instructions: [docs/setup.md](docs/setup.md).

## Documentation map

[docs/architecture.md](docs/architecture.md) · [docs/data-dictionary.md](docs/data-dictionary.md) · [docs/data-model.md](docs/data-model.md) · [docs/data-matcher-spec.md](docs/data-matcher-spec.md) · [docs/api-contract.md](docs/api-contract.md) · [docs/user-flows.md](docs/user-flows.md) · [docs/design-system.md](docs/design-system.md) · [docs/legal-compliance.md](docs/legal-compliance.md) · [docs/roadmap.md](docs/roadmap.md) · [docs/demo-script.md](docs/demo-script.md) · [docs/sample-findings.md](docs/sample-findings.md)

## License

Private, hackathon-internal. Not yet licensed for external redistribution.
