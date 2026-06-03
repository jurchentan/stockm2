from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from stockm2.data.providers.base import FundamentalsProvider, ProviderError
from stockm2.data.providers.fixture import FixtureProvider
from stockm2.data.providers.fmp import FMPProvider
from stockm2.data.providers.sec_yahoo import SecYahooProvider
from stockm2.models.buffett import BuffettConfig, BuffettValuation, evaluate_buffett_valuation


load_dotenv()


def build_config() -> BuffettConfig:
    config = BuffettConfig.legacy_defaults()
    st.sidebar.header("Assumptions")
    config.weighted_growth = st.sidebar.toggle("Weight years", value=config.weighted_growth)
    weights_text = st.sidebar.text_input("Year weights", value=",".join(str(value) for value in config.year_weights))
    config.year_weights = [float(value.strip()) for value in weights_text.split(",") if value.strip()]
    config.clip_growth = st.sidebar.toggle("Clip EPS growth", value=config.clip_growth)
    config.growth_clip_min = st.sidebar.number_input("Clip min", value=float(config.growth_clip_min))
    config.growth_clip_max = st.sidebar.number_input("Clip max", value=float(config.growth_clip_max))
    config.max_non_positive_growth_years = st.sidebar.number_input(
        "Max non-positive years", min_value=0, max_value=10, value=config.max_non_positive_growth_years
    )
    config.dampener_mode = st.sidebar.selectbox("Dampener mode", ["legacy", "fixed", "per_negative_year"])
    config.fixed_dampener = st.sidebar.number_input("Fixed dampener", value=float(config.fixed_dampener))
    config.dampener_start = st.sidebar.number_input("Dampener start", value=float(config.dampener_start))
    config.dampener_reduction_per_non_positive = st.sidebar.number_input(
        "Dampener reduction", value=float(config.dampener_reduction_per_non_positive)
    )
    config.dampener_addback = st.sidebar.number_input("Dampener addback", value=float(config.dampener_addback))
    config.forecast_years = st.sidebar.number_input("Forecast years", min_value=1, max_value=20, value=config.forecast_years)
    config.target_return = st.sidebar.number_input("Target return", value=float(config.target_return))
    config.margin_of_safety = st.sidebar.number_input("Margin of safety", value=float(config.margin_of_safety))
    config.pe_basis = st.sidebar.selectbox("PE basis", ["average", "latest", "manual"])
    if config.pe_basis == "manual":
        config.manual_pe = st.sidebar.number_input("Manual PE", min_value=0.01, value=20.0)
    if st.sidebar.button("Restore legacy defaults"):
        st.rerun()
    return config


def build_provider() -> FundamentalsProvider:
    st.sidebar.header("Data")
    default_provider = "sec_yahoo"
    provider_name = st.sidebar.selectbox(
        "Provider",
        ["sec_yahoo", "fixture", "fmp"],
        index=0,
    )
    if provider_name == "sec_yahoo":
        st.sidebar.caption("Free provider: SEC Companyfacts for EPS and Yahoo Finance chart data for prices.")
        return SecYahooProvider()
    if provider_name == "fmp":
        api_key = st.sidebar.text_input("FMP API key", value=os.getenv("FMP_API_KEY", ""), type="password")
        if not api_key:
            raise ProviderError("FMP provider selected but no API key is configured")
        st.sidebar.caption("Live API data. Historical PE is reconstructed from annual EPS and historical prices.")
        return FMPProvider(api_key=api_key)

    st.sidebar.caption("Fixture data is cached demo data from this repo and may be stale.")
    return FixtureProvider(Path("tests/fixtures/buffett_inputs.json"))


def render_sources(valuation: BuffettValuation) -> None:
    st.markdown("**Sources**")
    sources = getattr(valuation, "sources", [])
    if not sources:
        st.caption("No source metadata available for this provider.")
        return

    for source in sources:
        covered_fields = ", ".join(source.fields)
        label = f"[{source.label}]({source.url})" if source.url else source.label
        st.markdown(f"- {label}: `{covered_fields}`")
        if source.note:
            st.caption(source.note)


def render_app() -> None:
    st.title("Stock M2 Buffett MVP")
    st.caption("Buffett-style valuation with shared model logic and selectable data providers.")

    fixture_path = Path("tests/fixtures/buffett_inputs.json")
    with fixture_path.open() as fixture_file:
        fixture_data = json.load(fixture_file)
    available_tickers = [item["ticker"] for item in fixture_data["stocks"]]

    config = build_config()
    try:
        provider = build_provider()
    except ProviderError as exc:
        st.error(str(exc))
        st.stop()

    ticker_text = st.text_input("Tickers", value=",".join(available_tickers[:2]))
    selected_tickers = [item.strip().upper() for item in ticker_text.split(",") if item.strip()]

    if st.button("Run valuation"):
        for ticker in selected_tickers:
            try:
                stock_input = provider.get_annual_buffett_input(ticker, config.forecast_years)
                valuation = evaluate_buffett_valuation(stock_input, config)
            except Exception as exc:
                st.error(f"{ticker}: {exc}")
                continue
            st.subheader(f"{valuation.company_name} ({valuation.ticker})")
            st.write(
                {
                    "current_price": valuation.current_price,
                    "buy_price": valuation.buy_price,
                    "target_price": valuation.target_price,
                    "sell_price": valuation.sell_price,
                    "gap": valuation.current_price_gap,
                    "accepted": valuation.accepted,
                    "rejection_reasons": valuation.rejection_reasons,
                }
            )
            st.json(
                {
                    "historical_eps_growth": valuation.weighted_eps_growth_history,
                    "historical_pe": valuation.pe_history,
                    "assumptions": valuation.assumptions,
                }
            )
            render_sources(valuation)


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()
