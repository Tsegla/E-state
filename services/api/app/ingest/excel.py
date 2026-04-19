"""Read ДЗК / ДРРП workbooks and emit canonical row dicts.

The loader first routes the file through
:func:`app.ingest.markitdown_adapter.load_table`, which delegates to pandas for
CSV/XLSX/XLS and to ``microsoft/markitdown`` for PDF/DOCX/HTML. The resulting
DataFrame is then checked against the declarative schemas in
:mod:`app.ingest.schema` before rows are yielded.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from app.ingest.markitdown_adapter import LoadedTable, load_table
from app.ingest.normalize import (
    excel_serial_to_date,
    ga_to_m2,
    normalize_address,
    normalize_cadastral,
    normalize_koatuu,
    normalize_object_type,
    normalize_tax_id,
    parse_float,
    split_intended_use,
    valuation_to_kop,
)
from app.ingest.schema import NER_SCHEMA, ZEM_SCHEMA, InputSchema
from app.ingest.validation import (
    ColumnValidationReport,
    FileValidationReport,
    TableValidationReport,
    ValidationIssue,
    validate_input_file,
    validate_required_columns,
    validate_table_patterns,
)

RowBuilder = Callable[[dict[str, Any]], dict[str, Any] | None]


@dataclass(slots=True)
class WorkbookReadResult:
    """All validation reports + canonical records for a single workbook."""

    records: list[dict[str, Any]]
    file_report: FileValidationReport
    column_report: ColumnValidationReport
    table_report: TableValidationReport
    source_format: str
    extra_issues: list[ValidationIssue] = field(default_factory=list)


def read_zem_workbook(
    path: str | Path,
    *,
    content_type: str | None = None,
) -> WorkbookReadResult:
    """Validate and parse a ДЗК (земельний) workbook into canonical rows."""

    return _read_workbook(
        path,
        schema=ZEM_SCHEMA,
        row_builder=_build_zem_record,
        content_type=content_type,
    )


def read_ner_workbook(
    path: str | Path,
    *,
    content_type: str | None = None,
) -> WorkbookReadResult:
    """Validate and parse a ДРРП (нерухомість) workbook into canonical rows."""

    return _read_workbook(
        path,
        schema=NER_SCHEMA,
        row_builder=_build_ner_record,
        content_type=content_type,
    )


def _read_workbook(
    path: str | Path,
    *,
    schema: InputSchema,
    row_builder: RowBuilder,
    content_type: str | None,
) -> WorkbookReadResult:
    p = Path(path)

    file_report = validate_input_file(p, filename=p.name, content_type=content_type)
    loaded: LoadedTable = load_table(
        p,
        content_type=content_type,
        detected_format=file_report.detected_format,
    )
    df = loaded.dataframe
    column_report = validate_required_columns(df.columns, schema)
    table_report = validate_table_patterns(df, schema)

    records: list[dict[str, Any]] = []
    for row in _iter_row_dicts(df):
        if _is_empty_row(row):
            continue
        built = row_builder(row)
        if built is not None:
            records.append(built)

    return WorkbookReadResult(
        records=records,
        file_report=file_report,
        column_report=column_report,
        table_report=table_report,
        source_format=loaded.source_format,
        extra_issues=list(loaded.issues),
    )


def _iter_row_dicts(df: pd.DataFrame) -> Iterator[dict[str, Any]]:
    columns = list(df.columns)
    for row in df.itertuples(index=False, name=None):
        yield {
            col: _clean_cell(row[i]) if i < len(row) else None
            for i, col in enumerate(columns)
        }


def _clean_cell(value: Any) -> Any:
    """Normalise empty pandas values to ``None``.

    pandas returns ``float('nan')`` for blank numeric cells and ``pd.NaT`` for
    empty date cells; the downstream ``normalize.*`` helpers only guard
    against ``None``/``""``, so we collapse everything empty-looking back to
    ``None`` here to match the previous openpyxl-based reader.
    """

    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _is_empty_row(row: dict[str, Any]) -> bool:
    for value in row.values():
        if value is None:
            continue
        if isinstance(value, float) and pd.isna(value):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return False
    return True


def _cell_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _build_zem_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    cad = normalize_cadastral(_cell_text(raw.get("Кадастровий номер")))
    if not cad:
        return None
    code, label = split_intended_use(_cell_text(raw.get("Цільове призначення")))
    return {
        "cadastral_no": cad,
        "koatuu": normalize_koatuu(_cell_text(raw.get("koatuu"))),
        "ownership_form": (
            (_cell_text(raw.get("Форма власності")) or "").lower() or None
        ),
        "intended_use_code": code,
        "intended_use_label": label,
        "location_admin": _cell_text(raw.get("Місцерозташування")),
        "agri_use_kind": _cell_text(raw.get("Вид с/г угідь")),
        "area_m2": ga_to_m2(raw.get("Площа, га")),
        "valuation_kop": valuation_to_kop(raw.get("Усереднена нормативно грошова оцінка")),
        "owner_tax_id": normalize_tax_id(_cell_text(raw.get("ЄДРПОУ землекористувача"))),
        "owner_name_raw": _cell_text(raw.get("Землекористувач")),
        "share": parse_float(raw.get("Частка володіння"), default=1.0),
        "registered_at": excel_serial_to_date(raw.get("Дата державної реєстрації права власності")),
        "record_no": _cell_text(raw.get("Номер запису про право власності")),
        "registrar": _cell_text(
            raw.get("Орган, що здійснив державну реєстрацію права власності")
        ),
        "record_kind": _cell_text(raw.get("Тип")),
        "record_subkind": _cell_text(raw.get("Підтип")),
    }


def _build_ner_record(raw: dict[str, Any]) -> dict[str, Any] | None:
    tax_id = normalize_tax_id(_cell_text(raw.get("Податковий номер ПП")))
    if not tax_id:
        return None
    object_raw = _cell_text(raw.get("Тип об'єкта"))
    address_raw = _cell_text(raw.get("Адреса об'єкта"))
    joint_val = raw.get("Вид спіль ної власності") or raw.get("Вид спільної власності")
    joint_norm = _cell_text(joint_val)
    return {
        "owner_tax_id": tax_id,
        "owner_name_raw": _cell_text(raw.get("Назва платника")),
        "object_type_raw": object_raw,
        "object_type_norm": normalize_object_type(object_raw),
        "address_raw": address_raw,
        "address_norm": normalize_address(address_raw),
        "area_m2": parse_float(raw.get("Загальна площа"), default=0.0),
        "registered_at": excel_serial_to_date(raw.get("Дата держ. реєстр. права власн")),
        "terminated_at": excel_serial_to_date(raw.get("Дата держ. реєстр. прип. права власн")),
        "joint_ownership_kind": joint_norm.lower() if joint_norm else None,
        "share": parse_float(raw.get("Розмір частки у праві спільної власності"), default=1.0),
    }


__all__ = [
    "WorkbookReadResult",
    "read_ner_workbook",
    "read_zem_workbook",
]
