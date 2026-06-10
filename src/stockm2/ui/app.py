from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from stockm2.data.providers.base import FundamentalsProvider, ProviderError
from stockm2.data.providers.fixture import FixtureProvider
from stockm2.data.providers.fmp import FMPProvider
from stockm2.data.providers.sec_yahoo import SecYahooProvider
from stockm2.models.buffett import BuffettConfig, BuffettInput, BuffettValuation, evaluate_buffett_valuation
from stockm2.ui.cache import clear_input_cache, load_cached_input, save_cached_input
from stockm2.ui.presets import (
    DEFAULT_PRESETS,
    load_all_presets,
    load_assumption_presets,
    save_assumption_presets,
    save_custom_presets,
)


load_dotenv()


def build_config() -> BuffettConfig:
    config = st.session_state.get("assumption_config", BuffettConfig.legacy_defaults())
    st.sidebar.header("Assumptions")
    config.weighted_growth = st.sidebar.toggle(
        "Weight years",
        value=config.weighted_growth,
        help="Give more importance to some years of EPS growth history instead of treating every year equally.",
    )
    weights_text = st.sidebar.text_input(
        "Year weights",
        value=",".join(str(value) for value in config.year_weights),
        help="The weights used when 'Weight years' is on. Higher numbers make those years matter more in the growth estimate.",
    )
    config.year_weights = [float(value.strip()) for value in weights_text.split(",") if value.strip()]
    config.clip_growth = st.sidebar.toggle(
        "Clip EPS growth",
        value=config.clip_growth,
        help="Limit extremely high or low EPS growth values so one unusual year does not distort the model too much.",
    )
    config.growth_clip_min = st.sidebar.number_input(
        "Clip min",
        value=float(config.growth_clip_min),
        help="The lowest yearly EPS growth allowed after clipping. Example: -0.50 means growth cannot be treated as worse than -50%.",
    )
    config.growth_clip_max = st.sidebar.number_input(
        "Clip max",
        value=float(config.growth_clip_max),
        help="The highest yearly EPS growth allowed after clipping. Example: 0.50 means growth cannot be treated as better than +50%.",
    )
    config.max_non_positive_growth_years = st.sidebar.number_input(
        "Max non-positive years",
        min_value=0,
        max_value=10,
        value=config.max_non_positive_growth_years,
        help="How many flat or negative growth years are allowed before the stock is rejected by the model.",
    )
    config.dampener_mode = st.sidebar.selectbox(
        "Dampener mode",
        ["legacy", "legacy_1_0", "fixed", "per_negative_year", "none"],
        help=(
            "Controls how aggressively the model reduces the growth estimate to be more conservative. "
            "Legacy starts at 0.8, subtracts 0.1 for each negative weighted growth year, and adds back 0.1 once if any reduction happened. "
            "Legacy 1.0 works the same way but starts at 1.0 instead of 0.8. "
            "Fixed always uses the fixed dampener. Per-negative-year starts from the dampener start and reduces it for each negative year. "
            "None disables dampening and uses the raw average growth."
        ),
    )
    config.fixed_dampener = st.sidebar.number_input(
        "Fixed dampener",
        value=float(config.fixed_dampener),
        help="Used in fixed mode. A lower number reduces projected growth more. Example: 0.80 keeps 80% of the growth estimate.",
    )
    config.dampener_start = st.sidebar.number_input(
        "Dampener start",
        value=float(config.dampener_start),
        help="Starting dampener value used in per-negative-year mode before reductions are applied.",
    )
    config.dampener_reduction_per_non_positive = st.sidebar.number_input(
        "Dampener reduction",
        value=float(config.dampener_reduction_per_non_positive),
        help="How much the dampener is reduced for each negative growth year in per-negative-year mode.",
    )
    config.dampener_addback = st.sidebar.number_input(
        "Dampener addback",
        value=float(config.dampener_addback),
        help="A small amount added back after reductions in some dampener modes so the model is not overly harsh.",
    )
    config.forecast_years = st.sidebar.number_input(
        "Forecast years",
        min_value=1,
        max_value=20,
        value=config.forecast_years,
        help="How many years into the future the model projects EPS and price.",
    )
    config.target_return = st.sidebar.number_input(
        "Target return",
        value=float(config.target_return),
        help="The yearly return you want the stock to deliver. Higher values make the target price more conservative.",
    )
    config.sell_return = st.sidebar.number_input(
        "Sell return",
        value=float(config.sell_return),
        help="The yearly return used to calculate the model sell price. Lower values usually produce a higher sell price.",
    )
    config.margin_of_safety = st.sidebar.number_input(
        "Margin of safety",
        value=float(config.margin_of_safety),
        help="Extra discount applied to the target price to create the model buy price.",
    )
    config.pe_basis = st.sidebar.selectbox(
        "PE basis",
        ["average", "latest", "manual"],
        help="Choose which PE ratio the model should use: the average historical PE, the latest PE, or your own manual value.",
    )
    if config.pe_basis == "manual":
        config.manual_pe = st.sidebar.number_input(
            "Manual PE",
            min_value=0.01,
            value=20.0,
            help="The PE ratio to use when PE basis is set to manual.",
        )
    if st.sidebar.button("Restore legacy defaults"):
        st.session_state["assumption_config"] = BuffettConfig.legacy_defaults()
        st.rerun()
    st.session_state["assumption_config"] = config
    return config


