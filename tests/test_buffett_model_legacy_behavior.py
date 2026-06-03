from __future__ import annotations

import math

import pytest

from stockm2.data.providers.fixture import FixtureProvider
from stockm2.models.buffett import BuffettConfig, BuffettInput, evaluate_buffett_valuation


@pytest.fixture()
def fixture_provider() -> FixtureProvider:
    return FixtureProvider("tests/fixtures/buffett_inputs.json")


def test_legacy_weighting_and_buy_price_for_aapl(fixture_provider: FixtureProvider) -> None:
    valuation = evaluate_buffett_valuation(fixture_provider.get_annual_buffett_input("AAPL", 10), BuffettConfig.legacy_defaults())
    assert valuation.accepted is True
    assert valuation.weighted_eps_growth_history[0] == pytest.approx(0.04)
    assert valuation.weighted_eps_growth_history[-1] == pytest.approx(0.195)
    assert valuation.average_eps_growth == pytest.approx(0.1078, rel=1e-4)
    assert valuation.average_pe == pytest.approx(19.5, rel=1e-4)
    assert valuation.dampener == pytest.approx(0.8)
    assert valuation.buy_price == pytest.approx(39.17366359745202, rel=1e-6)
    assert valuation.current_price_gap == pytest.approx((195.0 - valuation.buy_price) / valuation.buy_price)


def test_rejects_when_more_than_two_non_positive_growth_years(fixture_provider: FixtureProvider) -> None:
    valuation = evaluate_buffett_valuation(fixture_provider.get_annual_buffett_input("BAD", 10), BuffettConfig.legacy_defaults())
    assert valuation.accepted is False
    assert "too_many_non_positive_growth_years" in valuation.rejection_reasons


def test_can_disable_weighting() -> None:
    stock = BuffettInput(
        ticker="TEST",
        company_name="Test Co",
        latest_eps=5.0,
        eps_growth_history=[0.1] * 10,
        pe_history=[20.0] * 10,
        current_price=100.0,
    )
    config = BuffettConfig.legacy_defaults()
    config.weighted_growth = False
    valuation = evaluate_buffett_valuation(stock, config)
    assert valuation.weighted_eps_growth_history == [0.1] * 10
    assert valuation.average_eps_growth == pytest.approx(0.1)


def test_zero_price_is_rejected() -> None:
    stock = BuffettInput(
        ticker="ZERO",
        company_name="Zero Price",
        latest_eps=5.0,
        eps_growth_history=[0.1] * 10,
        pe_history=[20.0] * 10,
        current_price=0.0,
    )
    valuation = evaluate_buffett_valuation(stock)
    assert valuation.accepted is False
    assert "current_price_must_be_positive" in valuation.rejection_reasons


def test_negative_eps_is_rejected() -> None:
    stock = BuffettInput(
        ticker="NEG",
        company_name="Negative EPS",
        latest_eps=-1.0,
        eps_growth_history=[0.1] * 10,
        pe_history=[20.0] * 10,
        current_price=10.0,
    )
    valuation = evaluate_buffett_valuation(stock)
    assert valuation.accepted is False
    assert "latest_eps_must_be_positive" in valuation.rejection_reasons


def test_missing_pe_history_raises() -> None:
    stock = BuffettInput(
        ticker="PELESS",
        company_name="No PE",
        latest_eps=2.0,
        eps_growth_history=[0.1] * 10,
        pe_history=[],
        current_price=10.0,
    )
    with pytest.raises(ValueError, match="pe_history requires at least 1 values"):
        evaluate_buffett_valuation(stock)


def test_insufficient_eps_history_for_weighted_legacy_mode_raises() -> None:
    stock = BuffettInput(
        ticker="SHORT",
        company_name="Short History",
        latest_eps=2.0,
        eps_growth_history=[0.1] * 3,
        pe_history=[10.0] * 10,
        current_price=10.0,
    )
    with pytest.raises(ValueError, match="weighted legacy mode expects growth history length to match year weights"):
        evaluate_buffett_valuation(stock)


def test_projected_eps_can_turn_negative_and_reject() -> None:
    stock = BuffettInput(
        ticker="CRASH",
        company_name="Crash Co",
        latest_eps=2.0,
        eps_growth_history=[-2.0] * 10,
        pe_history=[20.0] * 10,
        current_price=10.0,
    )
    config = BuffettConfig.legacy_defaults()
    config.weighted_growth = False
    config.clip_growth = False
    config.dampener_mode = "fixed"
    config.fixed_dampener = 1.0
    valuation = evaluate_buffett_valuation(stock, config)
    assert valuation.projected_eps < 0
    assert "projected_eps_must_be_positive" in valuation.rejection_reasons


def test_non_numeric_api_data_raises() -> None:
    stock = BuffettInput(
        ticker="BADTYPE",
        company_name="Bad Type",
        latest_eps=2.0,
        eps_growth_history=[0.1] * 9 + ["oops"],
        pe_history=[20.0] * 10,
        current_price=10.0,
    )
    with pytest.raises(ValueError, match="non-numeric"):
        evaluate_buffett_valuation(stock)


def test_latest_pe_basis_changes_selected_pe(fixture_provider: FixtureProvider) -> None:
    config = BuffettConfig.legacy_defaults()
    config.pe_basis = "latest"
    valuation = evaluate_buffett_valuation(fixture_provider.get_annual_buffett_input("AAPL", 10), config)
    assert valuation.selected_pe == pytest.approx(25.0)


def test_manual_pe_basis_changes_selected_pe(fixture_provider: FixtureProvider) -> None:
    config = BuffettConfig.legacy_defaults()
    config.pe_basis = "manual"
    config.manual_pe = 30.0
    valuation = evaluate_buffett_valuation(fixture_provider.get_annual_buffett_input("AAPL", 10), config)
    assert valuation.selected_pe == pytest.approx(30.0)
    assert math.isfinite(valuation.buy_price)
