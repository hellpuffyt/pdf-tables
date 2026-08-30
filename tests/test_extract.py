from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytest
from pdf_builders import (
    blank_pdf,
    multi_page_ruled_pdf,
    ruled_table_pdf,
    two_tables_one_page_pdf,
    whitespace_table_pdf,
    whitespace_varying_columns_pdf,
)

from pdf_tables.extract import _parse_pages, extract_tables


def test_parse_pages_none_means_all() -> None:
    assert _parse_pages(None, 5) == [1, 2, 3, 4, 5]


def test_parse_pages_single() -> None:
    assert _parse_pages("2", 5) == [2]


def test_parse_pages_range() -> None:
    assert _parse_pages("2-4", 5) == [2, 3, 4]


def test_parse_pages_mixed() -> None:
    assert _parse_pages("1,3-4", 5) == [1, 3, 4]


def test_parse_pages_clamped_to_range() -> None:
    assert _parse_pages("1,10", 5) == [1]


def test_parse_pages_empty_string() -> None:
    assert _parse_pages("", 3) == [1, 2, 3]


def test_extract_ruled_strategy(tmp_path: Path) -> None:
    data = [["A", "B"], ["1", "2"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="ruled")
    assert len(tables) == 1
    assert tables[0].strategy == "ruled"


def test_extract_whitespace_strategy(tmp_path: Path) -> None:
    path = whitespace_table_pdf(
        tmp_path / "t.pdf", ["Name", "Role"], [["Alice", "Engineer"], ["Bob", "Manager"]]
    )
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="whitespace")
    assert len(tables) == 1
    assert tables[0].strategy == "whitespace"


def test_extract_auto_strategy_finds_ruled_table(tmp_path: Path) -> None:
    data = [["A", "B"], ["1", "2"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="auto")
    assert len(tables) == 1
    assert tables[0].strategy == "ruled"


def test_extract_auto_strategy_finds_both_tables_on_page(tmp_path: Path) -> None:
    path = two_tables_one_page_pdf(tmp_path / "t.pdf")
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="auto")
    strategies = {t.strategy for t in tables}
    assert "ruled" in strategies
    assert "whitespace" in strategies
    assert len(tables) == 2


def test_min_confidence_filters_low_confidence_tables(tmp_path: Path) -> None:
    path = whitespace_varying_columns_pdf(tmp_path / "t.pdf")
    with pdfplumber.open(str(path)) as pdf:
        all_tables = extract_tables(pdf, strategy="whitespace", min_confidence=0.0)
        filtered = extract_tables(pdf, strategy="whitespace", min_confidence=0.9)
    assert len(all_tables) == 1
    assert len(filtered) == 0


def test_min_confidence_keeps_clean_tables(tmp_path: Path) -> None:
    data = [["A", "B"], ["1", "2"]]
    path = ruled_table_pdf(tmp_path / "t.pdf", data)
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="ruled", min_confidence=0.9)
    assert len(tables) == 1


def test_pages_selector_restricts_pages(tmp_path: Path) -> None:
    path = multi_page_ruled_pdf(tmp_path / "t.pdf", 3)
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="ruled", pages="2")
    assert len(tables) == 1
    assert tables[0].page == 2


def test_pages_selector_range(tmp_path: Path) -> None:
    path = multi_page_ruled_pdf(tmp_path / "t.pdf", 3)
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="ruled", pages="1-2")
    assert {t.page for t in tables} == {1, 2}


def test_no_tables_page_returns_empty_list(tmp_path: Path) -> None:
    path = blank_pdf(tmp_path / "t.pdf")
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="auto")
    assert tables == []


def test_table_indices_are_stable_and_zero_based(tmp_path: Path) -> None:
    path = two_tables_one_page_pdf(tmp_path / "t.pdf")
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy="auto")
    indices = sorted(t.index for t in tables)
    assert indices == list(range(len(tables)))


@pytest.mark.parametrize("strategy", ["auto", "ruled", "whitespace"])
def test_all_strategies_accept_a_blank_pdf(tmp_path: Path, strategy: str) -> None:
    path = blank_pdf(tmp_path / "t.pdf")
    with pdfplumber.open(str(path)) as pdf:
        tables = extract_tables(pdf, strategy=strategy)
    assert tables == []
