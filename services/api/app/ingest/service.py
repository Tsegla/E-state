"""Orchestrate reading the two source workbooks and persisting canonical rows.

This module writes to the DB; the matcher downstream reads from it. Pure
transformation logic lives in ``normalize`` and ``excel``; here we wire them
together and keep persistence concerns in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.models import DatasetRow, LandParcelRow, PersonRow, RealEstateRow
from app.domain.enums import DatasetStatus
from app.ingest.excel import read_ner_workbook, read_zem_workbook
from app.ingest.normalize import normalize_name


@dataclass(frozen=True, slots=True)
class IngestResult:
    dataset_id: UUID
    zem_rows: int
    ner_rows: int
    persons: int


def ingest_dataset(
    session: Session,
    *,
    zem_path: str | Path,
    ner_path: str | Path,
    label: str,
    uploaded_by: str | None = None,
) -> IngestResult:
    """Ingest a pair of ДЗК/ДРРП files into a new dataset.

    Writes:
      * one ``dataset`` row
      * many ``land_parcel`` rows
      * many ``real_estate`` rows
      * upserts into ``person`` union

    Does **not** run the matcher — call ``matcher.engine.run`` separately so
    ingest and matching can be rerun independently.
    """
    dataset = DatasetRow(
        id=uuid4(),
        label=label,
        uploaded_by=uploaded_by,
        source_zem_blob=str(zem_path),
        source_ner_blob=str(ner_path),
        status=DatasetStatus.INGESTING.value,
    )
    session.add(dataset)
    session.flush()

    zem_rows = 0
    ner_rows = 0
    persons: dict[str, dict[str, object]] = {}

    for rec in read_zem_workbook(zem_path):
        parcel = LandParcelRow(
            id=uuid4(),
            dataset_id=dataset.id,
            cadastral_no=rec["cadastral_no"],
            koatuu=rec["koatuu"],
            ownership_form=rec["ownership_form"],
            intended_use_code=rec["intended_use_code"],
            intended_use_label=rec["intended_use_label"],
            location_admin=rec["location_admin"],
            agri_use_kind=rec["agri_use_kind"],
            area_m2=rec["area_m2"],
            valuation_kop=rec["valuation_kop"],
            owner_tax_id=rec["owner_tax_id"],
            owner_name_raw=rec["owner_name_raw"],
            share=rec["share"],
            registered_at=rec["registered_at"],
            record_no=rec["record_no"],
            registrar=rec["registrar"],
            record_kind=rec["record_kind"],
            record_subkind=rec["record_subkind"],
        )
        session.add(parcel)
        zem_rows += 1
        tid = rec["owner_tax_id"]
        if tid:
            persons.setdefault(
                tid,
                {
                    "full_name_raw": rec["owner_name_raw"] or "",
                    "sources": set(),
                },
            )["sources"].add("dzk")  # type: ignore[union-attr]

    for rec in read_ner_workbook(ner_path):
        re_row = RealEstateRow(
            id=uuid4(),
            dataset_id=dataset.id,
            owner_tax_id=rec["owner_tax_id"],
            owner_name_raw=rec["owner_name_raw"],
            object_type_raw=rec["object_type_raw"],
            object_type_norm=rec["object_type_norm"],
            address_raw=rec["address_raw"],
            address_norm=rec["address_norm"],
            area_m2=rec["area_m2"],
            registered_at=rec["registered_at"],
            terminated_at=rec["terminated_at"],
            joint_ownership_kind=rec["joint_ownership_kind"],
            share=rec["share"],
        )
        session.add(re_row)
        ner_rows += 1
        tid = rec["owner_tax_id"]
        if tid:
            entry = persons.setdefault(
                tid,
                {
                    "full_name_raw": rec["owner_name_raw"] or "",
                    "sources": set(),
                },
            )
            entry["sources"].add("drrp")  # type: ignore[union-attr]
            if not entry["full_name_raw"] and rec["owner_name_raw"]:
                entry["full_name_raw"] = rec["owner_name_raw"]

    existing = {
        row.tax_id: row
        for row in session.query(PersonRow).filter(PersonRow.tax_id.in_(list(persons))).all()
    }
    for tid, info in persons.items():
        name_raw = str(info["full_name_raw"])
        sources = sorted(info["sources"])  # type: ignore[arg-type]
        if tid in existing:
            row = existing[tid]
            if name_raw and not row.full_name_raw:
                row.full_name_raw = name_raw
                row.full_name_norm = normalize_name(name_raw)
            existing_sources = set(row.sources or [])
            row.sources = sorted(existing_sources.union(sources))
        else:
            session.add(
                PersonRow(
                    tax_id=tid,
                    full_name_raw=name_raw,
                    full_name_norm=normalize_name(name_raw),
                    sources=sources,
                )
            )

    dataset.status = DatasetStatus.MATCHED.value  # will be overridden by matcher if needed
    session.flush()

    return IngestResult(
        dataset_id=dataset.id,
        zem_rows=zem_rows,
        ner_rows=ner_rows,
        persons=len(persons),
    )
