"""Assign flow + verified_asset canonical table.

Adds:

- ``finding.assignment_note`` and ``finding.assigned_at`` for the analyst -> inspector handoff.
- ``field_visit.source_of_truth`` and ``field_visit.truth_evidence_id`` so the inspector's
  verdict records which registry (or field override) they accepted.
- ``verified_asset`` canonical table that downstream surfaces read as the main source of truth
  for a resolved finding.

This migration is **idempotent** because ``0001_initial`` uses ``Base.metadata.create_all``
from the live ORM metadata. That means any table/column defined in the current ORM
(including new ones added in this revision) is already created by ``0001`` when the DB is
first stamped. We therefore check the live schema before adding anything.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _existing_columns(inspector: sa.Inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def _existing_fk_names(inspector: sa.Inspector, table: str) -> set[str]:
    return {fk["name"] for fk in inspector.get_foreign_keys(table) if fk.get("name")}


def _existing_index_names(inspector: sa.Inspector, table: str) -> set[str]:
    return {ix["name"] for ix in inspector.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    finding_cols = _existing_columns(inspector, "finding")
    with op.batch_alter_table("finding") as batch:
        if "assignment_note" not in finding_cols:
            batch.add_column(sa.Column("assignment_note", sa.String(length=2000), nullable=True))
        if "assigned_at" not in finding_cols:
            batch.add_column(sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))

    visit_cols = _existing_columns(inspector, "field_visit")
    visit_fks = _existing_fk_names(inspector, "field_visit")
    with op.batch_alter_table("field_visit") as batch:
        if "source_of_truth" not in visit_cols:
            batch.add_column(sa.Column("source_of_truth", sa.String(length=20), nullable=True))
        if "truth_evidence_id" not in visit_cols:
            batch.add_column(sa.Column("truth_evidence_id", sa.CHAR(length=32), nullable=True))
        if "fk_field_visit_truth_evidence" not in visit_fks:
            batch.create_foreign_key(
                "fk_field_visit_truth_evidence",
                "finding_evidence",
                ["truth_evidence_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "verified_asset" not in inspector.get_table_names():
        op.create_table(
            "verified_asset",
            sa.Column("id", sa.CHAR(length=32), primary_key=True),
            sa.Column("finding_id", sa.CHAR(length=32), nullable=False, unique=True),
            sa.Column("dataset_id", sa.CHAR(length=32), nullable=False),
            sa.Column("person_tax_id", sa.String(length=20), nullable=False),
            sa.Column("source_of_truth", sa.String(length=20), nullable=False),
            sa.Column("chosen_ref_kind", sa.String(length=30), nullable=True),
            sa.Column("chosen_ref_id", sa.CHAR(length=32), nullable=True),
            sa.Column("object_type", sa.String(length=200), nullable=True),
            sa.Column("area_m2", sa.Float(), nullable=True),
            sa.Column("use", sa.String(length=200), nullable=True),
            sa.Column("address", sa.String(length=500), nullable=True),
            sa.Column("verified_by", sa.String(length=100), nullable=False),
            sa.Column(
                "verified_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["finding_id"], ["finding.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["dataset_id"], ["dataset.id"], ondelete="CASCADE"),
        )

    # Re-inspect so index checks see the freshly created table.
    inspector = sa.inspect(bind)
    verified_indexes = _existing_index_names(inspector, "verified_asset")
    if "idx_verified_asset_person" not in verified_indexes:
        op.create_index("idx_verified_asset_person", "verified_asset", ["person_tax_id"])
    if "idx_verified_asset_dataset" not in verified_indexes:
        op.create_index("idx_verified_asset_dataset", "verified_asset", ["dataset_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "verified_asset" in inspector.get_table_names():
        for ix in ("idx_verified_asset_dataset", "idx_verified_asset_person"):
            if ix in _existing_index_names(inspector, "verified_asset"):
                op.drop_index(ix, table_name="verified_asset")
        op.drop_table("verified_asset")

    visit_cols = _existing_columns(inspector, "field_visit")
    visit_fks = _existing_fk_names(inspector, "field_visit")
    with op.batch_alter_table("field_visit") as batch:
        if "fk_field_visit_truth_evidence" in visit_fks:
            batch.drop_constraint("fk_field_visit_truth_evidence", type_="foreignkey")
        if "truth_evidence_id" in visit_cols:
            batch.drop_column("truth_evidence_id")
        if "source_of_truth" in visit_cols:
            batch.drop_column("source_of_truth")

    finding_cols = _existing_columns(inspector, "finding")
    with op.batch_alter_table("finding") as batch:
        if "assigned_at" in finding_cols:
            batch.drop_column("assigned_at")
        if "assignment_note" in finding_cols:
            batch.drop_column("assignment_note")
