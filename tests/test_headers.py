from __future__ import annotations

from pdf_tables.headers import detect_header


def test_bold_header_strong_signal() -> None:
    rows = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    detected, confidence, warnings = detect_header(rows, first_row_bold=True)
    assert detected is True
    assert confidence >= 0.5
    assert warnings == []


def test_no_signals_reports_uncertain() -> None:
    rows = [["Name", "Role"], ["Alice", "Engineer"], ["Bob", "Manager"]]
    detected, confidence, warnings = detect_header(rows, first_row_bold=None)
    assert detected is False
    assert "header_uncertain" in warnings


def test_all_caps_header() -> None:
    rows = [["NAME", "ROLE"], ["Alice", "Engineer"]]
    detected, confidence, _ = detect_header(rows)
    assert detected is True


def test_type_mismatch_numeric_column() -> None:
    rows = [["Item", "Count"], ["Widgets", "5"], ["Gadgets", "9"], ["Gizmos", "3"]]
    detected, _, _ = detect_header(rows)
    assert detected is True


def test_single_row_cannot_have_header() -> None:
    rows = [["Name", "Role"]]
    detected, confidence, warnings = detect_header(rows)
    assert detected is False
    assert confidence == 0.0
    assert "insufficient_rows_for_header" in warnings


def test_empty_rows_cannot_have_header() -> None:
    detected, confidence, warnings = detect_header([])
    assert detected is False
    assert confidence == 0.0


def test_all_numeric_rows_including_first_no_header_signal() -> None:
    rows = [["1", "2"], ["3", "4"], ["5", "6"]]
    detected, confidence, _ = detect_header(rows)
    assert detected is False


def test_bold_false_does_not_sink_other_signals() -> None:
    rows = [["ITEM", "QTY"], ["Widgets", "5"], ["Gadgets", "9"]]
    detected, confidence, _ = detect_header(rows, first_row_bold=False)
    assert detected is True


def test_confidence_is_bounded() -> None:
    rows = [["ITEM", "QTY"], ["Widgets", "5"], ["Gadgets", "9"]]
    _, confidence, _ = detect_header(rows, first_row_bold=True)
    assert 0.0 <= confidence <= 1.0
