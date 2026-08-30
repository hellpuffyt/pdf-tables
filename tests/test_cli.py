from __future__ import annotations

import json
from pathlib import Path

from pdf_builders import blank_pdf, multi_page_ruled_pdf, ruled_table_pdf

from pdf_tables.cli import main


def test_cli_extracts_ruled_table(tmp_path: Path, capsys) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    out_dir = tmp_path / "out"
    rc = main([str(path), "-o", str(out_dir)])
    assert rc == 0
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["n_tables"] == 1


def test_cli_missing_file_returns_error(tmp_path: Path) -> None:
    rc = main([str(tmp_path / "does_not_exist.pdf")])
    assert rc == 2


def test_cli_pages_option(tmp_path: Path) -> None:
    path = multi_page_ruled_pdf(tmp_path / "t.pdf", 3)
    out_dir = tmp_path / "out"
    rc = main([str(path), "-o", str(out_dir), "--pages", "2"])
    assert rc == 0
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["n_tables"] == 1
    assert manifest["tables"][0]["page"] == 2


def test_cli_min_confidence_option(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    out_dir = tmp_path / "out"
    rc = main([str(path), "-o", str(out_dir), "--min-confidence", "1.1"])
    assert rc == 0
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["n_tables"] == 0


def test_cli_strategy_option(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    out_dir = tmp_path / "out"
    rc = main([str(path), "-o", str(out_dir), "--strategy", "whitespace"])
    assert rc == 0
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    # A ruled-only table shouldn't be picked up by the whitespace strategy
    # in a way that guarantees a match, but the command must still succeed.
    assert "n_tables" in manifest


def test_cli_no_tables_produces_empty_manifest(tmp_path: Path) -> None:
    path = blank_pdf(tmp_path / "t.pdf")
    out_dir = tmp_path / "out"
    rc = main([str(path), "-o", str(out_dir)])
    assert rc == 0
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["n_tables"] == 0
    assert manifest["tables"] == []


def test_cli_prints_summary(tmp_path: Path, capsys) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    out_dir = tmp_path / "out"
    main([str(path), "-o", str(out_dir)])
    captured = capsys.readouterr()
    assert "Extracted 1 table(s)" in captured.out


def test_cli_version_flag() -> None:
    import pytest

    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
