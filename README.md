# pdf-tables

Extract tables from PDFs into CSV — and, unlike most extractors, tell you
which of the extracted tables you actually need to check by hand.

## What

`pdf-tables` reads a PDF, finds tables on each page using two independent
detection strategies, and writes one CSV per table plus a JSON manifest
describing every table: its page, bounding box, which strategy found it, a
`confidence` score, and a list of `warnings` explaining exactly what looked
ambiguous.

## Why

Every table extractor silently guesses. Feed it a PDF with no ruling lines,
a merged cell, or a column that wraps onto a second line, and it emits a
confidently wrong CSV — you find out during reconciliation, days later, or
you don't find out at all. `pdf-tables` is built around the opposite
premise: **report uncertainty instead of hiding it**. Run it over 200 tables
and it tells you which 3 need a human to look at them, instead of making you
check all 200.

## How detection works

### Ruled tables

When a table has ruling lines (a grid of horizontal and vertical rules),
`pdf-tables` uses `pdfplumber`'s line-intersection table finder to build the
cell grid from where those rules cross, then layers its own logic on top:

- A cell that appears as `None` at a grid position pdfplumber flagged as
  absorbed by a neighbor is unambiguous evidence of a **merged cell** — not
  a guess, since the ruling geometry says so directly.
- A cell whose rendered text contains multiple lines is already
  unambiguously joined by the ruling box boundaries; it's reported as
  `wrapped_text_joined`, informationally, since there's no doubt about which
  cell the wrapped lines belong to.
- Column count is checked across rows; if it varies, the grid itself is
  inconsistent and the table is flagged.
- The header row's font is inspected for boldness (from character-level
  font metadata) as one signal into header detection (see below).

### Whitespace-aligned tables

This is the harder, more common case: no ruling lines at all, just text
positioned in visual columns. `pdf-tables` implements this itself:

1. Words are clustered into rows by vertical position.
2. All word x-intervals across a run of rows are merged, and gaps between
   merged intervals wider than a threshold (derived from the page's average
   character width) become **column band boundaries** — the
   "x-coordinate histogram gap" approach.
3. Each word is assigned to the band its center falls in; words in the same
   row and band are joined into a cell.
4. Rows that are tightly spaced (closer than the page's typical line
   spacing) and mostly empty except for one or two cells are treated as
   **wrapped-text continuations** and folded into the row above, with a
   warning when the fold itself is ambiguous (more than one non-empty cell
   in the continuation line).
5. A run of rows only becomes a reported table when it has at least two
   rows and at least two stable column bands — a single column of prose, or
   one label, is correctly left alone.

### Auto mode

`--strategy auto` (the default) runs ruled detection first — rules are
unambiguous evidence when present — then runs whitespace detection over the
same page. A whitespace result that overlaps a ruled table only contributes
a `strategy_disagreement` warning when the two strategies actually disagree
on the **column count** (row-count differences are expected and not
flagged, since the two strategies join wrapped lines with different
heuristics). Whitespace tables that don't overlap any ruled table are
reported as their own tables, so a page can mix both kinds.

## Features

- Two independent detection strategies (ruled and whitespace), both fully
  implemented.
- Per-table `confidence` score and a list of specific `warnings`.
- Merged-cell detection.
- Multi-line / wrapped-cell handling, with honest uncertainty reporting for
  the ambiguous whitespace case.
- Header-row detection with a heuristic confidence score (case contrast,
  numeric type mismatch, bold font) and honest `header_uncertain` reporting
  when no signal is strong enough.
- `--pages` selector, `--strategy` override, `--min-confidence` filter.
- CSV per table plus a single `manifest.json` with everything needed to
  triage results programmatically.
- No system dependencies — no Java, no poppler binary. Pure-Python via
  `pdfplumber`.

## Architecture

```
src/pdf_tables/
  models.py      TableResult dataclass shared by both strategies
  ruled.py        Ruled-table detection (line intersections + own heuristics)
  whitespace.py   Whitespace-aligned detection (x-coordinate histogram gaps)
  headers.py      Header-row confidence heuristic
  util.py         Shared helpers (bold-ratio detection, median)
  extract.py      Orchestration: page selection, strategy dispatch, auto-mode merge
  output.py       CSV + manifest.json writers
  cli.py          Command-line interface
```

## Installation

```bash
pip install pdf-tables
```

Or from a local checkout:

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+. The only runtime dependency is `pdfplumber`, a
pure-Python wheel — no Java, no poppler, no other system binaries.

## Usage

```bash
pdf-tables report.pdf
pdf-tables report.pdf --out extracted/
pdf-tables report.pdf --strategy ruled
pdf-tables report.pdf --pages "1,3-5"
pdf-tables report.pdf --min-confidence 0.7
```

```
usage: pdf-tables [-h] [-o OUT] [--strategy {auto,ruled,whitespace}]
                   [--pages PAGES] [--min-confidence MIN_CONFIDENCE]
                   [--version]
                   pdf

positional arguments:
  pdf                   Path to the input PDF file

options:
  -o OUT, --out OUT     Output directory for CSVs and manifest.json (default: tables_out)
  --strategy {auto,ruled,whitespace}
                        Detection strategy to use (default: auto)
  --pages PAGES         Page selector, 1-based, e.g. "1,3-5" (default: all pages)
  --min-confidence MIN_CONFIDENCE
                        Drop tables with confidence below this threshold (0.0-1.0)
```

