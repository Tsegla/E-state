"""Export every finding from the dev SQLite DB into CSV + XLSX for manual audit.

Usage:
    uv run python scripts/export_findings.py [--dataset-id <hex>]

If --dataset-id is omitted, the most recently uploaded dataset is exported.

Output:
    docs/audit/findings_<label>_<short_id>.xlsx       one row per finding, with person name + tax id (unmasked, local only)
    docs/audit/findings_<label>_<short_id>.csv        same data, UTF-8 CSV
    docs/audit/findings_by_type_<label>_<short_id>.csv counts per finding_type/severity
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path

try:
    from openpyxl import Workbook  # type: ignore
except ImportError:
    Workbook = None  # type: ignore

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "e_state_dev.db"
OUT = REPO / "docs" / "audit"

EXPLANATIONS = {
    "AREA_PORTFOLIO_DELTA": "Сумарна площа нерухомості у {ratio}× перевищує площу землі цієї особи",
    "LAND_NO_REAL_ESTATE": "Особа має {residential_parcels} житлових ділянок ({total_residential_m2} м²), але жодного житлового об'єкта у ДРРП",
    "REAL_ESTATE_NO_LAND": "Особа має активну нерухомість у ДРРП, але жодної земельної ділянки у ДЗК",
    "OWNER_NAME_MISMATCH": "Один і той самий РНОКПП, але різне прізвище у ДЗК vs ДРРП (similarity={similarity})",
    "TERMINATED_BUT_ACTIVE": "ДРРП запис з датою припинення, але досі враховується як активний",
    "TERMINATED_RIGHTS_MISMATCH": "Право власності на нерухомість припинено ({drrp_termination_date}), але особа залишається активним землекористувачем",
    "MISSING_OWNER": "Ділянка у ДЗК без РНОКПП власника",
    "DUPLICATE_REGISTRATION": "Той самий кадастровий номер з різними власниками",
}

LAND_CATEGORY_UA = {
    "agricultural": "Сільгосп",
    "residential": "Житлова",
    "commercial": "Комерційна",
    "industrial": "Промислова",
}

OBJECT_CATEGORY_UA = {
    "residential": "житловим",
    "commercial": "комерційним",
    "industrial": "промисловим",
    "agricultural": "сільгосп",
}


def explain(finding_type: str, metrics: dict) -> str:
    if finding_type == "USE_VS_OBJECT_MISMATCH":
        land = [LAND_CATEGORY_UA.get(c, c) for c in metrics.get("land_categories", [])]
        obj = [OBJECT_CATEGORY_UA.get(c, c) for c in metrics.get("object_categories", [])]
        land_label = "/".join(land) or "Невідома"
        obj_label = "/".join(obj) or "невідомим"
        return f"{land_label}-ділянка з {obj_label} об'єктом на ній"
    template = EXPLANATIONS.get(finding_type, finding_type)
    try:
        return template.format(**metrics)
    except (KeyError, IndexError):
        return template


def pick_dataset(conn: sqlite3.Connection, dataset_id: str | None) -> tuple[str, str]:
    cur = conn.cursor()
    if dataset_id:
        row = cur.execute(
            "SELECT id, label FROM dataset WHERE id = ?", (dataset_id,)
        ).fetchone()
        if not row:
            raise SystemExit(f"Dataset {dataset_id} not found")
        return row[0], row[1]
    row = cur.execute(
        "SELECT id, label FROM dataset ORDER BY uploaded_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        raise SystemExit("No datasets found in DB")
    return row[0], row[1]


def load_findings(conn: sqlite3.Connection, dataset_id: str) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT f.id, f.person_tax_id, f.finding_type, f.severity, f.status,
               f.computed_metrics, datetime(f.detected_at, 'localtime'),
               p.full_name_raw
        FROM finding f
        LEFT JOIN person p ON p.tax_id = f.person_tax_id
        WHERE f.dataset_id = ?
        ORDER BY
            CASE f.severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
            f.finding_type,
            f.id
        """,
        (dataset_id,),
    )
    rows = []
    for r in cur.fetchall():
        metrics = json.loads(r[5]) if r[5] else {}
        rows.append(
            {
                "finding_id": r[0],
                "tax_id": r[1],
                "owner_name": r[7] or "",
                "finding_type": r[2],
                "severity": r[3],
                "status": r[4],
                "detected_at": r[6],
                "metrics_json": json.dumps(metrics, ensure_ascii=False),
                "explanation": explain(r[2], metrics),
                "land_m2": metrics.get("zem_m2") or metrics.get("total_residential_m2") or metrics.get("area_m2"),
                "re_m2": metrics.get("ner_m2") or metrics.get("total_re_m2"),
                "ratio": metrics.get("ratio"),
                "similarity": metrics.get("similarity"),
            }
        )
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "finding_id",
        "tax_id",
        "owner_name",
        "finding_type",
        "severity",
        "status",
        "detected_at",
        "land_m2",
        "re_m2",
        "ratio",
        "similarity",
        "explanation",
        "metrics_json",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def write_xlsx(rows: list[dict], path: Path) -> None:
    if Workbook is None:
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "findings"
    headers = [
        "Тип",
        "Severity",
        "РНОКПП",
        "ПІБ власника",
        "Площа землі (м²)",
        "Площа нерухомості (м²)",
        "Ratio",
        "Similarity",
        "Пояснення",
        "Metrics JSON",
        "ID",
    ]
    ws.append(headers)
    for r in rows:
        ws.append(
            [
                r["finding_type"],
                r["severity"],
                r["tax_id"],
                r["owner_name"],
                r["land_m2"],
                r["re_m2"],
                r["ratio"],
                r["similarity"],
                r["explanation"],
                r["metrics_json"],
                r["finding_id"],
            ]
        )
    for col_idx, width in enumerate(
        [24, 10, 14, 32, 16, 20, 8, 11, 60, 50, 34], start=1
    ):
        ws.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else "A" + chr(64 + col_idx - 26)].width = width
    ws.freeze_panes = "A2"
    wb.save(path)


def write_summary(conn: sqlite3.Connection, dataset_id: str, path: Path) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT finding_type, severity, COUNT(*)
        FROM finding
        WHERE dataset_id = ?
        GROUP BY finding_type, severity
        ORDER BY severity, COUNT(*) DESC
        """,
        (dataset_id,),
    )
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["finding_type", "severity", "count"])
        for row in cur.fetchall():
            w.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-id", default=None)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB)
    dataset_id, label = pick_dataset(conn, args.dataset_id)
    short = dataset_id[:8]
    slug = "".join(c if c.isalnum() else "_" for c in label).strip("_") or "dataset"

    rows = load_findings(conn, dataset_id)
    print(f"Dataset: {label} ({dataset_id})")
    print(f"Findings: {len(rows)}")

    csv_path = OUT / f"findings_{slug}_{short}.csv"
    xlsx_path = OUT / f"findings_{slug}_{short}.xlsx"
    summary_path = OUT / f"findings_by_type_{slug}_{short}.csv"

    write_csv(rows, csv_path)
    write_xlsx(rows, xlsx_path)
    write_summary(conn, dataset_id, summary_path)

    print(f"Wrote {csv_path}")
    if Workbook is not None:
        print(f"Wrote {xlsx_path}")
    else:
        print("(openpyxl not installed — skipped .xlsx)")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
