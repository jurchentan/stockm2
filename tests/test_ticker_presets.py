from __future__ import annotations

from pathlib import Path

from stockm2.ui.presets import DEFAULT_PRESETS, load_all_presets, normalize_tickers, save_custom_presets


def test_normalize_tickers_uppercases_and_deduplicates() -> None:
    assert normalize_tickers([" aapl ", "msft", "AAPL", ""]) == ["AAPL", "MSFT"]


def test_custom_presets_are_saved_and_loaded(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.json"
    save_custom_presets({"My Watchlist": ["aapl", "msft", "AAPL"]}, preset_path)
    all_presets, custom_presets = load_all_presets(preset_path)

    assert custom_presets == {"My Watchlist": ["AAPL", "MSFT"]}
    assert all_presets["My Watchlist"] == ["AAPL", "MSFT"]
    assert all_presets["S&P 500 Energy"] == DEFAULT_PRESETS["S&P 500 Energy"]
