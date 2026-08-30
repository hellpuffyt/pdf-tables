# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-08-30

### Added

- Ruled-table detection: cell grids built from ruling-line intersections, via pdfplumber's line-based table finder, with original logic layered on top for merged-cell detection, column-count-variance detection, and confidence scoring.
- Whitespace-aligned table detection: a from-scratch implementation that clusters word positions into rows, builds column bands from an x-coordinate histogram of gaps, and assigns words to bands.
- Multi-line / wrapped-cell handling for both strategies, including continuation-row merging for whitespace tables with an explicit "uncertain join" warning when the merge is ambiguous.
- Header-row detection heuristic combining case (ALL CAPS), numeric type-mismatch, and bold-font signals into a confidence score, honestly reporting `header_uncertain` when no signal is strong enough.
- Ambiguity reporting: per-table `confidence` score and `warnings` list covering column-count variance, possible merged cells, text overflowing a column band, uncertain continuation-row joins, and strategy disagreement in `auto` mode.
- CLI (`pdf-tables`) with `--strategy auto|ruled|whitespace`, `--pages`, and `--min-confidence` options; writes one CSV per table plus a `manifest.json` describing every table's page, bbox, strategy, confidence, and warnings.
- Test suite (86 tests) built on programmatically generated PDF fixtures (reportlab), covering both strategies, each warning firing and correctly not firing on clean tables, header detection, page selection, and PDFs with no tables.
