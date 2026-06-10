from __future__ import annotations

from pathlib import Path

from stockm2.models.buffett import BuffettConfig
from stockm2.ui.presets import load_assumption_presets, save_assumption_presets


def test_assumption_presets_are_saved_and_loaded(tmp_path: Path) -> None:
    preset_path = tmp_path / "assumptions.json"
    config = BuffettConfig.legacy_defaults()
    config.forecast_years = 7
    config.manual_pe = 22.0
    config.pe_basis = "manual"

    save_assumption_presets({"My assumptions": config}, preset_path)
    loaded = load_assumption_presets(preset_path)

    assert loaded["My assumptions"].forecast_years == 7
    assert loaded["My assumptions"].manual_pe == 22.0
    assert loaded["My assumptions"].pe_basis == "manual"
