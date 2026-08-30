# Contributing

Thanks for considering a contribution to pdf-tables.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Running the checks

```bash
pytest
ruff check .
mypy
```

All three must pass before a change is merged. `mypy` runs in strict mode
against `src/`; test files are not held to strict typing.

## Test fixtures

Test PDFs are generated at test time with `reportlab` (see
`tests/pdf_builders.py`) rather than committed as binary files. If you add a
test that needs a new kind of PDF layout, add a builder function there
instead of checking in a `.pdf`.

## Style

- Format and lint with `ruff`.
- Type-check library code with `mypy --strict`.
- Prefer small, focused functions with a docstring explaining *why*, not
  just *what* — this project's value is in explaining its own uncertainty,
  so the code should be equally legible about its own heuristics.

## Pull requests

- Keep changes focused; unrelated cleanups belong in a separate PR.
- Add or update tests for any behavioral change.
- Update `CHANGELOG.md` under an `[Unreleased]` heading.

## Reporting issues

Please include the pdfplumber version, a minimal reproducing PDF (or the
code used to generate one), and the CLI command you ran.