def build_provider() -> tuple[str, str, bool, FundamentalsProvider]:
    st.sidebar.header("Data")
    provider_name = st.sidebar.selectbox(
        "Provider",
        ["sec_yahoo", "fixture", "fmp"],
        index=0,
    )
    use_cache = st.sidebar.toggle(
        "Use saved stock records",
        value=True,
        help="Reuse previously saved stock records from the local database so repeated runs are much faster.",
    )
    if st.sidebar.button("Clear saved stock records"):
        clear_input_cache()
        st.sidebar.success("Saved stock records cleared.")
    if provider_name == "sec_yahoo":
        st.sidebar.caption("Free provider: SEC Companyfacts for EPS and Yahoo Finance chart data for prices.")
        provider_scope = "default"
        return provider_name, provider_scope, use_cache, SecYahooProvider()
    if provider_name == "fmp":
        api_key = st.sidebar.text_input("FMP API key", value=os.getenv("FMP_API_KEY", ""), type="password")
        if not api_key:
            raise ProviderError("FMP provider selected but no API key is configured")
        st.sidebar.caption("Live API data. Historical PE is reconstructed from annual EPS and historical prices.")
        provider_scope = f"api-key-length:{len(api_key)}"
        return provider_name, provider_scope, use_cache, FMPProvider(api_key=api_key)

    st.sidebar.caption("Fixture data is cached demo data from this repo and may be stale.")
    return (
        provider_name,
        str(Path("tests/fixtures/buffett_inputs.json").resolve()),
        use_cache,
        FixtureProvider(Path("tests/fixtures/buffett_inputs.json")),
    )


def get_stock_input(
    provider_name: str,
    provider_scope: str,
    use_cache: bool,
    provider: FundamentalsProvider,
    ticker: str,
    years: int,
) -> BuffettInput:
    if use_cache:
        cached_input = load_cached_input(provider_name, provider_scope, ticker, years)
        if cached_input is not None:
            return cached_input
    stock_input = provider.get_annual_buffett_input(ticker, years)
    if use_cache:
        save_cached_input(provider_name, provider_scope, ticker, years, stock_input)
    return stock_input


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


def format_price_gap(gap: float | None) -> str:
    if gap is None:
        return "not available"
    if gap > 0:
        direction = "above"
    elif gap < 0:
        direction = "below"
    else:
        direction = "at"
    return f"{abs(gap):.2%} {direction}"


def build_result_row(valuation: BuffettValuation) -> dict[str, object]:
    return {
        "ticker": valuation.ticker,
        "company_name": valuation.company_name,
        "current_price": valuation.current_price,
        "buy_price": valuation.buy_price,
        "target_price": valuation.target_price,
        "sell_price": valuation.sell_price,
        "gap": None if valuation.current_price_gap is None else valuation.current_price_gap * 100,
        "avg_eps_growth": valuation.average_eps_growth * 100,
        "avg_eps_growth_clamped": valuation.adjusted_eps_growth * 100,
        "rejection_reason_count": len(valuation.rejection_reasons),
        "accepted": valuation.accepted,
        "rejection_reasons": ", ".join(valuation.rejection_reasons),
        "current_vs_target_gap": None if valuation.current_vs_target_gap is None else valuation.current_vs_target_gap * 100,
        "current_vs_projected_future_gap": (
            None if valuation.current_vs_projected_future_gap is None else valuation.current_vs_projected_future_gap * 100
        ),
    }


