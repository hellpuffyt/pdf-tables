from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytest
from pdf_builders import (
    multi_page_ruled_pdf,
    ruled_table_pdf,
    ruled_table_with_wrapped_cell_pdf,
)

from pdf_tables.ruled import extract_ruled_tables


def _extract(path: Path):
    with pdfplumber.open(str(path)) as pdf:
        return extract_ruled_tables(pdf.pages[0], 1)


def test_simple_ruled_table_detected(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    tables = _extract(path)
    assert len(tables) == 1
    assert tables[0].strategy == "ruled"


def test_ruled_table_row_and_col_counts(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    table = _extract(path)[0]
    assert table.n_rows == 3
    assert table.n_cols == 2


def test_ruled_table_cell_content_matches(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    table = _extract(path)[0]
    assert table.rows[0] == ["Name", "Role"]
    assert table.rows[1] == ["Alice", "Engineer"]
    assert table.rows[2] == ["Bob", "Manager"]


def test_ruled_table_bbox_is_populated(tmp_path: Path) -> None:
    data = [["A", "B"], ["1", "2"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    table = _extract(path)[0]
    x0, top, x1, bottom = table.bbox
    assert x1 > x0
    assert bottom > top


def test_clean_ruled_table_has_no_warnings(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data, bold_header=True)
    table = _extract(path)[0]
    assert "column_count_varies" not in " ".join(table.warnings)
    assert "possible_merged_cell" not in " ".join(table.warnings)


def test_clean_ruled_table_has_high_confidence(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data, bold_header=True)
    table = _extract(path)[0]
    assert table.confidence == 1.0


def test_merged_cell_detected(tmp_path: Path) -> None:
    data = [["Name", "Role", "Notes"], ["Alice", "Engineer", "ok"], ["Team Total", "", "3 members"]]
    path = ruled_table_pdf(
        tmp_path / "t.pdf", data, col_widths=[100, 100, 150], span=((0, 2), (1, 2))
    )
    table = _extract(path)[0]
    assert any("possible_merged_cell" in w for w in table.warnings)


def test_merged_cell_lowers_confidence(tmp_path: Path) -> None:
    data = [["Name", "Role", "Notes"], ["Alice", "Engineer", "ok"], ["Team Total", "", "3 members"]]
    path = ruled_table_pdf(
        tmp_path / "t.pdf", data, col_widths=[100, 100, 150], span=((0, 2), (1, 2))
    )
    table = _extract(path)[0]
    assert table.confidence < 1.0


def test_no_merged_cell_warning_on_clean_table(tmp_path: Path) -> None:
    data = [["Name", "Role", "Notes"], ["Alice", "Engineer", "ok"], ["Bob", "Manager", "fine"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data, col_widths=[100, 100, 150])
    table = _extract(path)[0]
    assert not any("possible_merged_cell" in w for w in table.warnings)


def test_wrapped_cell_text_is_joined(tmp_path: Path) -> None:
    long_text = "A very long note that should wrap across multiple lines in this narrow cell"
    path = ruled_table_with_wrapped_cell_pdf(tmp_path / "t.pdf", long_text)
    table = _extract(path)[0]
    assert "\n" not in table.rows[1][2]
    assert "wrap" in table.rows[1][2]


def test_wrapped_cell_warning_present(tmp_path: Path) -> None:
    long_text = "A very long note that should wrap across multiple lines in this narrow cell"
    path = ruled_table_with_wrapped_cell_pdf(tmp_path / "t.pdf", long_text)
    table = _extract(path)[0]
    assert any("wrapped_text_joined" in w for w in table.warnings)


def test_no_wrapped_warning_on_single_line_cells(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    table = _extract(path)[0]
    assert not any("wrapped_text_joined" in w for w in table.warnings)


def test_bold_header_detected(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data, bold_header=True)
    table = _extract(path)[0]
    assert table.header_detected is True
    assert table.header == ["Name", "Role"]


def test_no_bold_header_ambiguous_reports_uncertain(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data, bold_header=False)
    table = _extract(path)[0]
    # No caps, no bold, no numeric-type contrast: should not confidently claim a header.
    assert table.header_detected is False
    assert "header_uncertain" in table.warnings


def test_numeric_type_mismatch_header_detected(tmp_path: Path) -> None:
    data = [
        ["Item", "Quantity"],
        ["Widgets", "12"],
        ["Gadgets", "7"],
        ["Gizmos", "30"],
    ]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    table = _extract(path)[0]
    assert table.header_detected is True


def test_all_caps_header_detected(tmp_path: Path) -> None:
    data = [["ITEM", "QUANTITY"], ["Widgets", "twelve"], ["Gadgets", "seven"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    table = _extract(path)[0]
    assert table.header_detected is True


def test_page_with_no_ruled_table_returns_empty(tmp_path: Path) -> None:
    from pdf_builders import prose_only_pdf

    path = prose_only_pdf(tmp_path / "t.pdf")
    tables = _extract(path)
    assert tables == []


def test_blank_page_returns_empty(tmp_path: Path) -> None:
    from pdf_builders import blank_pdf

    path = blank_pdf(tmp_path / "t.pdf")
    tables = _extract(path)
    assert tables == []


def test_multi_page_ruled_pdf_has_table_per_page(tmp_path: Path) -> None:
    path = multi_page_ruled_pdf(tmp_path / "t.pdf", 3)
    with pdfplumber.open(str(path)) as pdf:
        assert len(pdf.pages) == 3
        for i, page in enumerate(pdf.pages):
            tables = extract_ruled_tables(page, i + 1)
            assert len(tables) == 1
            assert tables[0].page == i + 1


def test_manifest_entry_shape(tmp_path: Path) -> None:
    data = [["Name", "Role"], ["Alice", "Engineer"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    table = _extract(path)[0]
    entry = table.to_manifest_entry()
    for key in ("page", "index", "strategy", "bbox", "n_rows", "n_cols", "confidence", "warnings"):
        assert key in entry


@pytest.mark.parametrize("n_rows", [1, 2, 5])
def test_ruled_table_various_row_counts(tmp_path: Path, n_rows: int) -> None:
    data = [["Col A", "Col B"]] + [[f"r{i}a", f"r{i}b"] for i in range(n_rows)]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    table = _extract(path)[0]
    assert table.n_rows == n_rows + 1
