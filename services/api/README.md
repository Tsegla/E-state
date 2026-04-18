# services/api — E-State data service

FastAPI + Pandas service: ingest ДЗК/ДРРП, run the matcher, expose the REST API.

See repo root [README.md](../../README.md) and [docs/setup.md](../../docs/setup.md) for setup.

## Module overview

- `app/ingest/` — read xlsx/csv, normalize per [docs/data-dictionary.md](../../docs/data-dictionary.md)
- `app/matcher/` — pure DataFrame pipeline with 8 detectors
- `app/domain/` — typed records (no DB/HTTP dependencies)
- `app/db/` — SQLAlchemy models mirroring the domain
- `app/api/` — FastAPI routers + DTOs + response envelope
- `app/security/` — JWT, PII masking, audit log
- `app/cli.py` — `uv run e-state seed-from-docs` and friends
