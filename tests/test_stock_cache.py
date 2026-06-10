from __future__ import annotations

from pathlib import Path
import sqlite3

from stockm2.models.buffett import BuffettInput, DataSource
from stockm2.ui.cache import deserialize_buffett_input, load_cached_input, save_cached_input, serialize_buffett_input


def test_stock_input_cache_round_trip(tmp_path: Path) -> None:
    stock_input = BuffettInput(
        ticker="AAPL",
        company_name="Apple Inc.",
        latest_eps=6.13,
        eps_growth_history=[0.1, 0.2],
        pe_history=[20.0, 21.0],
        current_price=200.0,
        fiscal_years=["2022", "2023"],
        sources=[DataSource(label="Test", fields=["latest_eps"])],
    )
    payload = serialize_buffett_input(stock_input)
    restored = deserialize_buffett_input(payload)

    assert restored.ticker == "AAPL"
    assert restored.sources[0].label == "Test"


def test_cached_file_can_be_loaded(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "records.db"
    monkeypatch.setenv("STOCKM2_DB_PATH", str(database_path))
    stock_input = BuffettInput(
        ticker="MSFT",
        company_name="Microsoft Corporation",
        latest_eps=11.0,
        eps_growth_history=[0.1],
        pe_history=[25.0],
        current_price=430.0,
        fiscal_years=["2023"],
        sources=[],
    )
    save_cached_input("sec_yahoo", "saved", "MSFT", 10, stock_input)

    loaded = load_cached_input("sec_yahoo", "saved", "MSFT", 10)

    assert loaded is not None
    assert loaded.company_name == "Microsoft Corporation"
    connection = sqlite3.connect(database_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM stock_inputs").fetchone()[0]
    finally:
        connection.close()
    assert count == 1
