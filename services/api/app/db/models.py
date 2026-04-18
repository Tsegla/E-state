"""SQLAlchemy ORM models.

Mirror the canonical schema in [docs/data-model.md](../../../docs/data-model.md). JSON columns are stored as SQLite JSON / Postgres JSONB
via SQLAlchemy's ``JSON`` generic type.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, TypeDecorator


class _UUIDType(TypeDecorator):
    """SQLite-friendly UUID: stored as 32-char hex."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        if isinstance(value, UUID):
            return value.hex
        return UUID(str(value)).hex

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if value is None:
            return None
        return UUID(value)


UUIDCol = _UUIDType


class Base(DeclarativeBase):
    pass


class DatasetRow(Base):
    __tablename__ = "dataset"

    id: Mapped[UUID] = mapped_column(UUIDCol(), primary_key=True, default=uuid4)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    uploaded_by: Mapped[str | None] = mapped_column(String(200))
    source_zem_blob: Mapped[str | None] = mapped_column(String(500))
    source_ner_blob: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="ingesting", nullable=False)

    land_parcels: Mapped[list["LandParcelRow"]] = relationship(back_populates="dataset")
    real_estate: Mapped[list["RealEstateRow"]] = relationship(back_populates="dataset")
    findings: Mapped[list["FindingRow"]] = relationship(back_populates="dataset")


