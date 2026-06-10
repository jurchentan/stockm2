from __future__ import annotations

import os

import requests

from stockm2.data.providers.base import FundamentalsProvider, ProviderError
from stockm2.models.buffett import BuffettInput, DataSource


class FMPProvider(FundamentalsProvider):
    base_url = "https://financialmodelingprep.com/stable"

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ProviderError("FMP_API_KEY is required for the FMP provider")
        self.session = session or requests.Session()

    def _get(self, path: str, params: dict[str, object]) -> list[dict[str, object]] | dict[str, object]:
        response = self.session.get(f"{self.base_url}{path}", params={**params, "apikey": self.api_key}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, (list, dict)):
            raise ProviderError(f"Unexpected FMP response for {path}: {payload!r}")
        return payload

    @staticmethod
    def _as_list(payload: list[dict[str, object]] | dict[str, object]) -> list[dict[str, object]]:
        if isinstance(payload, list):
            return payload
        return [payload]

    def get_annual_buffett_input(self, ticker: str, years: int) -> BuffettInput:
        quote = self._as_list(self._get("/quote", {"symbol": ticker}))
        income = self._as_list(self._get("/income-statement", {"symbol": ticker, "period": "annual", "limit": years + 1}))
        prices = self._as_list(self._get("/historical-price-eod/full", {"symbol": ticker}))

        if not income or not quote:
            raise ProviderError(f"Insufficient FMP data for {ticker}")

        annual_income = list(reversed(income[: years + 1]))
        eps_series = [item.get("epsdiluted") or item.get("eps") for item in annual_income]
        if any(value in (None, 0) for value in eps_series):
            raise ProviderError(f"Missing annual EPS history for {ticker}")

        fiscal_years = [str(item.get("calendarYear")) for item in annual_income[1:]]
        latest_eps = float(eps_series[-1])
        eps_growth_history = []
        for prev_eps, next_eps in zip(eps_series[:-1], eps_series[1:]):
            prev = float(prev_eps)
            curr = float(next_eps)
            if prev == 0:
                raise ProviderError(f"Cannot compute EPS growth from zero EPS for {ticker}")
            eps_growth_history.append((curr - prev) / abs(prev))

        historical_price_items = prices
        price_by_year: dict[str, float] = {}
        for item in historical_price_items:
            date = str(item.get("date", ""))
            close = item.get("close")
            if not date or close is None:
                continue
            price_by_year[date[:4]] = float(close)

        pe_history = []
        for year, eps in zip(fiscal_years, eps_series[1:]):
            year_close = price_by_year.get(year)
            if year_close is None:
                continue
            pe_history.append(year_close / float(eps))

        if not eps_growth_history or not pe_history:
            raise ProviderError(f"Not enough annual history to build a Buffett input for {ticker}")

        return BuffettInput(
            ticker=ticker.upper(),
            company_name=str(quote[0].get("companyName") or ticker.upper()),
            latest_eps=latest_eps,
            eps_growth_history=eps_growth_history,
            pe_history=pe_history,
            current_price=float(quote[0]["price"]),
            fiscal_years=fiscal_years,
            sources=[
                DataSource(
                    label="Financial Modeling Prep quote API",
                    fields=["company_name"],
                    url="https://site.financialmodelingprep.com/developer/docs/stable/quote",
                    note="Company name and current price source.",
                ),
                DataSource(
                    label="Financial Modeling Prep income statement API",
                    fields=["latest_eps", "eps_growth_history"],
                    url=f"https://site.financialmodelingprep.com/developer/docs/stable/income-statements",
                    note="EPS growth is derived from annual diluted EPS values from the income statement response.",
                ),
                DataSource(
                    label="Financial Modeling Prep historical prices API",
                    fields=["pe_history"],
                    url=f"https://site.financialmodelingprep.com/developer/docs/stable/historical-price-eod-full",
                    note="Historical PE is reconstructed from annual EPS and historical close prices.",
                ),
            ],
        )
