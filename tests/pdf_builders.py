"""Programmatic PDF fixture builders used across the test suite.

Fixtures are generated at test time with reportlab rather than committed as
binary files, so the exact layout of each hard case is visible in the code
that builds it.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

_STYLES = getSampleStyleSheet()


def ruled_table_pdf(
    path: Path,
    data: list[list[str]],
    *,
    col_widths: list[float] | None = None,
    bold_header: bool = False,
    span: tuple[tuple[int, int], tuple[int, int]] | None = None,
) -> Path:
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]
    if bold_header:
        style_cmds.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
    if span is not None:
        style_cmds.append(("SPAN", span[0], span[1]))
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle(style_cmds))
    doc.build([table])
    return path


def ruled_table_with_wrapped_cell_pdf(path: Path, long_text: str) -> Path:
    data = [
        ["Name", "Role", "Notes"],
        ["Alice", "Engineer", Paragraph(long_text, _STYLES["Normal"])],
        ["Bob", "Manager", "Short"],
    ]
    return ruled_table_pdf(path, data, col_widths=[100, 100, 150])


def multi_page_ruled_pdf(path: Path, n_pages: int) -> Path:
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    flowables = []
    for p in range(n_pages):
        data = [["Col A", "Col B"], [f"page{p}-a1", f"page{p}-b1"], [f"page{p}-a2", f"page{p}-b2"]]
        t = Table(data)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)]))
        flowables.append(t)
        if p < n_pages - 1:
            from reportlab.platypus import PageBreak

            flowables.append(PageBreak())
    doc.build(flowables)
    return path


def whitespace_table_pdf(
    path: Path,
    headers: list[str],
    rows: list[list[str]],
    *,
    x_positions: list[int] | None = None,
    bold_header: bool = True,
    row_gap: int = 18,
    y_start: int = 700,
) -> Path:
    c = canvas.Canvas(str(path), pagesize=letter)
    xs = x_positions or [100 + i * 120 for i in range(len(headers))]
    c.setFont("Helvetica-Bold" if bold_header else "Helvetica", 10)
    for x, h in zip(xs, headers, strict=False):
        c.drawString(x, y_start, h)
    c.setFont("Helvetica", 10)
    y = y_start - row_gap
    for row in rows:
        for x, cell in zip(xs, row, strict=False):
            if cell:
                c.drawString(x, y, cell)
        y -= row_gap
    c.showPage()
    c.save()
    return path


def whitespace_varying_columns_pdf(path: Path) -> Path:
    return whitespace_table_pdf(
        path,
        ["Item", "Qty", "Price"],
        [
            ["Widget", "3", "9.99"],
            ["Gadget", "1", ""],  # missing a cell -> column count varies
            ["Gizmo", "5", "4.50"],
        ],
        x_positions=[100, 220, 300],
        bold_header=False,
    )


def whitespace_wrapped_pdf(path: Path) -> Path:
    """A whitespace table where one row's description wraps onto a second
    tightly-spaced line, simulating wrapped text with no ruling lines."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 10)
    xs = [100, 220, 340]
    c.drawString(xs[0], 700, "Item")
    c.drawString(xs[1], 700, "Qty")
    c.drawString(xs[2], 700, "Description")
    y = 682
    c.drawString(xs[0], y, "Widget")
    c.drawString(xs[1], y, "3")
    c.drawString(xs[2], y, "A small part")
    y -= 12  # tight spacing: continuation line
    c.drawString(xs[2], y, "used in assembly")
    y -= 18
    c.drawString(xs[0], y, "Gadget")
    c.drawString(xs[1], y, "1")
    c.drawString(xs[2], y, "Standalone")
    c.showPage()
    c.save()
    return path


def prose_only_pdf(path: Path) -> Path:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "This is just a paragraph of prose text.")
    c.drawString(100, 680, "It has no tabular structure whatsoever.")
    c.drawString(100, 660, "Just ordinary sentences, one after another.")
    c.showPage()
    c.save()
    return path


def blank_pdf(path: Path) -> Path:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.showPage()
    c.save()
    return path


def two_tables_one_page_pdf(path: Path) -> Path:
    """One ruled table (drawn with grid lines) and one separate
    whitespace-aligned table, both on the same page."""
    c = canvas.Canvas(str(path), pagesize=letter)

    # Ruled table near the top: a 2-column, 3-row grid with manual lines.
    x0, top, x1, bottom = 100, 720, 300, 660
    col_x = [x0, 200, x1]
    row_y = [top, 700, 680, bottom]
    for x in col_x:
        c.line(x, top, x, bottom)
    for y in row_y:
        c.line(x0, y, x1, y)
    c.setFont("Helvetica", 10)
    cells = [["A", "B"], ["1", "2"], ["3", "4"]]
    for r, row in enumerate(cells):
        for col, text in enumerate(row):
            cx = col_x[col] + 8
            cy = row_y[r] - 14
            c.drawString(cx, cy, text)

    # Whitespace-aligned table further down the page.
    xs = [100, 220, 340]
    c.drawString(xs[0], 500, "Name")
    c.drawString(xs[1], 500, "Score")
    c.drawString(xs[2], 500, "Grade")
    ys = 482
    for name, score, grade in [("Ann", "88", "B"), ("Ray", "95", "A")]:
        c.drawString(xs[0], ys, name)
        c.drawString(xs[1], ys, score)
        c.drawString(xs[2], ys, grade)
        ys -= 16

    c.showPage()
    c.save()
    return path