### Library usage

```python
import pdfplumber
from pdf_tables import extract_tables

with pdfplumber.open("report.pdf") as pdf:
    tables = extract_tables(pdf, strategy="auto", min_confidence=0.5)

for table in tables:
    print(table.page, table.strategy, table.confidence, table.warnings)
    for row in table.rows:
        print(row)
```

## Output format

Running `pdf-tables report.pdf -o out/` produces:

```
out/
  table_p1_0.csv
  table_p2_0.csv
  manifest.json
```

`manifest.json`:

```json
{
  "source": "report.pdf",
  "n_tables": 2,
  "tables": [
    {
      "page": 1,
      "index": 0,
      "strategy": "ruled",
      "bbox": [131.0, 78.0, 481.0, 156.0],
      "n_rows": 3,
      "n_cols": 3,
      "header_detected": true,
      "header_confidence": 0.9,
      "header": ["Name", "Role", "Notes"],
      "confidence": 1.0,
      "warnings": [],
      "csv": "table_p1_0.csv"
    }
  ]
}
```

## Confidence and warnings reference

| Warning | Meaning |
|---|---|
| `column_count_varies` | Rows in the table have different cell counts — the grid itself is inconsistent. |
| `possible_merged_cell:rows=[...]` | One or more rows contain a cell that spans a detected column boundary (ruled: pdfplumber's absorbed-cell marker; whitespace: a word straddling a band edge). |
| `wrapped_text_joined:rows=[...]` | A ruled cell's multiple lines were joined into one value. Informational — the cell boundary is unambiguous, so this is not an uncertainty flag. |
| `text_overflow_band:rows=[...]` | Whitespace-strategy only: a word extends well past its column band's right edge, suggesting the band boundaries may be slightly off for that row. |
| `continuation_rows_joined:rows=[...]` | Whitespace-strategy only: one or more tightly-spaced, mostly-empty rows were folded into the row above as wrapped-text continuations. |
| `continuation_join_uncertain:rows=[...]` | A continuation-row join above involved more than one non-empty cell, so which cell it continues is less certain. |
| `header_uncertain` | No signal (case, numeric-type contrast, bold font) was strong enough to confidently call the first row a header. |
| `strategy_disagreement:whitespace_rows=N,whitespace_cols=M` | Auto mode only: the whitespace strategy, run over the same region as a detected ruled table, found a different column count. |

`confidence` (0.0–1.0) starts at 1.0 for a table and is reduced for each
structural issue found (column-count variance, merged cells, ambiguous
continuation joins, text overflowing a band, and a whitespace/ruled
disagreement in auto mode). A confidence of `1.0` with no warnings means the
table's structure was unambiguous under every check this tool runs — not
that the OCR/text content itself is guaranteed accurate.

## Examples

Extract every table from a report, keep only the ones the tool is fairly
sure about, and inspect the manifest for the rest:

```bash
pdf-tables quarterly_report.pdf --out out/ --min-confidence 0.7
python -c "import json; m = json.load(open('out/manifest.json')); \
    [print(t['csv'], t['warnings']) for t in m['tables'] if t['confidence'] < 0.7]"
```

Force whitespace-only detection on a scanned-and-OCR'd PDF with no ruling
lines:

```bash
pdf-tables scanned.pdf --strategy whitespace
```

## Testing

```bash
pytest
```

The test suite (86 tests) generates every fixture PDF at test time with
`reportlab` — no binary PDFs are committed to the repository. Fixtures
include ruled tables, whitespace-aligned tables, a merged cell, wrapped
text (both ruled and whitespace), varying column counts, multi-page PDFs,
pages with two tables using different strategies, prose-only pages, and
blank pages — each checked for both the ambiguity warning firing when it
should and, just as important, *not* firing on a clean table.

## Limitations

- Whitespace detection groups rows into a table block using vertical-gap
  and column-band heuristics; densely mixed prose-and-table layouts (e.g. a
  table embedded inside a paragraph with similar line spacing) can be
  missed or over-merged.
- Rotated or skewed page content is not corrected for.
- Confidence scores are heuristic, not statistical guarantees — they
  reflect which structural checks this tool ran and passed, not ground
  truth.
- No OCR: this operates on text already present in the PDF. Scanned images
  without a text layer will not produce any tables.
- Nested or irregular ruling-line tables (e.g. a table inside a table cell)
  are extracted as pdfplumber's line-finder sees them, which may split or
  merge unexpectedly complex layouts.

## Security

`pdf-tables` only reads the PDF file(s) you pass it and writes CSV/JSON
files to the output directory you specify — it makes no network requests.
As with any PDF-parsing tool, don't run it against untrusted PDFs in a
security-sensitive context without the usual sandboxing precautions; parsing
malformed input could in principle trigger bugs in the underlying
`pdfplumber`/`pypdf` stack.

## License

MIT — see [LICENSE](LICENSE).
