from __future__ import annotations

import json
from pathlib import Path

from stockm2.data.providers.base import FundamentalsProvider, ProviderError
from stockm2.models.buffett import BuffettInput, DataSource


class FixtureProvider(FundamentalsProvider):
    def __init__(self, fixture_path: str | Path):
        self.fixture_path = Path(fixture_path)
        payload = json.loads(self.fixture_path.read_text())
        self._stocks = {item["ticker"].upper(): item for item in payload["stocks"]}

    def get_annual_buffett_input(self, ticker: str, years: int) -> BuffettInput:
        item = self._stocks.get(ticker.upper())
        if item is None:
            raise ProviderError(f"Ticker {ticker} not found in fixture {self.fixture_path}")
        return BuffettInput(
            ticker=item["ticker"],
            company_name=item["company_name"],
            latest_eps=item["latest_eps"],
            eps_growth_history=item["eps_growth_history"][:years],
            pe_history=item["pe_history"][:years],
            current_price=item["current_price"],
            fiscal_years=item.get("fiscal_years", [])[:years],
            sources=item.get(
                "sources",
                [
                    DataSource(
                        label="Local fixture",
                        fields=["latest_eps", "eps_growth_history", "pe_history", "current_price"],
                        url=self.fixture_path.resolve().as_uri(),
                        note="Fixture-backed demo data from this repository.",
                    )
                ],
            ),
        )