def render_results(valuations: list[BuffettValuation], config: BuffettConfig) -> None:
    if not valuations:
        return

    st.subheader("Results")
    search_text = st.text_input("Search stocks", placeholder="Ticker or company name")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    accepted_filter = filter_col1.selectbox("Accepted", ["all", "accepted", "rejected"])
    max_rejection_reasons = filter_col2.number_input("Max rejection reasons", min_value=0, value=10)
    min_gap_percent = filter_col3.number_input("Min % vs buy price", value=-1000.0)
    max_gap_percent = filter_col4.number_input("Max % vs buy price", value=10000.0)

    rank_options = {
        "% below/above buy price": "gap",
        "% below/above target price": "current_vs_target_gap",
        "% below/above projected price": "current_vs_projected_future_gap",
        "Average EPS growth": "avg_eps_growth",
        "Average EPS growth (clamped)": "avg_eps_growth_clamped",
        "Ticker": "ticker",
    }
    rank_label = st.selectbox("Rank by", list(rank_options))
    sort_desc = st.toggle("Highest first", value=False)

    rows = [build_result_row(valuation) for valuation in valuations]
    filtered_rows: list[dict[str, object]] = []
    lowered_search = search_text.strip().lower()
    for row in rows:
        if lowered_search:
            searchable_text = f"{row['ticker']} {row['company_name']}".lower()
            if lowered_search not in searchable_text:
                continue
        if accepted_filter == "accepted" and not row["accepted"]:
            continue
        if accepted_filter == "rejected" and row["accepted"]:
            continue
        if row["rejection_reason_count"] > max_rejection_reasons:
            continue
        gap_percent = float(row["gap"]) if row["gap"] is not None else None
        if gap_percent is None or gap_percent < min_gap_percent or gap_percent > max_gap_percent:
            continue
        filtered_rows.append(row)

    rank_key = rank_options[rank_label]

    def sort_value(row: dict[str, object]) -> tuple[int, object]:
        value = row[rank_key]
        if value is None:
            return (1, 0)
        return (0, value)

    filtered_rows.sort(key=sort_value, reverse=sort_desc)

    st.dataframe(
        filtered_rows,
        width="stretch",
        column_config={
            "gap": st.column_config.NumberColumn("% vs buy price", format="%.2f%%"),
            "avg_eps_growth": st.column_config.NumberColumn("Avg EPS growth", format="%.2f%%"),
            "avg_eps_growth_clamped": st.column_config.NumberColumn("Avg EPS growth (clamped)", format="%.2f%%"),
            "current_vs_target_gap": st.column_config.NumberColumn("% vs target", format="%.2f%%"),
            "current_vs_projected_future_gap": st.column_config.NumberColumn("% vs projected", format="%.2f%%"),
        },
        hide_index=True,
    )

    for valuation in valuations:
        matching_rows = [row for row in filtered_rows if row["ticker"] == valuation.ticker]
        if not matching_rows:
            continue
        st.markdown(
            f"`{valuation.ticker}` - current price: {valuation.current_price:.2f}, "
            f"model buy price: {valuation.buy_price:.2f} ; sell price: {valuation.sell_price:.2f}"
        )
        with st.expander(f"Details for {valuation.ticker}"):
            st.write(
                {
                    "current_price": valuation.current_price,
                    "buy_price": valuation.buy_price,
                    "target_price": valuation.target_price,
                    "sell_price": valuation.sell_price,
                    "gap": valuation.current_price_gap,
                    "average_eps_growth": valuation.average_eps_growth,
                    "adjusted_eps_growth": valuation.adjusted_eps_growth,
                    "current_vs_target_amount": valuation.current_vs_target_amount,
                    "current_vs_target_gap": valuation.current_vs_target_gap,
                    "current_vs_projected_future_amount": valuation.current_vs_projected_future_amount,
                    "current_vs_projected_future_gap": valuation.current_vs_projected_future_gap,
                    "accepted": valuation.accepted,
                    "rejection_reasons": valuation.rejection_reasons,
                }
            )
            st.caption(
                f"Current price is {format_price_gap(valuation.current_vs_target_gap)} the current-year target price "
                f"and {format_price_gap(valuation.current_vs_projected_future_gap)} the {config.forecast_years}-year projected price."
            )
            st.json(
                {
                    "historical_eps_growth": valuation.weighted_eps_growth_history,
                    "historical_pe": valuation.pe_history,
                    "assumptions": valuation.assumptions,
                }
            )
            render_sources(valuation)


