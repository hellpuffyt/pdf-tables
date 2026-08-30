"""CSV and JSON manifest writers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import TableResult


def table_csv_filename(table: TableResult) -> str:
    return f"table_p{table.page}_{table.index}.csv"


def write_csv(table: TableResult, out_dir: Path) -> Path:
    path = out_dir / table_csv_filename(table)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in table.rows:
            writer.writerow(row)
    return path


def write_outputs(tables: list[TableResult], out_dir: Path, source: str) -> Path:
    """Write one CSV per table plus a manifest.json; return the manifest path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for table in tables:
        write_csv(table, out_dir)
        entry = table.to_manifest_entry()
        entry["csv"] = table_csv_filename(table)
        manifest_entries.append(entry)

    manifest = {"source": source, "n_tables": len(tables), "tables": manifest_entries}
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path
