"""Tests for the three-tier ingest validation layer.

Covers:
- file-level sniffing (extension + magic bytes)
- column-level required/optional detection
- data-level regex warnings for EDRPOU + cadastral identifiers
- the markitdown_adapter table-extraction helpers (on deterministic markdown)
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

from app.ingest.markitdown_adapter import _extract_table_from_markdown, load_table
from app.ingest.schema import NER_SCHEMA, ZEM_SCHEMA, InputSchema
from app.ingest.validation import (
    ValidationErrorSummary,
    validate_input_file,
    validate_required_columns,
    validate_table_patterns,
)

ZEM_HEADER_ROW = [
    "Кадастровий номер",
    "koatuu",
    "Форма власності",
    "Цільове призначення",
    "Місцерозташування",
    "Вид с/г угідь",
    "Площа, га",
    "Усереднена нормативно грошова оцінка",
    "ЄДРПОУ землекористувача",
    "Землекористувач",
    "Частка володіння",
    "Дата державної реєстрації права власності",
    "Номер запису про право власності",
    "Орган, що здійснив державну реєстрацію права власності",
    "Тип",
    "Підтип",
]


def _write_xlsx(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(str(path))


def test_validate_input_file_accepts_real_xlsx(tmp_path: Path) -> None:
    path = tmp_path / "sample.xlsx"
    _write_xlsx(path, ZEM_HEADER_ROW, [])

    report = validate_input_file(path, filename=path.name)

    assert report.is_supported
    assert report.detected_format == "xlsx"
    assert report.file_extension == ".xlsx"
    assert not [i for i in report.issues if i.level == "error"]


def test_validate_input_file_accepts_pdf_magic(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF-1.4\n%fake pdf body\n")

    report = validate_input_file(path, filename=path.name, content_type="application/pdf")

    assert report.detected_format == "pdf"
    assert report.is_supported


def test_validate_input_file_rejects_renamed_txt(tmp_path: Path) -> None:
    path = tmp_path / "sneaky.txt"
    path.write_text("hello world", encoding="utf-8")

    with pytest.raises(ValidationErrorSummary) as excinfo:
        validate_input_file(path, filename=path.name)

    assert excinfo.value.code == "unsupported_extension"


def test_validate_input_file_warns_on_extension_mismatch(tmp_path: Path) -> None:
    # CSV body stored with .xlsx extension -> magic bytes say csv, extension says xlsx.
    path = tmp_path / "masquerade.xlsx"
    path.write_text("a;b;c\n1;2;3\n", encoding="utf-8")

    report = validate_input_file(path, filename=path.name)

    assert report.detected_format == "csv"
    codes = {issue.code for issue in report.issues}
    assert "file_extension_mismatch" in codes


def test_validate_input_file_accepts_bytes_buffer() -> None:
    buf = BytesIO(b"%PDF-1.7\n%..\n")

    report = validate_input_file(buf, filename="inline.pdf", content_type="application/pdf")

    assert report.detected_format == "pdf"


def test_validate_required_columns_passes_for_full_header() -> None:
    report = validate_required_columns(ZEM_HEADER_ROW, ZEM_SCHEMA)

    assert not report.missing_columns
    assert not [i for i in report.issues if i.level == "error"]


def test_validate_required_columns_raises_when_missing() -> None:
    trimmed = [c for c in ZEM_HEADER_ROW if c != "ЄДРПОУ землекористувача"]

    with pytest.raises(ValidationErrorSummary) as excinfo:
        validate_required_columns(trimmed, ZEM_SCHEMA)

    assert excinfo.value.code == "missing_required_columns"
    assert "ЄДРПОУ землекористувача" in excinfo.value.message


def test_validate_required_columns_flags_unexpected_as_info() -> None:
    columns = [*ZEM_HEADER_ROW, "__extra_column__"]

    report = validate_required_columns(columns, ZEM_SCHEMA)

    assert "__extra_column__" in report.unexpected_columns
    codes = {issue.code for issue in report.issues}
    assert "unexpected_columns" in codes


def test_validate_table_patterns_detects_bad_identifiers() -> None:
    df = pd.DataFrame(
        {
            "ЄДРПОУ землекористувача": ["12345678", "12345", "", "невідомо", "BADID"],
            "Кадастровий номер": [
                "4610136300:01:001:0001",
                "4610136300:01:001:0002",
                "",
                "невідомо",
                "BAD-CAD",
            ],
        }
    )

    report = validate_table_patterns(df, ZEM_SCHEMA)

    codes = {issue.code for issue in report.issues}
    assert "owner_id_regex_mismatch" in codes
    assert "cadastral_number_regex_mismatch" in codes

    owner_issue = next(i for i in report.issues if i.code == "owner_id_regex_mismatch")
    assert owner_issue.row_count == 2  # "12345" and "BADID"
    assert set(owner_issue.sample_values) == {"12345", "BADID"}


def test_validate_table_patterns_ner_accepts_10_digit_tax_id() -> None:
    df = pd.DataFrame({"Податковий номер ПП": ["1234567890", "12345678", "abc"]})

    report = validate_table_patterns(df, NER_SCHEMA)

    codes = {issue.code: issue for issue in report.issues}
    assert "owner_id_regex_mismatch" in codes
    assert codes["owner_id_regex_mismatch"].row_count == 1
    assert codes["owner_id_regex_mismatch"].sample_values == ["abc"]


def test_validate_table_patterns_empty_report_when_all_valid() -> None:
    df = pd.DataFrame(
        {
            "ЄДРПОУ землекористувача": ["12345678", "87654321"],
            "Кадастровий номер": ["4610136300:01:001:0001", "4610136300:01:001:0002"],
        }
    )

    report = validate_table_patterns(df, ZEM_SCHEMA)
    assert report.issues == []


def test_load_table_reads_xlsx(tmp_path: Path) -> None:
    path = tmp_path / "book.xlsx"
    _write_xlsx(path, ["a", "b"], [[1, 2], [3, 4]])

    loaded = load_table(path, detected_format="xlsx")

    assert loaded.source_format == "xlsx"
    assert list(loaded.dataframe.columns) == ["a", "b"]
    assert len(loaded.dataframe) == 2


def test_load_table_reads_csv(tmp_path: Path) -> None:
    path = tmp_path / "tab.csv"
    path.write_text("id;name\n1;alice\n2;bob\n", encoding="utf-8")

    loaded = load_table(path, detected_format="csv")

    assert loaded.source_format == "csv"
    assert list(loaded.dataframe.columns) == ["id", "name"]
    assert loaded.dataframe.iloc[1]["name"] == "bob"


def test_extract_table_from_markdown_gfm_pipe_tables() -> None:
    markdown_text = (
        "# Report\n\n"
        "Some prose here.\n\n"
        "| ЄДРПОУ землекористувача | Площа, га |\n"
        "| --- | --- |\n"
        "| 12345678 | 10.5 |\n"
        "| 87654321 | 3.25 |\n\n"
        "Trailing text.\n"
    )

    df = _extract_table_from_markdown(markdown_text)

    assert df is not None
    assert list(df.columns) == ["ЄДРПОУ землекористувача", "Площа, га"]
    assert df.iloc[0]["ЄДРПОУ землекористувача"] == "12345678"
    assert df.iloc[1]["Площа, га"] == "3.25"


def test_extract_table_from_markdown_html_table() -> None:
    html_text = (
        "<table>"
        "<tr><th>a</th><th>b</th></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</table>"
    )

    df = _extract_table_from_markdown(html_text)

    assert df is not None
    assert list(df.columns) == ["a", "b"]
    assert len(df) == 1


def test_extract_table_from_markdown_returns_none_without_tables() -> None:
    assert _extract_table_from_markdown("Just a paragraph with no tables.\n") is None


def test_read_zem_workbook_end_to_end(tmp_path: Path) -> None:
    from app.ingest.excel import read_zem_workbook

    path = tmp_path / "zem.xlsx"
    _write_xlsx(
        path,
        ZEM_HEADER_ROW,
        [
            [
                "4610136300:01:001:0001",
                "4610136300",
                "приватна",
                "02.01 Для будівництва",
                "вул. Тестова 1",
                "",
                12.5,
                85000,
                "12345678",
                "ТОВ Тест",
                1.0,
                44562,
                "ABC-1",
                "Реєстр",
                "Тип",
                "Підтип",
            ],
            # Row with invalid EDRPOU -> should generate a warning, not abort.
            [
                "4610136300:01:001:0002",
                "4610136300",
                "приватна",
                "01 Для ведення товарного",
                "вул. Тестова 2",
                "",
                30.0,
                42000,
                "BAD",
                "ФОП Бад",
                1.0,
                44562,
                "ABC-2",
                "Реєстр",
                "Тип",
                "Підтип",
            ],
        ],
    )

    result = read_zem_workbook(path)

    assert result.file_report.detected_format == "xlsx"
    assert result.column_report.missing_columns == []
    regex_codes = {i.code for i in result.table_report.issues}
    assert "owner_id_regex_mismatch" in regex_codes
    assert len(result.records) == 2
    assert result.records[0]["cadastral_no"] == "4610136300:01:001:0001"


def test_read_zem_workbook_raises_on_missing_column(tmp_path: Path) -> None:
    from app.ingest.excel import read_zem_workbook

    path = tmp_path / "broken.xlsx"
    headers = [h for h in ZEM_HEADER_ROW if h != "ЄДРПОУ землекористувача"]
    _write_xlsx(path, headers, [])

    with pytest.raises(ValidationErrorSummary) as excinfo:
        read_zem_workbook(path)
    assert excinfo.value.code == "missing_required_columns"


def test_custom_schema_can_override_patterns() -> None:
    # The regex lives in schema.InputSchema, so callers can adjust it without
    # touching the validation code — this is the whole point of schema.py.
    relaxed = InputSchema(
        name="zem-relaxed",
        required_columns=ZEM_SCHEMA.required_columns,
        optional_columns=ZEM_SCHEMA.optional_columns,
        owner_id_column="ЄДРПОУ землекористувача",
        owner_id_pattern=r"^.+$",
        cadastral_column="Кадастровий номер",
        cadastral_pattern=r"^.+$",
    )
    df = pd.DataFrame(
        {
            "ЄДРПОУ землекористувача": ["anything", "here"],
            "Кадастровий номер": ["whatever", "works"],
        }
    )

    assert validate_table_patterns(df, relaxed).issues == []
