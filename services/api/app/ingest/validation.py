"""Three-tier validation layer for ingested datasets.

Tiers:

1. **File-level** — extension, MIME hint, and magic-byte sniffing. Verifies the
   payload actually matches a supported tabular or document format before we
   spend time parsing it. Implemented in :func:`validate_input_file`.
2. **Column-level** — required headers must be present; extras are collected as
   informational noise. Implemented in :func:`validate_required_columns`.
3. **Data-level** — per-row regex checks for identifier columns (EDRPOU, tax
   id, cadastral number). Bad rows are surfaced as warnings with sample values;
   they never abort the import on their own. Implemented in
   :func:`validate_table_patterns`.

All reports are Pydantic models so the API layer can serialize them directly
into the response envelope. Hard failures raise :class:`ValidationErrorSummary`,
which is caught by the upload route and re-raised as the public
``ValidationError`` envelope type.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from app.ingest.schema import InputSchema

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".csv", ".xlsx", ".xls", ".pdf", ".docx", ".html", ".htm"}
)
TABULAR_EXTENSIONS: frozenset[str] = frozenset({".csv", ".xlsx", ".xls"})
UNSTRUCTURED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".html", ".htm"})

_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
_PDF_MAGIC = b"%PDF-"
_CONTENT_SAMPLE_BYTES = 8192

# Values treated as "missing identifier" and skipped by data-level regex checks.
_UNKNOWN_ID_VALUES: frozenset[str] = frozenset(
    {"", "unknown", "невідомо", "невідомий", "none", "nan", "null", "-", "—"}
)

IssueLevel = Literal["error", "warning", "info"]


class ValidationIssue(BaseModel):
    """Structured description of a single validation problem."""

    level: IssueLevel
    code: str
    message: str
    column: str | None = None
    row_count: int | None = None
    sample_values: list[str] = Field(default_factory=list)


class FileValidationReport(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    is_supported: bool
    detected_format: str
    file_extension: str | None = None
    mime_type: str | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)


class ColumnValidationReport(BaseModel):
    present_columns: list[str] = Field(default_factory=list)
    missing_columns: list[str] = Field(default_factory=list)
    unexpected_columns: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)


class TableValidationReport(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list)


class ValidationErrorSummary(ValueError):
    """Raised for hard validation failures that must abort the import."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "validation_failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