def render_app() -> None:
    st.title("Stock M2 Buffett MVP")
    st.caption("Buffett-style valuation with shared model logic and selectable data providers.")

    fixture_path = Path("tests/fixtures/buffett_inputs.json")
    with fixture_path.open() as fixture_file:
        fixture_data = json.load(fixture_file)
    available_tickers = [item["ticker"] for item in fixture_data["stocks"]]
    default_ticker_text = ",".join(available_tickers[:2])
    if "ticker_text" not in st.session_state:
        st.session_state["ticker_text"] = default_ticker_text
    if "valuations" not in st.session_state:
        st.session_state["valuations"] = []
    if "valuation_errors" not in st.session_state:
        st.session_state["valuation_errors"] = []
    if "last_forecast_years" not in st.session_state:
        st.session_state["last_forecast_years"] = None

    config = build_config()
    try:
        provider_name, provider_scope, use_cache, provider = build_provider()
    except ProviderError as exc:
        st.error(str(exc))
        st.stop()

    presets, custom_presets = load_all_presets()
    assumption_presets = load_assumption_presets()
    preset_names = list(presets)
    selected_preset_name = st.selectbox(
        "Preset",
        options=[""] + preset_names,
        format_func=lambda name: "Select a preset" if not name else f"{name} ({len(presets[name])} tickers)",
    )
    preset_action_col, preset_save_col, preset_delete_col = st.columns(3)
    if preset_action_col.button("Load preset", disabled=not selected_preset_name):
        st.session_state["ticker_text"] = ",".join(presets[selected_preset_name])
        st.rerun()

    preset_name = preset_save_col.text_input("Save as preset", key="preset_name")
    ticker_text = st.text_area("Tickers", key="ticker_text", height=120)
    selected_tickers = [item.strip().upper() for item in ticker_text.split(",") if item.strip()]

    if preset_save_col.button("Save preset"):
        cleaned_name = preset_name.strip()
        if not cleaned_name:
            st.error("Preset name is required.")
        elif cleaned_name in DEFAULT_PRESETS:
            st.error("Default presets are read-only. Save under a new name.")
        elif not selected_tickers:
            st.error("Add at least one ticker before saving a preset.")
        else:
            custom_presets[cleaned_name] = selected_tickers
            preset_path = save_custom_presets(custom_presets)
            st.success(f"Saved preset '{cleaned_name}' to {preset_path}.")
            st.rerun()

    if preset_delete_col.button("Delete preset", disabled=selected_preset_name not in custom_presets):
        del custom_presets[selected_preset_name]
        preset_path = save_custom_presets(custom_presets)
        st.session_state["ticker_text"] = default_ticker_text
        st.success(f"Deleted preset '{selected_preset_name}' from {preset_path}.")
        st.rerun()

    st.caption(
        "Default presets are seeded and read-only. Customize the tickers above, then save them as your own preset to load later."
    )

    st.subheader("Assumption presets")
    assumption_names = list(assumption_presets)
    selected_assumption_preset = st.selectbox(
        "Assumption preset",
        options=[""] + assumption_names,
        format_func=lambda name: "Select an assumption preset" if not name else name,
    )
    assumption_col1, assumption_col2, assumption_col3 = st.columns(3)
    if assumption_col1.button("Load assumptions", disabled=not selected_assumption_preset):
        st.session_state["assumption_config"] = assumption_presets[selected_assumption_preset]
        st.rerun()
    assumption_preset_name = assumption_col2.text_input("Save assumptions as", key="assumption_preset_name")
    if assumption_col2.button("Save assumptions"):
        cleaned_name = assumption_preset_name.strip()
        if not cleaned_name:
            st.error("Assumption preset name is required.")
        else:
            assumption_presets[cleaned_name] = BuffettConfig(**asdict(config))
            preset_path = save_assumption_presets(assumption_presets)
            st.success(f"Saved assumption preset '{cleaned_name}' to {preset_path}.")
            st.rerun()
    if assumption_col3.button("Delete assumptions", disabled=selected_assumption_preset not in assumption_presets):
        del assumption_presets[selected_assumption_preset]
        preset_path = save_assumption_presets(assumption_presets)
        st.success(f"Deleted assumption preset '{selected_assumption_preset}' from {preset_path}.")
        st.rerun()

    if st.button("Run valuation"):
        valuations: list[BuffettValuation] = []
        errors: list[str] = []
        for ticker in selected_tickers:
            try:
                stock_input = get_stock_input(
                    provider_name,
                    provider_scope,
                    use_cache,
                    provider,
                    ticker,
                    config.forecast_years,
                )
                valuation = evaluate_buffett_valuation(stock_input, config)
            except Exception as exc:
                errors.append(f"{ticker}: {exc}")
                continue
            valuations.append(valuation)
        st.session_state["valuations"] = valuations
        st.session_state["valuation_errors"] = errors
        st.session_state["last_forecast_years"] = config.forecast_years

    for error in st.session_state["valuation_errors"]:
        st.error(error)

    if st.session_state["valuations"]:
        render_results(st.session_state["valuations"], config)


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()
