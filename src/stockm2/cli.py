from __future__ import annotations

import argparse
import json
from pathlib import Path

from stockm2.data.providers.base import FundamentalsProvider
from stockm2.data.providers.fixture import FixtureProvider
from stockm2.data.providers.fmp import FMPProvider
from stockm2.data.providers.sec_yahoo import SecYahooProvider
from stockm2.models.buffett import BuffettConfig, evaluate_buffett_valuation


DEFAULT_FIXTURE = Path("tests/fixtures/buffett_inputs.json")


def _parse_tickers(args: argparse.Namespace) -> list[str]:
    tickers: list[str] = []
    if args.ticker:
        tickers.extend(args.ticker)
    if args.tickers:
        tickers.extend([item.strip() for item in args.tickers.split(",") if item.strip()])
    if args.input:
        tickers.extend([line.strip() for line in Path(args.input).read_text().splitlines() if line.strip()])
    deduped: list[str] = []
    for ticker in tickers:
        upper = ticker.upper()
        if upper not in deduped:
            deduped.append(upper)
    return deduped


def _provider_from_args(args: argparse.Namespace) -> FundamentalsProvider:
    if args.provider == "fmp":
        return FMPProvider()
    if args.provider == "sec_yahoo":
        return SecYahooProvider()
    fixture_path = Path(args.fixture or DEFAULT_FIXTURE)
    return FixtureProvider(fixture_path)


def _config_from_args(args: argparse.Namespace) -> BuffettConfig:
    config = BuffettConfig.legacy_defaults()
    config.forecast_years = args.forecast_years
    config.target_return = args.target_return
    config.margin_of_safety = args.margin_of_safety
    config.weighted_growth = not args.no_weighting
    config.clip_growth = not args.no_clipping
    config.growth_clip_min = args.clip_min
    config.growth_clip_max = args.clip_max
    config.max_non_positive_growth_years = args.max_non_positive_growth_years
    config.dampener_mode = args.dampener_mode
    config.fixed_dampener = args.fixed_dampener
    config.dampener_start = args.dampener_start
    config.dampener_reduction_per_non_positive = args.dampener_reduction
    config.dampener_addback = args.dampener_addback
    config.pe_basis = args.pe_basis
    config.manual_pe = args.manual_pe
    return config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stockm2")
    subparsers = parser.add_subparsers(dest="command", required=True)

    buffett = subparsers.add_parser("buffett")
    buffett.add_argument("ticker", nargs="*")
    buffett.add_argument("--tickers")
    buffett.add_argument("--input")
    buffett.add_argument("--provider", choices=["fixture", "fmp", "sec_yahoo"], default="sec_yahoo")
    buffett.add_argument("--fixture")
    buffett.add_argument("--format", choices=["table", "json"], default="table")
    buffett.add_argument("--forecast-years", type=int, default=10)
    buffett.add_argument("--target-return", type=float, default=0.18)
    buffett.add_argument("--margin-of-safety", type=float, default=0.25)
    buffett.add_argument("--no-weighting", action="store_true")
    buffett.add_argument("--no-clipping", action="store_true")
    buffett.add_argument("--clip-min", type=float, default=-0.5)
    buffett.add_argument("--clip-max", type=float, default=0.5)
    buffett.add_argument("--max-non-positive-growth-years", type=int, default=2)
    buffett.add_argument("--dampener-mode", choices=["legacy", "fixed", "per_negative_year"], default="legacy")
    buffett.add_argument("--fixed-dampener", type=float, default=0.8)
    buffett.add_argument("--dampener-start", type=float, default=0.8)
    buffett.add_argument("--dampener-reduction", type=float, default=0.1)
    buffett.add_argument("--dampener-addback", type=float, default=0.1)
    buffett.add_argument("--pe-basis", choices=["average", "latest", "manual"], default="average")
    buffett.add_argument("--manual-pe", type=float)
    return parser


def _format_table(results: list[dict[str, object]]) -> str:
    lines = ["ticker\taccepted\tcurrent_price\tbuy_price\ttarget_price\tgap\treasons"]
    for item in results:
        gap = item["current_price_gap"]
        gap_text = "n/a" if gap is None else f"{gap:.4f}"
        lines.append(
            f"{item['ticker']}\t{item['accepted']}\t{item['current_price']:.2f}\t{item['buy_price']:.2f}\t{item['target_price']:.2f}\t{gap_text}\t{','.join(item['rejection_reasons'])}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command != "buffett":
        parser.error("unsupported command")

    tickers = _parse_tickers(args)
    if not tickers:
        parser.error("at least one ticker is required")

    provider = _provider_from_args(args)
    config = _config_from_args(args)
    results = []
    for ticker in tickers:
        stock = provider.get_annual_buffett_input(ticker, config.forecast_years)
        results.append(evaluate_buffett_valuation(stock, config).to_dict())

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(_format_table(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