def validate_input_file(
    source: Any,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> FileValidationReport:
    """Validate that *source* is a supported file.

    *source* may be a :class:`pathlib.Path`, a string path, raw ``bytes``, or a
    binary file-like object (e.g. FastAPI ``UploadFile.file``). When possible,
    pass *filename* and *content_type* so the report captures both the declared
    and detected formats.
    """

    extension: str | None = None
    content_head: bytes = b""

    if isinstance(source, (str, Path)):
        path = Path(source)
        extension = path.suffix.lower() or None
        try:
            with path.open("rb") as fh:
                content_head = fh.read(_CONTENT_SAMPLE_BYTES)
        except OSError as exc:
            raise ValidationErrorSummary(
                f"Unable to read input file: {exc}",
                code="file_unreadable",
            ) from exc
    elif isinstance(source, (bytes, bytearray, memoryview)):
        content_head = bytes(source[:_CONTENT_SAMPLE_BYTES])
    elif hasattr(source, "read"):
        try:
            position = source.tell()
        except Exception:
            position = None
        raw = source.read(_CONTENT_SAMPLE_BYTES)
        content_head = raw.encode("utf-8", errors="ignore") if isinstance(raw, str) else raw
        if position is not None and hasattr(source, "seek"):
            try:
                source.seek(position)
            except Exception:
                pass
    else:
        raise ValidationErrorSummary(
            "Input must be a path, bytes buffer, or binary file-like object.",
            code="file_unreadable",
        )

    if filename and not extension:
        extension = Path(filename).suffix.lower() or None

    if extension and extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValidationErrorSummary(
            f"Unsupported file extension '{extension}'. Supported formats: {supported}.",
            code="unsupported_extension",
            details={"extension": extension, "supported": sorted(SUPPORTED_EXTENSIONS)},
        )

    detected_format = _detect_format(content_head, extension, content_type)

    issues: list[ValidationIssue] = []
    is_supported = detected_format in {"csv", "xlsx", "xls", "pdf", "docx", "html"}
    if not is_supported:
        raise ValidationErrorSummary(
            "Unsupported or unreadable file signature. Expected CSV, XLSX, XLS, PDF, DOCX, "
            "or HTML file.",
            code="unsupported_signature",
            details={"extension": extension, "mime_type": content_type},
        )

    if extension:
        normalized_ext = extension.lstrip(".")
        if normalized_ext == "htm":
            normalized_ext = "html"
        if normalized_ext != detected_format:
            issues.append(
                ValidationIssue(
                    level="warning",
                    code="file_extension_mismatch",
                    message=(
                        f"File extension '{extension}' does not match detected content "
                        f"'{detected_format}'."
                    ),
                )
            )

    return FileValidationReport(
        is_supported=is_supported,
        detected_format=detected_format,
        file_extension=extension,
        mime_type=content_type,
        issues=issues,
    )


def validate_required_columns(
    columns: Iterable[str],
    schema: InputSchema,
) -> ColumnValidationReport:
    """Ensure every :attr:`InputSchema.required_columns` value is present."""

    present_columns = [str(col) for col in columns]
    normalized = set(present_columns)
    required = list(schema.required_columns)
    optional = list(schema.optional_columns)

    missing_columns = [col for col in required if col not in normalized]
    expected = set(required) | set(optional)
    unexpected_columns = [col for col in present_columns if col not in expected]

    issues: list[ValidationIssue] = []
    if unexpected_columns:
        issues.append(
            ValidationIssue(
                level="info",
                code="unexpected_columns",
                message=(
                    f"Found {len(unexpected_columns)} extra column(s) not in the "
                    f"{schema.name} schema."
                ),
                row_count=len(unexpected_columns),
                sample_values=[str(c) for c in unexpected_columns[:5]],
            )
        )

    if missing_columns:
        message = "Missing required columns: " + ", ".join(missing_columns)
        issues.append(
            ValidationIssue(
                level="error",
                code="missing_required_columns",
                message=message,
                row_count=len(missing_columns),
                sample_values=list(missing_columns),
            )
        )
        raise ValidationErrorSummary(
            message,
            code="missing_required_columns",
            details={
                "schema": schema.name,
                "missing": missing_columns,
                "present": present_columns,
            },
        )

    return ColumnValidationReport(
        present_columns=present_columns,
        missing_columns=missing_columns,
        unexpected_columns=unexpected_columns,
        issues=issues,
    )


def validate_table_patterns(df: pd.DataFrame, schema: InputSchema) -> TableValidationReport:
    """Run per-column regex checks; warnings only, never raises."""

    issues: list[ValidationIssue] = []

    if schema.owner_id_column and schema.owner_id_pattern and schema.owner_id_column in df.columns:
        issues.extend(
            _collect_regex_issues(
                df=df,
                column=schema.owner_id_column,
                pattern=schema.owner_id_pattern,
                issue_code="owner_id_regex_mismatch",
                message_prefix="Owner identifier does not match expected pattern",
                ignore_values=_UNKNOWN_ID_VALUES,
            )
        )

    if (
        schema.cadastral_column
        and schema.cadastral_pattern
        and schema.cadastral_column in df.columns
    ):
        issues.extend(
            _collect_regex_issues(
                df=df,
                column=schema.cadastral_column,
                pattern=schema.cadastral_pattern,
                issue_code="cadastral_number_regex_mismatch",
                message_prefix="Cadastral number does not match expected pattern",
                ignore_values=_UNKNOWN_ID_VALUES,
            )
        )

    return TableValidationReport(issues=issues)


def issues_to_messages(issues: Iterable[ValidationIssue]) -> list[str]:
    """Flatten issues into short ``[code] message (Samples: ...)`` lines."""

    messages: list[str] = []
    for issue in issues:
        suffix = ""
        if issue.sample_values:
            suffix = f" Samples: {', '.join(issue.sample_values)}"
        messages.append(f"[{issue.code}] {issue.message}{suffix}")
    return messages


def _collect_regex_issues(
    df: pd.DataFrame,
    *,
    column: str,
    pattern: str,
    issue_code: str,
    message_prefix: str,
    ignore_values: frozenset[str] | set[str],
) -> list[ValidationIssue]:
    ignore_norm = {str(v).strip().lower() for v in ignore_values}

    raw = df[column].fillna("").astype(str).str.strip()
    normalized = raw.str.lower()
    allowed_mask = normalized.isin(ignore_norm) | normalized.eq("")

    invalid_mask = ~allowed_mask & ~raw.str.fullmatch(pattern, na=False)
    invalid_count = int(invalid_mask.sum())
    if invalid_count == 0:
        return []

    samples = [str(v) for v in raw.loc[invalid_mask].head(5).tolist()]
    return [
        ValidationIssue(
            level="warning",
            code=issue_code,
            column=column,
            row_count=invalid_count,
            message=(
                f"{message_prefix} in {invalid_count} row(s) for column '{column}'."
            ),
            sample_values=samples,
        )
    ]


def _detect_format(
    content_head: bytes,
    extension: str | None,
    content_type: str | None,
) -> str:
    if content_head.startswith(_PDF_MAGIC):
        return "pdf"
    if content_head.startswith(_OLE_MAGIC):
        return "xls"
    if content_head.startswith(_ZIP_MAGIC):
        # Both .xlsx and .docx are ZIP containers; peek at member names to
        # disambiguate. Fall back to extension / MIME if we can't.
        zip_kind = _sniff_zip_container(content_head)
        if zip_kind:
            return zip_kind
        if extension == ".docx":
            return "docx"
        if extension in (".xlsx",):
            return "xlsx"
        if content_type and "wordprocessing" in content_type:
            return "docx"
        if content_type and "spreadsheet" in content_type:
            return "xlsx"
        return "xlsx"

    if _looks_like_html(content_head):
        return "html"
    if _looks_like_csv(content_head):
        return "csv"

    if extension in {".xlsx", ".xls", ".csv", ".pdf", ".docx", ".html", ".htm"}:
        return "html" if extension in {".html", ".htm"} else extension.lstrip(".")
    if content_type:
        ct = content_type.lower()
        if "pdf" in ct:
            return "pdf"
        if "csv" in ct or "text/plain" in ct:
            return "csv"
        if "html" in ct:
            return "html"
        if "wordprocessing" in ct:
            return "docx"
        if "spreadsheet" in ct or "excel" in ct:
            return "xlsx"
    return "unknown"


def _sniff_zip_container(head: bytes) -> str | None:
    """Cheap ZIP member probe without unpacking the archive.

    openpyxl / python-docx containers expose their format via the prefix of the
    first few member names, which appears inside the local file headers.
    """

    try:
        import zipfile

        with zipfile.ZipFile(BytesIO(head + b"\x00" * 0)) as _:  # pragma: no cover - fast path
            pass
    except Exception:
        # Fall through to substring scan — ``head`` often contains enough of
        # the central directory names to classify without a full open.
        pass

    if b"word/" in head:
        return "docx"
    if b"xl/" in head or b"xl/workbook" in head:
        return "xlsx"
    return None


def _looks_like_html(head: bytes) -> bool:
    try:
        text = head.decode("utf-8", errors="ignore").lstrip().lower()
    except Exception:
        return False
    return text.startswith("<!doctype html") or text.startswith("<html") or "<table" in text[:2048]


_CSV_SEPARATOR_RE = re.compile(r"[;,\t]")


def _looks_like_csv(head: bytes) -> bool:
    if not head:
        return False
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            text = head.decode(encoding)
            break
        except UnicodeDecodeError:
            text = ""
    if not text:
        return False
    if "\x00" in text:
        return False
    has_separator = bool(_CSV_SEPARATOR_RE.search(text))
    has_newline = "\n" in text or "\r" in text
    return has_separator and has_newline


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "TABULAR_EXTENSIONS",
    "UNSTRUCTURED_EXTENSIONS",
    "ColumnValidationReport",
    "FileValidationReport",
    "TableValidationReport",
    "ValidationErrorSummary",
    "ValidationIssue",
    "issues_to_messages",
    "validate_input_file",
    "validate_required_columns",
    "validate_table_patterns",
]
