"""Core data structures shared across detection strategies."""

from __future__ import annotations

from dataclasses import dataclass, field

BBox = tuple[float, float, float, float]


@dataclass
class TableResult:
    """A single detected table, independent of the strategy that found it."""

    page: int
    index: int
    strategy: str
    bbox: BBox
    rows: list[list[str]]
    header: list[str] | None
    header_detected: bool
    header_confidence: float
    confidence: float
    warnings: list[str] = field(default_factory=list)

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    @property
    def n_cols(self) -> int:
        return max((len(r) for r in self.rows), default=0)

    def body_rows(self) -> list[list[str]]:
        """Rows excluding the detected header, if any."""
        if self.header_detected and self.rows:
            return self.rows[1:]
        return self.rows

    def to_manifest_entry(self) -> dict[str, object]:
        return {
            "page": self.page,
            "index": self.index,
            "strategy": self.strategy,
            "bbox": list(self.bbox),
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "header_detected": self.header_detected,
            "header_confidence": round(self.header_confidence, 4),
            "header": self.header,
            "confidence": round(self.confidence, 4),
            "warnings": list(self.warnings),
        }
