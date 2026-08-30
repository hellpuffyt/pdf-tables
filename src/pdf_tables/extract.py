"""Top-level orchestration: page selection, strategy dispatch, filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .models import TableResult
from .ruled import extract_ruled_tables
from .whitespace import extract_whitespace_tables

if TYPE_CHECKING:
    from pdfplumber.pdf import PDF

Strategy = Literal["auto", "ruled", "whitespace"]


BBox = tuple[float, float, float, float]


def _bbox_overlap_ratio(a: BBox, b: BBox) -> float:
    ax0, atop, ax1, abottom = a
    bx0, btop, bx1, bbottom = b
    ix0, ix1 = max(ax0, bx0), min(ax1, bx1)
    itop, ibottom = max(atop, btop), min(abottom, bbottom)
    if ix1 <= ix0 or ibottom <= itop:
        return 0.0
    inter = (ix1 - ix0) * (ibottom - itop)
    area_a = max(1e-6, (ax1 - ax0) * (abottom - atop))
    area_b = max(1e-6, (bx1 - bx0) * (bbottom - btop))
    return inter / min(area_a, area_b)


def _parse_pages(pages_spec: str | None, n_pages: int) -> list[int]:
    """Parse a 1-based page selector like "1,3-5" into a sorted list."""
    if not pages_spec:
        return list(range(1, n_pages + 1))
    result: set[int] = set()
    for part in pages_spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            result.update(range(start, end + 1))
        else:
            result.add(int(part))
    return sorted(p for p in result if 1 <= p <= n_pages)


def extract_tables(
    pdf: PDF,
    *,
    strategy: Strategy = "auto",
    pages: str | None = None,
    min_confidence: float = 0.0,
) -> list[TableResult]:
    """Extract tables from ``pdf`` according to ``strategy``.

    ``strategy='auto'`` runs ruled detection first (rules are unambiguous
    when present); whitespace detection then fills in the rest of each
    page, and any whitespace table that substantially overlaps an
    already-found ruled table is treated as corroboration (or, when the two
    disagree on shape, a "strategy_disagreement" warning) rather than a
    separate result.
    """
    page_numbers = _parse_pages(pages, len(pdf.pages))
    results: list[TableResult] = []

    for page_number in page_numbers:
        page = pdf.pages[page_number - 1]
        page_results: list[TableResult] = []

        if strategy in ("auto", "ruled"):
            page_results.extend(extract_ruled_tables(page, page_number))

        if strategy == "whitespace":
            page_results.extend(extract_whitespace_tables(page, page_number))
        elif strategy == "auto":
            ruled_here = [t for t in page_results if t.strategy == "ruled"]
            ws_tables = extract_whitespace_tables(page, page_number)
            for ws in ws_tables:
                overlapping = [
                    r for r in ruled_here if _bbox_overlap_ratio(r.bbox, ws.bbox) > 0.6
                ]
                if not overlapping:
                    page_results.append(ws)
                    continue
                for r in overlapping:
                    # Row-count differences alone are common and expected: the
                    # two strategies join wrapped/continuation lines using
                    # different heuristics. Only a *column* count mismatch
                    # reflects real structural disagreement worth flagging.
                    if r.n_cols != ws.n_cols:
                        r.warnings.append(
                            f"strategy_disagreement:whitespace_rows={ws.n_rows},"
                            f"whitespace_cols={ws.n_cols}"
                        )
                        r.confidence = max(0.0, r.confidence - 0.15)

        # Re-index within the page in a stable, deterministic order.
        page_results.sort(key=lambda t: (t.bbox[1], t.bbox[0]))
        for i, t in enumerate(page_results):
            t.index = i
        results.extend(page_results)

    if min_confidence > 0.0:
        results = [t for t in results if t.confidence >= min_confidence]

    return results
