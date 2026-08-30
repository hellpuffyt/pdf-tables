from __future__ import annotations

import csv
import json
from pathlib import Path

from pdf_tables.models import TableResult
from pdf_tables.output import table_csv_filename, write_csv, write_outputs


def _make_table(page: int = 1, index: int = 0) -> TableResult:
    return TableResult(
        page=page,
        index=index,
        strategy="ruled",
        bbox=(0.0, 0.0, 100.0, 50.0),
        rows=[["Name", "Role"], ["Alice", "Engineer"]],
        header=["Name", "Role"],
        header_detected=True,
        header_confidence=0.9,
        confidence=1.0,
        warnings=[],
    )


def test_csv_filename_format() -> None:
    table = _make_table(page=2, index=3)
    assert table_csv_filename(table) == "table_p2_3.csv"


def test_write_csv_content(tmp_path: Path) -> None:
    table = _make_table()
    path = write_csv(table, tmp_path)
    with path.open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows == [["Name", "Role"], ["Alice", "Engineer"]]


def test_write_outputs_creates_manifest(tmp_path: Path) -> None:
    tables = [_make_table()]
    manifest_path = write_outputs(tables, tmp_path, source="in.pdf")
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["n_tables"] == 1
    assert manifest["source"] == "in.pdf"
    assert manifest["tables"][0]["csv"] == "table_p1_0.csv"


def test_write_outputs_creates_out_dir(tmp_path: Path) -> None:
    out_dir = tmp_path / "nested" / "dir"
    write_outputs([_make_table()], out_dir, source="in.pdf")
    assert out_dir.exists()
    assert (out_dir / "table_p1_0.csv").exists()


def test_write_outputs_empty_list(tmp_path: Path) -> None:
    manifest_path = write_outputs([], tmp_path, source="in.pdf")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["n_tables"] == 0
    assert manifest["tables"] == []


def test_manifest_entry_contains_warnings_and_confidence(tmp_path: Path) -> None:
    table = _make_table()
    table.warnings = ["column_count_varies"]
    table.confidence = 0.6
    write_outputs([table], tmp_path, source="in.pdf")
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["tables"][0]
    assert entry["warnings"] == ["column_count_varies"]
    assert entry["confidence"] == 0.6


def test_multiple_tables_get_distinct_csv_files(tmp_path: Path) -> None:
    tables = [_make_table(page=1, index=0), _make_table(page=1, index=1)]
    write_outputs(tables, tmp_path, source="in.pdf")
    assert (tmp_path / "table_p1_0.csv").exists()
    assert (tmp_path / "table_p1_1.csv").exists()
