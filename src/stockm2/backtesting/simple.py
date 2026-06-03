from __future__ import annotations

from dataclasses import dataclass

from stockm2.models.buffett import BuffettValuation


@dataclass(slots=True)
class BacktestCase:
    valuation: BuffettValuation
    future_price: float


@dataclass(slots=True)
class BacktestResult:
    ticker: str
    signal: str
    future_return: float


def signal_for_valuation(valuation: BuffettValuation) -> str:
    if valuation.current_price <= valuation.buy_price:
        return "buy"
    if valuation.current_price >= valuation.target_price:
        return "sell"
    return "hold"


def run_backtest(cases: list[BacktestCase]) -> list[BacktestResult]:
    results: list[BacktestResult] = []
    for case in cases:
        future_return = (case.future_price - case.valuation.current_price) / case.valuation.current_price
        results.append(
            BacktestResult(
                ticker=case.valuation.ticker,
                signal=signal_for_valuation(case.valuation),
                future_return=future_return,
            )
        )
    return results
