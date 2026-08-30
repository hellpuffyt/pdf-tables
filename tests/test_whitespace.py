from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytest
from pdf_builders import (
    blank_pdf,
    prose_only_pdf,
    whitespace_table_pdf,
    whitespace_varying_columns_pdf,
    whitespace_wrapped_pdf,
)

from pdf_tables.whitespace import extract_whitespace_tables


def _extract(path: Path):
    with pdfplumber.open(str(path)) as pdf:
        return extract_whitespace_tables(pdf.pages[0], 1)


def test_simple_whitespace_table_detected(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf",
        ["Name", "Role", "Salary"],
        [["Alice", "Engineer", "95000"], ["Bob", "Manager", "105000"]],
    )
    tables = _extract(path)
    assert len(tables) == 1
    assert tables[0].strategy == "whitespace"


def test_whitespace_table_row_col_counts(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf",
        ["Name", "Role", "Salary"],
        [["Alice", "Engineer", "95000"], ["Bob", "Manager", "105000"]],
    )
    table = _extract(path)[0]
    assert table.n_rows == 3
    assert table.n_cols == 3


def test_whitespace_table_cell_content(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf",
        ["Name", "Role", "Salary"],
        [["Alice", "Engineer", "95000"]],
    )
    table = _extract(path)[0]
    assert table.rows[0] == ["Name", "Role", "Salary"]
    assert table.rows[1] == ["Alice", "Engineer", "95000"]


def test_whitespace_header_detected_when_bold_caps(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf",
        ["NAME", "ROLE", "SALARY"],
        [["Alice", "Engineer", "95000"], ["Bob", "Manager", "105000"]],
        bold_header=True,
    )
    table = _extract(path)[0]
    assert table.header_detected is True
    assert table.header == ["NAME", "ROLE", "SALARY"]


def test_whitespace_clean_table_has_no_warnings(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf",
        ["Name", "Role", "Salary"],
        [
            ["Alice", "Engineer", "95000"],
            ["Bob", "Manager", "105000"],
            ["Carol", "Designer", "88000"],
        ],
    )
    table = _extract(path)[0]
    assert table.warnings == []


def test_whitespace_clean_table_has_high_confidence(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf",
        ["Name", "Role", "Salary"],
        [["Alice", "Engineer", "95000"], ["Bob", "Manager", "105000"]],
    )
    table = _extract(path)[0]
    assert table.confidence == 1.0


def test_whitespace_varying_column_count_warns(tmp_path: Path) -> None:
    path = whitespace_varying_columns_pdf(tmp_path / "t.pdf")
    table = _extract(path)[0]
    assert any("column_count_varies" in w for w in table.warnings)


def test_whitespace_varying_column_count_lowers_confidence(tmp_path: Path) -> None:
    path = whitespace_varying_columns_pdf(tmp_path / "t.pdf")
    table = _extract(path)[0]
    assert table.confidence < 1.0


def test_whitespace_no_column_variance_warning_on_clean_rows(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf",
        ["Item", "Qty", "Price"],
        [["Widget", "3", "9.99"], ["Gadget", "1", "5.00"], ["Gizmo", "5", "4.50"]],
        x_positions=[100, 220, 300],
    )
    table = _extract(path)[0]
    assert not any("column_count_varies" in w for w in table.warnings)


def test_whitespace_wrapped_text_joined(tmp_path: Path) -> None:
    path = whitespace_wrapped_pdf(tmp_path / "t.pdf")
    table = _extract(path)[0]
    joined = " ".join(row_text for row in table.rows for row_text in row)
    assert "small part used in assembly" in joined


def test_whitespace_wrapped_text_warning_present(tmp_path: Path) -> None:
    path = whitespace_wrapped_pdf(tmp_path / "t.pdf")
    table = _extract(path)[0]
    assert any("continuation_rows_joined" in w for w in table.warnings)


def test_whitespace_wrapped_table_reduces_row_count(tmp_path: Path) -> None:
    path = whitespace_wrapped_pdf(tmp_path / "t.pdf")
    table = _extract(path)[0]
    # header + Widget + Gadget = 3 logical rows, not 4 physical lines.
    assert table.n_rows == 3


def test_prose_only_page_returns_no_whitespace_table(tmp_path: Path) -> None:
    path = prose_only_pdf(tmp_path / "t.pdf")
    tables = _extract(path)
    assert tables == []


def test_blank_page_returns_no_whitespace_table(tmp_path: Path) -> None:
    path = blank_pdf(tmp_path / "t.pdf")
    tables = _extract(path)
    assert tables == []


def test_single_row_of_text_is_not_a_table(tmp_path: Path) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    path = tmp_path / "t.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 10)
    c.drawString(100, 700, "Name")
    c.drawString(220, 700, "Role")
    c.showPage()
    c.save()
    tables = _extract(path)
    assert tables == []


def test_two_columns_minimum_required(tmp_path: Path) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    path = tmp_path / "t.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 10)
    for i, line in enumerate(["Alpha", "Beta", "Gamma"]):
        c.drawString(100, 700 - i * 18, line)
    c.showPage()
    c.save()
    tables = _extract(path)
    assert tables == []


def test_bbox_covers_all_rows(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf",
        ["Name", "Role"],
        [["Alice", "Engineer"], ["Bob", "Manager"], ["Carol", "Designer"]],
        x_positions=[100, 220],
    )
    table = _extract(path)[0]
    x0, top, x1, bottom = table.bbox
    assert bottom > top
    assert x1 > x0


@pytest.mark.parametrize("n_rows", [2, 3, 6])
def test_whitespace_various_row_counts(tmp_path: Path, n_rows: int) -> None:
    rows = [[f"n{i}", f"r{i}"] for i in range(n_rows)]
    path = whitespace_table_pdf(tmp_path / "t.pdf", ["Name", "Role"], rows, x_positions=[100, 220])
    table = _extract(path)[0]
    assert table.n_rows == n_rows + 1
