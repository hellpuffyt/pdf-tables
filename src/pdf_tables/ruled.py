"""Ruled-table detection: build a cell grid from ruling line intersections.

This delegates the line-intersection geometry to pdfplumber (which inspects
the page's vector ``lines``/``rects`` to find horizontal and vertical rules
and intersect them into a grid) and layers this project's own logic on top:
merged-cell detection, column-count-variance detection, header heuristics,
and confidence scoring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .headers import detect_header
from .models import TableResult
from .util import row_bold_ratio

if TYPE_CHECKING:
    from pdfplumber.page import Page
    from pdfplumber.table import Table as PlumberTable

RULED_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
}


def _clean_multiline(cell: str | None) -> str:
    if cell is None:
        return ""
    return " ".join(cell.split())


def extract_ruled_tables(page: Page, page_number: int) -> list[TableResult]:
    """Detect and extract all ruled tables on ``page``."""
    results: list[TableResult] = []
    try:
        raw_tables = page.find_tables(table_settings=RULED_TABLE_SETTINGS)
    except Exception:
        return results

    for idx, table in enumerate(raw_tables):
        result = _build_ruled_result(page, table, page_number, idx)
        if result is not None:
            results.append(result)
    return results


def _build_ruled_result(
    page: Page, table: PlumberTable, page_number: int, index: int
) -> TableResult | None:
    raw_rows = table.extract()
    if not raw_rows or not any(any((c or "").strip() for c in row) for row in raw_rows):
        return None

    rows = [[_clean_multiline(c) for c in row] for row in raw_rows]
    warnings: list[str] = []

    col_counts = {len(r) for r in rows}
    if len(col_counts) > 1:
        warnings.append("column_count_varies")

    n_cols = max(len(r) for r in rows)

    # Merged-cell detection: pdfplumber represents a spanned cell as `None`
    # in every grid position it absorbs, which is unambiguous evidence of a
    # merge (not a guess), so we flag it as an informational warning.
    merged_rows = []
    for r_idx, row in enumerate(table.rows):
        if any(c is None for c in row.cells):
            merged_rows.append(r_idx)
    if merged_rows:
        warnings.append(f"possible_merged_cell:rows={merged_rows}")

    # Wrapped text: pdfplumber already joins a wrapped cell's lines with
    # "\n" because the ruling box makes the cell boundary unambiguous, so
    # this is reported as informational, not as an uncertainty warning.
    wrapped_rows = [
        r_idx for r_idx, row in enumerate(raw_rows) if any("\n" in (c or "") for c in row)
    ]
    if wrapped_rows:
        warnings.append(f"wrapped_text_joined:rows={wrapped_rows}")

    bold = row_bold_ratio(page, table.rows[0].bbox) if table.rows else None
    header_detected, header_conf, header_warnings = detect_header(rows, first_row_bold=bold)
    warnings.extend(header_warnings)

    confidence = 1.0
    if "column_count_varies" in warnings:
        confidence -= 0.35
    if merged_rows:
        confidence -= 0.1
    if n_cols < 2 or len(rows) < 1:
        confidence -= 0.4
    confidence = max(0.0, min(1.0, confidence))

    return TableResult(
        page=page_number,
        index=index,
        strategy="ruled",
        bbox=(table.bbox[0], table.bbox[1], table.bbox[2], table.bbox[3]),
        rows=rows,
        header=rows[0] if header_detected and rows else None,
        header_detected=header_detected,
        header_confidence=header_conf,
        confidence=confidence,
        warnings=warnings,
    )
