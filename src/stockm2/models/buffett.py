from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Literal


PEBasis = Literal["average", "latest", "manual"]
DampenerMode = Literal["legacy", "fixed", "per_negative_year"]


@dataclass(slots=True)
class DataSource:
    label: str
    fields: list[str]
    url: str | None = None
    note: str | None = None


@dataclass(slots=True)
class BuffettInput:
    ticker: str
    company_name: str
    latest_eps: float
    eps_growth_history: list[float]
    pe_history: list[float]
    current_price: float
    fiscal_years: list[str] = field(default_factory=list)
    sources: list[DataSource] = field(default_factory=list)


@dataclass(slots=True)
class BuffettConfig:
    forecast_years: int = 10
    target_return: float = 0.18
    sell_return: float = 0.15
    margin_of_safety: float = 0.25
    max_eps_growth: float = 0.50
    weighted_growth: bool = True
    year_weights: list[float] = field(
        default_factory=lambda: [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5]
    )
    clip_growth: bool = True
    growth_clip_min: float = -0.50
    growth_clip_max: float = 0.50
    max_non_positive_growth_years: int = 2
    dampener_enabled: bool = True
    dampener_mode: DampenerMode = "legacy"
    legacy_max_dampener: float = 0.8
    fixed_dampener: float = 0.8
    dampener_start: float = 0.8
    dampener_reduction_per_non_positive: float = 0.1
    dampener_addback: float = 0.1
    pe_basis: PEBasis = "average"
    manual_pe: float | None = None

    @classmethod
    def legacy_defaults(cls) -> "BuffettConfig":
        return cls()


@dataclass(slots=True)
class BuffettValuation:
    ticker: str
    company_name: str
    current_price: float
    latest_eps: float
    weighted_eps_growth_history: list[float]
    clipped_eps_growth_history: list[float]
    pe_history: list[float]
    average_eps_growth: float
    average_pe: float
    selected_pe: float
    dampener: float
    adjusted_eps_growth: float
    projected_eps: float
    projected_future_price: float
    target_price: float
    buy_price: float
    sell_price: float
    current_price_gap: float | None
    accepted: bool
    rejection_reasons: list[str]
    sources: list[DataSource]
    assumptions: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _require_numeric_series(name: str, values: list[float], minimum_length: int = 1) -> list[float]:
    if len(values) < minimum_length:
        raise ValueError(f"{name} requires at least {minimum_length} values")
    normalized: list[float] = []
    for value in values:
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name} contains non-numeric value: {value!r}")
        normalized.append(float(value))
    return normalized


def apply_weighting(growth_history: list[float], config: BuffettConfig) -> list[float]:
    growth_history = _require_numeric_series("eps_growth_history", growth_history, 1)
    if not config.weighted_growth:
        return list(growth_history)
    if len(growth_history) != len(config.year_weights):
        raise ValueError("weighted legacy mode expects growth history length to match year weights")
    return [growth * weight for growth, weight in zip(growth_history, config.year_weights)]


def apply_clipping(growth_history: list[float], config: BuffettConfig) -> list[float]:
    if not config.clip_growth:
        return list(growth_history)
    return [max(config.growth_clip_min, min(config.growth_clip_max, value)) for value in growth_history]


def count_non_positive_growth_years(weighted_growth_history: list[float]) -> int:
    return len([value for value in weighted_growth_history if value <= 0])


def determine_dampener(weighted_growth_history: list[float], config: BuffettConfig) -> float:
    if not config.dampener_enabled:
        return 1.0

    if config.dampener_mode == "fixed":
        return config.fixed_dampener

    negative_years = len([value for value in weighted_growth_history if value < 0])

    if config.dampener_mode == "per_negative_year":
        dampener = config.dampener_start - (negative_years * config.dampener_reduction_per_non_positive)
        if negative_years > 0:
            dampener += config.dampener_addback
        return dampener

    dampener = config.legacy_max_dampener
    for value in weighted_growth_history:
        if value < 0:
            dampener -= 0.1
    if dampener != config.legacy_max_dampener:
        dampener += 0.1
    return dampener


