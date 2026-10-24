# Production readiness — pdf-tables

Audit date: 2026-10-22. Tested commit: `b8c0d08` (branch `audit/production-readiness`, based on `main` @ `b17f6f5`).

## Scope

CLI that extracts tables from text-based PDFs (pdfplumber) using ruled-line and whitespace-alignment
strategies, writes one CSV per table plus `manifest.json` with confidence and warnings. No OCR.

## Platforms

CPython 3.10+, `pdfplumber>=0.11,<1.0` (pure Python). Verified on macOS 27 (Apple M5), CPython 3.12.14.

## Clean-clone verification (commit `b8c0d08`)

```bash
git clone -b audit/production-readiness <local clone> pdf-tables && cd pdf-tables
uv venv --python 3.12 .venv && . .venv/bin/activate && uv pip install -e ".[dev]"
# CI smoke step: reportlab 3x2 ruled table
pdf-tables smoke.pdf --out smoke_out      # 1 table, rows=3 cols=2, CSV written
pdf-tables smoke.pdf --pages 5 --out x    # exit 2: selects no page
pytest && ruff check . && mypy            # 93 passed / clean / clean
python -m build --wheel                   # wheel builds
```

## Commands and results

| Command | Baseline (`b17f6f5`) | After (`b8c0d08`) |
| --- | --- | --- |
| `pytest` | exit 0 — 86 passed, 0 failed, 0 skipped | exit 0 — 93 passed, 0 failed, 0 skipped |
| `ruff check .` / `mypy` | exit 0 / exit 0 | exit 0 / exit 0 |
| `uvx pip-audit` (pdfplumber, pdfminer.six, Pillow, …) | — | no known vulnerabilities |

CI status — default branch: success (`b17f6f5`, 2026-08-30); audit branch: pending until pushed.

## Extraction verification (independent of the test suite)

10 random tables (2–6 columns, 3–12 rows, text + integers) rendered with reportlab twice — with a
grid, and as plain positioned text. `--strategy ruled` and `--strategy whitespace`: 20/20 tables
reproduced cell for cell. Not verified: scanned PDFs (no OCR by design), real-world multi-column
layouts, merged cells in real documents.

## Bugs found and fixed

| Severity | Bug | Regression test |
| --- | --- | --- |
| Medium (supply chain) | README `pip install pdf-tables` installs an unrelated PyPI project (v0.0.1, different author) | README fixed |
| Low (silent wrong result) | `--pages 99`/`0`/`6-9` exited 0 with zero tables; `x`/`3-1` gave "failed to process" | `tests/test_extract.py::test_parse_pages_selecting_no_page_is_an_error`, `test_parse_pages_malformed_is_an_error`, `tests/test_cli.py::test_cli_pages_outside_the_document_is_a_usage_error` |

## Security review

- Output file names are generated (`table_p{page}_{index}.csv`), never taken from PDF content — no path traversal.
- CSV cells are verbatim: spreadsheet formula injection from untrusted PDFs is possible; documented in README/SECURITY.md (not changed, to keep data faithful).
- History secret scan: no hits. `pip-audit`: clean. Workflow permissions `contents: read`.

## Known limitations

No OCR; heuristic whitespace detection; header detection is heuristic (`header_uncertain` common).

## Acceptance checklist

| # | Item | Expected | Evidence | Result |
| --- | --- | --- | --- | --- |
| 1 | Ruled tables extracted exactly | cell-for-cell | 10/10 generated | PASS |
| 2 | Whitespace tables extracted exactly | cell-for-cell | 10/10 generated | PASS |
| 3 | Manifest with confidence/warnings | present | smoke run | PASS |
| 4 | Bad page selection → exit 2 | error | new tests | PASS |
| 5 | Non-PDF → exit 1 message | message | manual run | PASS |
| 6 | Clean clone | install/smoke/tests/wheel | above | PASS |

## Classification proposal

**Partially Verified** — correct on generated PDFs; real-world documents not available for testing.
