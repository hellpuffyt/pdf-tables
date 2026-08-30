"""Small shared helpers used by both detection strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdfplumber.page import Page


def row_bold_ratio(page: Page, bbox: tuple[float, float, float, float]) -> bool | None:
    """Best-effort: does the text inside ``bbox`` render mostly bold?

    Returns ``None`` when there is not enough text to judge either way.
    """
    x0, top, x1, bottom = bbox
    chars = [
        c
        for c in page.chars
        if c["x0"] >= x0 - 1
        and c["x1"] <= x1 + 1
        and c["top"] >= top - 1
        and c["bottom"] <= bottom + 1
        and c.get("text", "").strip()
    ]
    if not chars:
        return None
    bold = sum(1 for c in chars if "bold" in str(c.get("fontname", "")).lower())
    return (bold / len(chars)) > 0.6


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0
