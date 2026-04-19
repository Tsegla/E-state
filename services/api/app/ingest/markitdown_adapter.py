"""Load tabular inputs through a single interface.

For classic tabular formats (CSV/XLSX/XLS) we keep using pandas directly — it
is faster and preserves numeric types better than routing through a markdown
round-trip. For unstructured documents (PDF/DOCX/HTML) we delegate to the
``microsoft/markitdown`` library, which normalises the content to GitHub-
flavoured Markdown. We then parse the largest HTML/Markdown table out of that
Markdown and surface it as a :class:`pandas.DataFrame` with the same header
row contract as the Excel loader expects.

``markitdown`` is imported lazily so the API can still boot (and all the
non-PDF paths keep working) when the optional extra is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from app.ingest.validation import (
    TABULAR_EXTENSIONS,
    UNSTRUCTURED_EXTENSIONS,
    ValidationErrorSummary,
    ValidationIssue,
)


@dataclass(slots=True)
class LoadedTable:
    dataframe: pd.DataFrame
    source_format: str
    issues: list[ValidationIssue] = field(default_factory=list)


def load_table(
    path: str | Path,
    *,
    content_type: str | None = None,
    detected_format: str | None = None,
) -> LoadedTable:
    """Return the first usable table from *path* as a DataFrame.

    The caller is expected to have already run :func:`validate_input_file` so
    ``detected_format`` is known. We still accept a missing value and fall back
    to the extension for robustness.
    """

    p = Path(path)
    extension = p.suffix.lower()
    fmt = (detected_format or "").lower() or extension.lstrip(".")

    if extension in TABULAR_EXTENSIONS or fmt in {"csv", "xlsx", "xls"}:
        return _load_tabular(p, fmt=fmt)

    if extension in UNSTRUCTURED_EXTENSIONS or fmt in {"pdf", "docx", "html"}:
        return _load_via_markitdown(p, fmt=fmt, content_type=content_type)

    raise ValidationErrorSummary(
        f"Unsupported file format for '{p.name}'. Cannot extract tabular content.",
        code="unsupported_format",
        details={"extension": extension, "detected_format": fmt},
    )


def _load_tabular(path: Path, *, fmt: str) -> LoadedTable:
    extension = path.suffix.lower()
    if extension in {".xlsx", ".xls"} or fmt in {"xlsx", "xls"}:
        try:
            df = pd.read_excel(path, dtype=object)
        except Exception as exc:
            raise ValidationErrorSummary(
                f"Could not parse Excel file '{path.name}': {exc}",
                code="excel_parse_failed",
            ) from exc
        return LoadedTable(
            dataframe=_normalize_columns(df),
            source_format="xls" if extension == ".xls" else "xlsx",
        )

    # CSV path with tolerant separator / encoding fallback.
    last_error: Exception | None = None
    candidates: list[pd.DataFrame] = []
    for sep, kwargs in (
        (";", {}),
        (",", {}),
        (None, {"engine": "python"}),
    ):
        for encoding in ("utf-8-sig", "cp1251"):
            try:
                df = pd.read_csv(path, sep=sep, encoding=encoding, dtype=object, **kwargs)
                candidates.append(df)
            except Exception as exc:  # pragma: no cover - fallback chain
                last_error = exc

    if not candidates:
        raise ValidationErrorSummary(
            f"Unable to read CSV file '{path.name}': {last_error}",
            code="csv_parse_failed",
        )

    # Pick the interpretation with the most columns and the fewest empty rows.
    best = max(
        candidates,
        key=lambda df: (len(df.columns), -int(df.isna().all(axis=1).sum())),
    )
    return LoadedTable(dataframe=_normalize_columns(best), source_format="csv")


def _load_via_markitdown(
    path: Path,
    *,
    fmt: str,
    content_type: str | None,
) -> LoadedTable:
    try:
        from markitdown import MarkItDown  # type: ignore
    except ImportError as exc:
        raise ValidationErrorSummary(
            "This file format requires the 'markitdown' extra. Install the API "
            "service with `uv sync` (or `pip install 'markitdown[all]'`) to "
            "enable PDF/DOCX/HTML ingestion.",
            code="markitdown_not_installed",
        ) from exc

    try:
        converter = MarkItDown(enable_plugins=False)
        result = converter.convert(str(path))
    except Exception as exc:
        raise ValidationErrorSummary(
            f"markitdown could not convert '{path.name}': {exc}",
            code="markitdown_conversion_failed",
        ) from exc

    markdown_text: str = getattr(result, "text_content", "") or ""
    if not markdown_text.strip():
        raise ValidationErrorSummary(
            f"markitdown produced no text for '{path.name}'.",
            code="markitdown_empty_output",
        )

    df = _extract_table_from_markdown(markdown_text)
    if df is None or df.empty or len(df.columns) == 0:
        raise ValidationErrorSummary(
            f"No tabular content could be extracted from '{path.name}'.",
            code="no_table_detected",
        )

    resolved_fmt = fmt or (path.suffix.lower().lstrip(".") if path.suffix else "unknown")
    return LoadedTable(
        dataframe=_normalize_columns(df),
        source_format=resolved_fmt,
        issues=[
            ValidationIssue(
                level="info",
                code="markitdown_used",
                message=(
                    f"Content of '{path.name}' was converted to Markdown via "
                    "microsoft/markitdown before table extraction."
                ),
            )
        ],
    )


def _extract_table_from_markdown(markdown_text: str) -> pd.DataFrame | None:
    """Pick the largest table out of the Markdown document, if any."""

    # Try HTML first — markitdown often emits ``<table>`` for PDFs/DOCX and
    # pandas handles HTML tables out of the box.
    try:
        html_tables = pd.read_html(StringIO(markdown_text))
    except (ValueError, ImportError):
        html_tables = []

    candidates: list[pd.DataFrame] = list(html_tables)

    gfm = _parse_gfm_tables(markdown_text)
    candidates.extend(gfm)

    if not candidates:
        return None

    best = max(
        candidates,
        key=lambda df: (len(df.columns), len(df)),
    )
    return best


def _parse_gfm_tables(text: str) -> list[pd.DataFrame]:
    """Best-effort GFM pipe-table parser.

    We do not try to handle every exotic markdown variant; ``markitdown`` emits
    well-formed pipe tables with a ``| --- |`` separator row, which is all we
    need to support here.
    """

    tables: list[pd.DataFrame] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        header = lines[i].strip()
        separator = lines[i + 1].strip()
        if _is_pipe_row(header) and _is_separator_row(separator):
            header_cells = _split_pipe_row(header)
            rows: list[list[str]] = []
            j = i + 2
            while j < len(lines):
                row = lines[j].strip()
                if not _is_pipe_row(row):
                    break
                rows.append(_split_pipe_row(row))
                j += 1
            normalized_rows = [
                row + [""] * (len(header_cells) - len(row)) if len(row) < len(header_cells) else row[: len(header_cells)]
                for row in rows
            ]
            try:
                tables.append(pd.DataFrame(normalized_rows, columns=header_cells))
            except Exception:  # pragma: no cover - defensive
                pass
            i = j
        else:
            i += 1
    return tables


def _is_pipe_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _is_separator_row(line: str) -> bool:
    if not _is_pipe_row(line):
        return False
    cells = _split_pipe_row(line)
    return bool(cells) and all(set(c.strip()) <= set("-: ") and "-" in c for c in cells)


def _split_pipe_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from header names; leave cell content untouched."""

    normalized: list[Any] = []
    for col in df.columns:
        if col is None:
            normalized.append("")
            continue
        normalized.append(str(col).strip())
    df = df.copy()
    df.columns = normalized
    return df


__all__ = ["LoadedTable", "load_table"]