def select_pe(pe_history: list[float], config: BuffettConfig) -> tuple[float, float]:
    pe_history = _require_numeric_series("pe_history", pe_history, 1)
    average_pe = mean(pe_history)
    if config.pe_basis == "latest":
        return average_pe, pe_history[-1]
    if config.pe_basis == "manual":
        if config.manual_pe is None:
            raise ValueError("manual PE basis requires manual_pe")
        return average_pe, float(config.manual_pe)
    return average_pe, average_pe


def compound_growth(initial_value: float, growth_rate: float, years: int) -> float:
    value = float(initial_value)
    for _ in range(years):
        value *= growth_rate
    return value


def evaluate_buffett_valuation(stock: BuffettInput, config: BuffettConfig | None = None) -> BuffettValuation:
    config = config or BuffettConfig.legacy_defaults()
    if not isinstance(stock.latest_eps, (int, float)):
        raise ValueError("latest_eps must be numeric")
    if not isinstance(stock.current_price, (int, float)):
        raise ValueError("current_price must be numeric")

    weighted_growth_history = apply_weighting(stock.eps_growth_history, config)
    clipped_growth_history = apply_clipping(weighted_growth_history, config)
    average_eps_growth = mean(clipped_growth_history)
    non_positive_years = count_non_positive_growth_years(weighted_growth_history)
    rejection_reasons: list[str] = []

    if stock.current_price <= 0:
        rejection_reasons.append("current_price_must_be_positive")
    if stock.latest_eps <= 0:
        rejection_reasons.append("latest_eps_must_be_positive")
    if non_positive_years > config.max_non_positive_growth_years:
        rejection_reasons.append("too_many_non_positive_growth_years")

    average_pe, selected_pe = select_pe(stock.pe_history, config)
    if selected_pe <= 0:
        rejection_reasons.append("selected_pe_must_be_positive")

    dampener = determine_dampener(weighted_growth_history, config)
    adjusted_eps_growth = average_eps_growth * dampener
    projected_eps = compound_growth(stock.latest_eps, 1 + adjusted_eps_growth, config.forecast_years)
    projected_future_price = projected_eps * selected_pe
    target_price = projected_future_price / ((1 + config.target_return) ** config.forecast_years)
    buy_price = target_price * (1 - config.margin_of_safety)
    sell_price = projected_future_price / ((1 + config.sell_return) ** config.forecast_years)

    if projected_eps <= 0:
        rejection_reasons.append("projected_eps_must_be_positive")
    if buy_price <= 0:
        rejection_reasons.append("buy_price_must_be_positive")

    current_price_gap = None if buy_price == 0 else (stock.current_price - buy_price) / buy_price
    accepted = not rejection_reasons

    return BuffettValuation(
        ticker=stock.ticker,
        company_name=stock.company_name,
        current_price=float(stock.current_price),
        latest_eps=float(stock.latest_eps),
        weighted_eps_growth_history=weighted_growth_history,
        clipped_eps_growth_history=clipped_growth_history,
        pe_history=[float(value) for value in stock.pe_history],
        average_eps_growth=average_eps_growth,
        average_pe=average_pe,
        selected_pe=selected_pe,
        dampener=dampener,
        adjusted_eps_growth=adjusted_eps_growth,
        projected_eps=projected_eps,
        projected_future_price=projected_future_price,
        target_price=target_price,
        buy_price=buy_price,
        sell_price=sell_price,
        current_price_gap=current_price_gap,
        accepted=accepted,
        rejection_reasons=rejection_reasons,
        sources=stock.sources,
        assumptions=asdict(config),
    )


def evaluate_many(stocks: list[BuffettInput], config: BuffettConfig | None = None) -> list[BuffettValuation]:
    config = config or BuffettConfig.legacy_defaults()
    return [evaluate_buffett_valuation(stock, config) for stock in stocks]
