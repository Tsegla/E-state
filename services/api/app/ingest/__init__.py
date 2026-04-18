"""Read raw ДЗК/ДРРП files and normalize into canonical rows."""

from app.ingest.excel import read_ner_workbook, read_zem_workbook
from app.ingest.normalize import (
    excel_serial_to_date,
    ga_to_m2,
    normalize_name,
    normalize_object_type,
    normalize_tax_id,
    split_intended_use,
)
from app.ingest.service import IngestResult, ingest_dataset

__all__ = [
    "IngestResult",
    "excel_serial_to_date",
    "ga_to_m2",
    "ingest_dataset",
    "normalize_name",
    "normalize_object_type",
    "normalize_tax_id",
    "read_ner_workbook",
    "read_zem_workbook",
    "split_intended_use",
]
