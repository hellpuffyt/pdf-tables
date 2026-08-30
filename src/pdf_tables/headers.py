"""Heuristic header-row detection.

A header is guessed from three independent, weakly-predictive signals:

* **case** -- header cells are often ALL CAPS or Title Case while body rows
  are mixed / sentence case.
* **type mismatch** -- a column that is numeric in every body row but not in
  the first row strongly suggests that row is a label, not data.
* **font weight** -- when the caller can tell us the first row was rendered
  in a bold font (ruled-table extraction can, from character metadata) that
  is treated as strong evidence.

None of these signals is reliable alone, so we combine them into a
0..1 confidence score and only call it a header above a threshold. When the
table is too small to compare against, or the signals disagree, we honestly
report ``header_detected=False`` rather than guess.
"""

from __future__ import annotations

_NUMERIC_CHARS = set("0123456789.,-+%$()")


def _looks_numeric(cell: str) -> bool:
    text = cell.strip()
    if not text:
        return False
    stripped = text.strip("$%()").replace(",", "")
    if not stripped:
        return False
    try:
        float(stripped)
        return True
    except ValueError:
        return all(ch in _NUMERIC_CHARS or ch.isspace() for ch in text)


def _is_caps(cell: str) -> bool:
    letters = [c for c in cell if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def detect_header(
    rows: list[list[str]], *, first_row_bold: bool | None = None
) -> tuple[bool, float, list[str]]:
    """Return ``(header_detected, confidence, warnings)``.

    ``rows`` must include the candidate header as ``rows[0]``.
    """
    warnings: list[str] = []
    if len(rows) < 2:
        return False, 0.0, ["insufficient_rows_for_header"]

    header = rows[0]
    body = rows[1:]
    n_cols = len(header)
    if n_cols == 0:
        return False, 0.0, ["insufficient_rows_for_header"]

    signals: list[float] = []

    # Signal 1: case contrast between header and body.
    header_caps = sum(1 for c in header if _is_caps(c)) / n_cols
    body_cells = [c for r in body for c in r if c.strip()]
    body_caps = (
        sum(1 for c in body_cells if _is_caps(c)) / len(body_cells) if body_cells else 0.0
    )
    if header_caps == 1.0 and body_caps == 0.0:
        signals.append(0.45)
    elif header_caps > 0.5 and header_caps - body_caps > 0.25:
        signals.append(0.35)
    elif header_caps - body_caps > 0.5:
        signals.append(0.2)

    # Signal 2: type mismatch - column is numeric in body but not in header.
    mismatch_cols = 0
    numeric_body_cols = 0
    for col in range(n_cols):
        body_vals = [r[col] for r in body if col < len(r) and r[col].strip()]
        if len(body_vals) < max(1, len(body) // 2):
            continue
        if not all(_looks_numeric(v) for v in body_vals):
            continue
        numeric_body_cols += 1
        header_val = header[col] if col < len(header) else ""
        if header_val.strip() and not _looks_numeric(header_val):
            mismatch_cols += 1
    if numeric_body_cols:
        ratio = mismatch_cols / numeric_body_cols
        if ratio > 0:
            signals.append(min(0.5, 0.5 * ratio))

    # Signal 3: font weight, when supplied by the caller.
    # Bold is positive evidence when present; its absence is common even in
    # genuine headers, so it is not treated as evidence *against* one.
    if first_row_bold is True:
        signals.append(0.4)

    # Signal 4: header cells are non-empty and unique-ish, unlike a data row.
    non_empty = sum(1 for c in header if c.strip())
    if non_empty == n_cols:
        signals.append(0.1)

    confidence = max(0.0, min(1.0, sum(signals)))
    detected = confidence >= 0.5

    if not detected:
        warnings.append("header_uncertain")
    return detected, confidence, warnings
