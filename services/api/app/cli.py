"""Typer CLI: ``uv run e-state ...``

Commands:
  seed-from-docs   Ingest the xlsx pair under docs/ into a fresh dataset and run the matcher.
  run-matcher      Rerun the matcher for an existing dataset.
  token            Mint a short-lived dev token for a given role.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import typer

from app.db.session import db_session, init_db
from app.ingest.service import ingest_dataset
from app.matcher.engine import run as run_matcher
from app.security.auth import Principal, create_access_token

app = typer.Typer(add_completion=False, help="E-State data service CLI")

DEFAULT_ZEM = Path(__file__).resolve().parents[3] / "docs" / "ДРРП земля.xlsx"
DEFAULT_NER = Path(__file__).resolve().parents[3] / "docs" / "ДРРП нерухомість.xlsx"


@app.command("init-db")
def init_db_cmd() -> None:
    """Create all tables (dev convenience)."""
    init_db()
    typer.echo("tables created")


@app.command("seed-from-docs")
def seed_from_docs(
    zem: Path = typer.Option(DEFAULT_ZEM, exists=True, readable=True),
    ner: Path = typer.Option(DEFAULT_NER, exists=True, readable=True),
    label: str = typer.Option("Демо-набір docs/"),
    run_match: bool = typer.Option(True, help="Run matcher after ingest"),
) -> None:
    """Ingest the xlsx files under ``docs/`` and run the matcher."""
    init_db()
    with db_session() as session:
        result = ingest_dataset(
            session,
            zem_path=zem,
            ner_path=ner,
            label=label,
            uploaded_by="cli",
        )
        typer.echo(
            f"dataset={result.dataset_id} zem={result.zem_rows} ner={result.ner_rows} persons={result.persons}"
        )
        if run_match:
            match_result = run_matcher(session, result.dataset_id)
            typer.echo(
                f"findings={match_result.findings_created} by_type={match_result.by_type} "
                f"by_severity={match_result.by_severity} duration_ms={match_result.duration_ms}"
            )


@app.command("run-matcher")
def run_matcher_cmd(dataset_id: str) -> None:
    """Rerun the matcher for an existing dataset."""
    with db_session() as session:
        result = run_matcher(session, UUID(dataset_id))
        typer.echo(
            f"findings={result.findings_created} by_type={result.by_type} "
            f"by_severity={result.by_severity} duration_ms={result.duration_ms}"
        )


@app.command("token")
def token(
    subject: str = typer.Option(...),
    role: str = typer.Option("analyst", help="analyst | inspector | admin"),
    community: str | None = typer.Option(None),
) -> None:
    """Mint a short-lived dev JWT."""
    token = create_access_token(Principal(subject=subject, role=role, community=community))
    typer.echo(token)


if __name__ == "__main__":  # pragma: no cover
    app()