class PersonRow(Base):
    __tablename__ = "person"

    tax_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    full_name_raw: Mapped[str] = mapped_column(String(300), nullable=False)
    full_name_norm: Mapped[str] = mapped_column(String(300), nullable=False)
    sources: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class LandParcelRow(Base):
    __tablename__ = "land_parcel"

    id: Mapped[UUID] = mapped_column(UUIDCol(), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(
        UUIDCol(), ForeignKey("dataset.id", ondelete="CASCADE"), nullable=False
    )
    cadastral_no: Mapped[str] = mapped_column(String(40), nullable=False)
    koatuu: Mapped[str | None] = mapped_column(String(15))
    ownership_form: Mapped[str | None] = mapped_column(String(50))
    intended_use_code: Mapped[str | None] = mapped_column(String(10))
    intended_use_label: Mapped[str | None] = mapped_column(String(500))
    location_admin: Mapped[str | None] = mapped_column(String(500))
    agri_use_kind: Mapped[str | None] = mapped_column(String(200))
    area_m2: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    valuation_kop: Mapped[int | None] = mapped_column(Integer)
    owner_tax_id: Mapped[str | None] = mapped_column(String(20))
    owner_name_raw: Mapped[str | None] = mapped_column(String(300))
    share: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    registered_at: Mapped[date | None] = mapped_column(Date)
    record_no: Mapped[str | None] = mapped_column(String(60))
    registrar: Mapped[str | None] = mapped_column(String(500))
    record_kind: Mapped[str | None] = mapped_column(String(60))
    record_subkind: Mapped[str | None] = mapped_column(String(500))

    dataset: Mapped[DatasetRow] = relationship(back_populates="land_parcels")

    __table_args__ = (
        Index("idx_land_parcel_owner", "owner_tax_id"),
        Index("idx_land_parcel_cadastral", "cadastral_no"),
        Index("idx_land_parcel_dataset", "dataset_id"),
    )


class RealEstateRow(Base):
    __tablename__ = "real_estate"

    id: Mapped[UUID] = mapped_column(UUIDCol(), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(
        UUIDCol(), ForeignKey("dataset.id", ondelete="CASCADE"), nullable=False
    )
    owner_tax_id: Mapped[str | None] = mapped_column(String(20))
    owner_name_raw: Mapped[str | None] = mapped_column(String(300))
    object_type_raw: Mapped[str | None] = mapped_column(String(200))
    object_type_norm: Mapped[str | None] = mapped_column(String(50))
    address_raw: Mapped[str | None] = mapped_column(String(500))
    address_norm: Mapped[str | None] = mapped_column(String(500))
    area_m2: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    registered_at: Mapped[date | None] = mapped_column(Date)
    terminated_at: Mapped[date | None] = mapped_column(Date)
    joint_ownership_kind: Mapped[str | None] = mapped_column(String(50))
    share: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    dataset: Mapped[DatasetRow] = relationship(back_populates="real_estate")

    __table_args__ = (
        Index("idx_real_estate_owner", "owner_tax_id"),
        Index("idx_real_estate_dataset", "dataset_id"),
    )


class FindingRow(Base):
    __tablename__ = "finding"

    id: Mapped[UUID] = mapped_column(UUIDCol(), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(
        UUIDCol(), ForeignKey("dataset.id", ondelete="CASCADE"), nullable=False
    )
    person_tax_id: Mapped[str] = mapped_column(String(20), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    computed_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_visit_id: Mapped[UUID | None] = mapped_column(
        UUIDCol(), ForeignKey("field_visit.id", ondelete="SET NULL"), nullable=True
    )
    # Analyst -> inspector handoff. The note is persisted here (not in audit_log,
    # which only stores payload hashes) so the inspector sees the context.
    assignment_note: Mapped[str | None] = mapped_column(String(2000))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dataset: Mapped[DatasetRow] = relationship(back_populates="findings")
    evidence: Mapped[list["FindingEvidenceRow"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "person_tax_id", "finding_type", name="uq_finding_person_type"
        ),
        Index("idx_finding_severity", "dataset_id", "severity"),
        Index("idx_finding_status", "dataset_id", "status"),
    )


class FindingEvidenceRow(Base):
    __tablename__ = "finding_evidence"

    id: Mapped[UUID] = mapped_column(UUIDCol(), primary_key=True, default=uuid4)
    finding_id: Mapped[UUID] = mapped_column(
        UUIDCol(), ForeignKey("finding.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    ref_id: Mapped[UUID] = mapped_column(UUIDCol(), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    finding: Mapped[FindingRow] = relationship(back_populates="evidence")


class FieldVisitRow(Base):
    __tablename__ = "field_visit"

    id: Mapped[UUID] = mapped_column(UUIDCol(), primary_key=True, default=uuid4)
    finding_id: Mapped[UUID] = mapped_column(
        UUIDCol(), ForeignKey("finding.id", ondelete="CASCADE"), nullable=False
    )
    inspector_id: Mapped[str] = mapped_column(String(100), nullable=False)
    photo_refs: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    actual_object_type: Mapped[str | None] = mapped_column(String(200))
    actual_area_m2: Mapped[float | None] = mapped_column(Float)
    actual_use: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(2000))
    gps: Mapped[dict | None] = mapped_column(JSON)
    # Which registry the inspector confirmed reflects reality:
    #   "dzk" -> the chosen finding_evidence of kind land_parcel
    #   "drrp" -> the chosen finding_evidence of kind real_estate
    #   "field_override" -> neither; actual_* fields hold the truth
    source_of_truth: Mapped[str | None] = mapped_column(String(20))
    truth_evidence_id: Mapped[UUID | None] = mapped_column(
        UUIDCol(), ForeignKey("finding_evidence.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VerifiedAssetRow(Base):
    """Canonical 'main table' of inspector-verified truth.

    Upserted on every resolving ``field_visit``. Unique per ``finding_id``:
    re-submitting a visit overwrites the previous verdict. Downstream reads
    (analyst detail, reports, optionally citizen portal) should prefer this
    row over the raw registries whenever a verified record exists.
    """

    __tablename__ = "verified_asset"

    id: Mapped[UUID] = mapped_column(UUIDCol(), primary_key=True, default=uuid4)
    finding_id: Mapped[UUID] = mapped_column(
        UUIDCol(),
        ForeignKey("finding.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    dataset_id: Mapped[UUID] = mapped_column(
        UUIDCol(), ForeignKey("dataset.id", ondelete="CASCADE"), nullable=False
    )
    person_tax_id: Mapped[str] = mapped_column(String(20), nullable=False)
    source_of_truth: Mapped[str] = mapped_column(String(20), nullable=False)
    chosen_ref_kind: Mapped[str | None] = mapped_column(String(30))
    chosen_ref_id: Mapped[UUID | None] = mapped_column(UUIDCol())
    object_type: Mapped[str | None] = mapped_column(String(200))
    area_m2: Mapped[float | None] = mapped_column(Float)
    use: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(500))
    verified_by: Mapped[str] = mapped_column(String(100), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_verified_asset_person", "person_tax_id"),
        Index("idx_verified_asset_dataset", "dataset_id"),
    )


class AuditLogRow(Base):
    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(UUIDCol(), primary_key=True, default=uuid4)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    target_table: Mapped[str] = mapped_column(String(60), nullable=False)
    target_id: Mapped[str] = mapped_column(String(60), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_audit_ts", "ts"),)
