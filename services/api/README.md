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

## Migrations

Alembic lives under `alembic/`. Two revisions today:

- `0001` — initial schema.
- `0002` — adds `finding.assignment_note` / `finding.assigned_at`, `field_visit.source_of_truth` / `field_visit.truth_evidence_id`, and the canonical `verified_asset` table. See [docs/data-model.md §2.8](../../docs/data-model.md).

To apply against your dev DB:

```bash
uv run alembic upgrade head
```

If you have an older local `e_state_dev.db` that predates `0002` and you don't mind losing the data, the fastest reset is:

```bash
rm e_state_dev.db && uv run alembic upgrade head && uv run e-state seed-from-docs
```

