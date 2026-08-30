"""Command-line interface for pdf-tables."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pdfplumber

from . import __version__
from .extract import extract_tables
from .output import write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-tables",
        description=(
            "Extract tables from a PDF into CSV files, reporting confidence "
            "and warnings when the table structure is ambiguous."
        ),
    )
    parser.add_argument("pdf", type=Path, help="Path to the input PDF file")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("tables_out"),
        help="Output directory for CSVs and manifest.json (default: tables_out)",
    )
    parser.add_argument(
        "--strategy",
        choices=["auto", "ruled", "whitespace"],
        default="auto",
        help="Detection strategy to use (default: auto)",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help='Page selector, 1-based, e.g. "1,3-5" (default: all pages)',
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Drop tables with confidence below this threshold (0.0-1.0)",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(f"error: no such file: {args.pdf}", file=sys.stderr)
        return 2

    try:
        with pdfplumber.open(str(args.pdf)) as pdf:
            tables = extract_tables(
                pdf,
                strategy=args.strategy,
                pages=args.pages,
                min_confidence=args.min_confidence,
            )
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        print(f"error: failed to process {args.pdf}: {exc}", file=sys.stderr)
        return 1

    manifest_path = write_outputs(tables, args.out, source=str(args.pdf))

    print(f"Extracted {len(tables)} table(s) from {args.pdf}")
    for t in tables:
        flag = " ".join(t.warnings) if t.warnings else "none"
        print(
            f"  page {t.page} table {t.index}: strategy={t.strategy} "
            f"rows={t.n_rows} cols={t.n_cols} confidence={t.confidence:.2f} "
            f"warnings=[{flag}]"
        )
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
