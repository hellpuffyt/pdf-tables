"""Whitespace-aligned table detection.

No ruling lines to lean on, so this clusters word positions directly:

1. Group words into text rows by their vertical position.
2. Build a histogram of horizontal space occupied by *any* word across a
   run of rows; gaps in that histogram wider than a threshold become column
   band boundaries (this is the "x-coordinate histogram gap" approach).
3. Assign each word to the band its left edge falls in, and join same-band,
   same-row words into a cell.
4. Merge tightly-spaced, mostly-empty follow-on rows into the row above as
   wrapped-text continuations.

This is deliberately conservative: a page (or region) is only reported as a
table when there are at least two rows and at least two stable column
bands. Everything else -- prose, a single label, a caption -- is left alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .headers import detect_header
from .models import TableResult
from .util import median, row_bold_ratio

if TYPE_CHECKING:
    from pdfplumber.page import Page

BBox = tuple[float, float, float, float]


@dataclass
class _Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float


@dataclass
class _Row:
    words: list[_Word]

    @property
    def top(self) -> float:
        return min(w.top for w in self.words)

    @property
    def bottom(self) -> float:
        return max(w.bottom for w in self.words)


def _cluster_rows(words: list[_Word], y_tolerance: float = 3.0) -> list[_Row]:
    words_sorted = sorted(words, key=lambda w: (w.top, w.x0))
    rows: list[_Row] = []
    for w in words_sorted:
        placed = False
        for row in rows[-3:] if len(rows) > 3 else rows:
            if abs(row.top - w.top) <= y_tolerance:
                row.words.append(w)
                placed = True
                break
        if not placed:
            rows.append(_Row(words=[w]))
    for row in rows:
        row.words.sort(key=lambda w: w.x0)
    rows.sort(key=lambda r: r.top)
    return rows


def _row_internal_gaps(row: _Row) -> list[float]:
    gaps = []
    for a, b in zip(row.words, row.words[1:], strict=False):
        gaps.append(b.x0 - a.x1)
    return gaps


def _gap_threshold(all_words: list[_Word]) -> float:
    widths = [w.x1 - w.x0 for w in all_words if w.text.strip()]
    lengths = [max(1, len(w.text.strip())) for w in all_words if w.text.strip()]
    if widths and lengths:
        avg_char_width = median([w / n for w, n in zip(widths, lengths, strict=True)])
    else:
        avg_char_width = 5.0
    return max(8.0, avg_char_width * 2.5)


def _build_bands(rows: list[_Row], threshold: float) -> list[tuple[float, float]]:
    """Merge all word x-intervals in ``rows`` and split on gaps > threshold."""
    intervals = sorted(
        ((w.x0, w.x1) for row in rows for w in row.words), key=lambda t: t[0]
    )
    if not intervals:
        return []
    bands: list[list[float]] = [list(intervals[0])]
    for x0, x1 in intervals[1:]:
        last = bands[-1]
        if x0 - last[1] > threshold:
            bands.append([x0, x1])
        else:
            last[1] = max(last[1], x1)
    return [(b[0], b[1]) for b in bands]


def _assign_band(x0: float, x1: float, bands: list[tuple[float, float]]) -> int:
    center = (x0 + x1) / 2
    best_idx = 0
    best_dist = float("inf")
    for i, (b0, b1) in enumerate(bands):
        if b0 <= center <= b1:
            return i
        dist = min(abs(center - b0), abs(center - b1))
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


def _is_candidate_row(row: _Row, threshold: float) -> bool:
    if len(row.words) < 2:
        return False
    return any(g > threshold for g in _row_internal_gaps(row))


def _group_blocks(rows: list[_Row], threshold: float) -> list[list[_Row]]:
    """Group rows into candidate table blocks.

    A row starts/extends a block when it looks tabular (>=2 words with a
    wide internal gap). A non-tabular row -- e.g. a single wrapped-text
    continuation line -- is still folded into an *already open* block when
    it sits unusually close to the previous row, so continuation-row
    merging (done later, in ``_extract_block``) can see it; otherwise it
    closes the block.
    """
    row_gaps = [rows[i].top - rows[i - 1].bottom for i in range(1, len(rows))]
    positive_gaps = [g for g in row_gaps if g > 0]
    typical_gap = median(positive_gaps) if positive_gaps else 0.0
    # A gap much larger than the typical line spacing marks a new visual
    # block (a different table, or a paragraph break) even between two rows
    # that each individually look tabular.
    large_gap = max(typical_gap * 2.2, typical_gap + 10.0) if typical_gap > 0 else float("inf")

    blocks: list[list[_Row]] = []
    current: list[_Row] = []
    for i, row in enumerate(rows):
        gap = row.top - rows[i - 1].bottom if i > 0 else 0.0
        is_candidate = _is_candidate_row(row, threshold)
        tight_continuation = (
            not is_candidate
            and current
            and typical_gap > 0
            and gap < typical_gap * 0.6
        )
        block_broken = bool(current) and gap > large_gap

        if block_broken:
            if len(current) >= 2:
                blocks.append(current)
            current = []

        if is_candidate or tight_continuation:
            current.append(row)
        else:
            if len(current) >= 2:
                blocks.append(current)
            current = []
    if len(current) >= 2:
        blocks.append(current)
    return blocks


def _extract_block(
    page: Page, block: list[_Row], page_number: int, index: int, threshold: float
) -> TableResult | None:
    bands = _build_bands(block, threshold)
    if len(bands) < 2:
        return None

    grid: list[list[str]] = []
    overflow_rows: set[int] = set()
    boundary_rows: set[int] = set()

    for row in block:
        cells = ["" for _ in bands]
        for w in row.words:
            band_idx = _assign_band(w.x0, w.x1, bands)
            b0, b1 = bands[band_idx]
            if w.x1 > b1 + 2 or w.x0 < b0 - 2:
                boundary_rows.add(len(grid))
            if w.x1 > b1 + 6:
                overflow_rows.add(len(grid))
            cells[band_idx] = f"{cells[band_idx]} {w.text}".strip()
        grid.append(cells)

    # Continuation-row merging: a tightly spaced row with content in very
    # few bands likely continues the row above (wrapped text) rather than
    # starting a new logical row.
    row_gaps = [block[i].top - block[i - 1].bottom for i in range(1, len(block))]
    typical_gap = median([g for g in row_gaps if g > 0]) if row_gaps else 0.0

    merged_grid: list[list[str]] = []
    continuation_rows: list[int] = []
    uncertain_joins: list[int] = []
    for i, cells in enumerate(grid):
        nonempty = [j for j, c in enumerate(cells) if c]
        is_continuation_candidate = (
            i > 0
            and merged_grid
            and len(nonempty) >= 1
            and len(nonempty) <= max(1, len(bands) // 3)
            and typical_gap > 0
            and (block[i].top - block[i - 1].bottom) < typical_gap * 0.6
        )
        if is_continuation_candidate:
            continuation_rows.append(i)
            target = merged_grid[-1]
            for j in nonempty:
                if target[j]:
                    target[j] = f"{target[j]} {cells[j]}".strip()
                else:
                    target[j] = cells[j]
            if len(nonempty) > 1:
                uncertain_joins.append(i)
        else:
            merged_grid.append(cells)

    if len(merged_grid) < 2:
        return None

    warnings: list[str] = []
    nonempty_counts = {
        sum(1 for c in row if c) for row in merged_grid if any(c for c in row)
    }
    if len(nonempty_counts) > 1:
        warnings.append("column_count_varies")

    if boundary_rows:
        warnings.append(f"possible_merged_cell:rows={sorted(boundary_rows)}")
    if overflow_rows:
        warnings.append(f"text_overflow_band:rows={sorted(overflow_rows)}")
    if continuation_rows:
        warnings.append(f"continuation_rows_joined:rows={continuation_rows}")
    if uncertain_joins:
        warnings.append(f"continuation_join_uncertain:rows={uncertain_joins}")

    x0 = min(b[0] for b in bands)
    x1 = max(b[1] for b in bands)
    top = min(r.top for r in block)
    bottom = max(r.bottom for r in block)

    bold = row_bold_ratio(page, (x0, top, x1, block[0].bottom))
    header_detected, header_conf, header_warnings = detect_header(
        merged_grid, first_row_bold=bold
    )
    warnings.extend(header_warnings)

    confidence = 1.0
    if "column_count_varies" in warnings:
        confidence -= 0.25
    if boundary_rows:
        confidence -= 0.2
    if overflow_rows:
        confidence -= 0.1
    if uncertain_joins:
        confidence -= 0.15
    confidence = max(0.0, min(1.0, confidence))

    return TableResult(
        page=page_number,
        index=index,
        strategy="whitespace",
        bbox=(x0, top, x1, bottom),
        rows=merged_grid,
        header=merged_grid[0] if header_detected and merged_grid else None,
        header_detected=header_detected,
        header_confidence=header_conf,
        confidence=confidence,
        warnings=warnings,
    )


def extract_whitespace_tables(page: Page, page_number: int) -> list[TableResult]:
    """Detect and extract all whitespace-aligned tables on ``page``."""
    raw_words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    if not raw_words:
        return []
    words = [
        _Word(text=w["text"], x0=w["x0"], x1=w["x1"], top=w["top"], bottom=w["bottom"])
        for w in raw_words
    ]
    rows = _cluster_rows(words)
    if len(rows) < 2:
        return []

    threshold = _gap_threshold(words)
    blocks = _group_blocks(rows, threshold)

    results = []
    for idx, block in enumerate(blocks):
        result = _extract_block(page, block, page_number, idx, threshold)
        if result is not None:
            results.append(result)
    return results
