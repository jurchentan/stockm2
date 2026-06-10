from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from stockm2.data.providers.base import FundamentalsProvider, ProviderError
from stockm2.models.buffett import BuffettInput, DataSource


class SecYahooProvider(FundamentalsProvider):
    sec_tickers_url = "https://www.sec.gov/files/company_tickers.json"
    sec_companyfacts_url = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    yahoo_chart_url = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

    eps_concepts = [
        "EarningsPerShareDiluted",
        "EarningsPerShareBasicAndDiluted",
        "IncomeLossFromContinuingOperationsPerDilutedShare",
    ]

    def __init__(self, session: requests.Session | None = None, user_agent: str | None = None):
        self.session = session or requests.Session()
        self.user_agent = user_agent or "stockm2/0.1 alex@local"
        self.session.headers.update({"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"})
        self._ticker_map: dict[str, str] | None = None

    def _get_json(self, url: str, params: dict[str, object] | None = None) -> object:
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _get_ticker_map(self) -> dict[str, str]:
        if self._ticker_map is not None:
            return self._ticker_map
        payload = self._get_json(self.sec_tickers_url)
        if not isinstance(payload, dict):
            raise ProviderError("Unexpected SEC ticker mapping response")
        ticker_map: dict[str, str] = {}
        for item in payload.values():
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker", "")).upper()
            cik = str(item.get("cik_str", "")).zfill(10)
            if ticker and cik:
                ticker_map[ticker] = cik
        self._ticker_map = ticker_map
        return ticker_map

    def _get_cik(self, ticker: str) -> str:
        cik = self._get_ticker_map().get(ticker.upper())
        if not cik:
            raise ProviderError(f"SEC CIK mapping not found for {ticker}")
        return cik

    def _extract_annual_eps(self, companyfacts: dict[str, object], years: int) -> tuple[str, list[dict[str, object]]]:
        facts = companyfacts.get("facts")
        if not isinstance(facts, dict):
            raise ProviderError("SEC companyfacts missing facts payload")
        us_gaap = facts.get("us-gaap")
        if not isinstance(us_gaap, dict):
            raise ProviderError("SEC companyfacts missing us-gaap facts")

        for concept in self.eps_concepts:
            concept_payload = us_gaap.get(concept)
            if not isinstance(concept_payload, dict):
                continue
            units = concept_payload.get("units")
            if not isinstance(units, dict):
                continue
            series = units.get("USD/shares") or units.get("USD / shares")
            if not isinstance(series, list):
                continue

            filtered: list[dict[str, object]] = []
            for item in series:
                if not isinstance(item, dict):
                    continue
                form = str(item.get("form", ""))
                fy = item.get("fy")
                value = item.get("val")
                end = item.get("end")
                filed = item.get("filed")
                frame = item.get("frame")
                if form not in {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}:
                    continue
                if fy is None or value is None or not end:
                    continue
                filtered.append(
                    {
                        "fy": int(fy),
                        "val": float(value),
                        "end": str(end),
                        "filed": str(filed or ""),
                        "frame": str(frame or ""),
                    }
                )

            deduped_by_year: dict[int, dict[str, object]] = {}
            for item in filtered:
                existing = deduped_by_year.get(item["fy"])
                if existing is None or item["filed"] > existing["filed"]:
                    deduped_by_year[item["fy"]] = item

            annual_eps = [deduped_by_year[year] for year in sorted(deduped_by_year)]
            if len(annual_eps) >= 2:
                return concept, annual_eps[-(years + 1) :]

        raise ProviderError("Not enough annual diluted EPS history in SEC companyfacts to compute annual growth")

    def _get_yahoo_chart(self, ticker: str, start_date: str) -> dict[str, object]:
        payload = self._get_json(
            self.yahoo_chart_url.format(ticker=ticker.upper()),
            {
                "interval": "1d",
                "includePrePost": "false",
                "events": "div,splits",
                "period1": int(datetime.fromisoformat(start_date).replace(tzinfo=UTC).timestamp()),
                "period2": int((datetime.now(UTC) + timedelta(days=1)).timestamp()),
            },
        )
        if not isinstance(payload, dict):
            raise ProviderError("Unexpected Yahoo chart payload")
        chart = payload.get("chart")
        if not isinstance(chart, dict):
            raise ProviderError("Yahoo chart response missing chart object")
        error = chart.get("error")
        if error:
            raise ProviderError(f"Yahoo chart error for {ticker}: {error}")
        result = chart.get("result")
        if not isinstance(result, list) or not result:
            raise ProviderError(f"Yahoo chart result missing for {ticker}")
        item = result[0]
        if not isinstance(item, dict):
            raise ProviderError(f"Yahoo chart result malformed for {ticker}")
        return item

    @staticmethod
    def _build_price_series(chart: dict[str, object]) -> tuple[float, dict[str, float]]:
        meta = chart.get("meta")
        timestamps = chart.get("timestamp")
        indicators = chart.get("indicators")
        if not isinstance(meta, dict) or not isinstance(timestamps, list) or not isinstance(indicators, dict):
            raise ProviderError("Yahoo chart payload missing meta, timestamps, or indicators")
        quote = indicators.get("quote")
        if not isinstance(quote, list) or not quote or not isinstance(quote[0], dict):
            raise ProviderError("Yahoo chart payload missing quote series")
        closes = quote[0].get("close")
        if not isinstance(closes, list):
            raise ProviderError("Yahoo chart payload missing close prices")

        current_price = meta.get("regularMarketPrice") or meta.get("previousClose")
        if not isinstance(current_price, (int, float)):
            raise ProviderError("Yahoo chart payload missing current price")

        price_by_date: dict[str, float] = {}
        for timestamp, close in zip(timestamps, closes):
            if close is None:
                continue
            date = datetime.fromtimestamp(int(timestamp), tz=UTC).date().isoformat()
            price_by_date[date] = float(close)
        return float(current_price), price_by_date

    @staticmethod
    def _latest_price_on_or_before(target_date: str, price_by_date: dict[str, float]) -> float:
        candidates = [date for date in price_by_date if date <= target_date]
        if not candidates:
            raise ProviderError(f"No Yahoo historical price available on or before {target_date}")
        return price_by_date[max(candidates)]

    def get_annual_buffett_input(self, ticker: str, years: int) -> BuffettInput:
        cik = self._get_cik(ticker)
        companyfacts = self._get_json(self.sec_companyfacts_url.format(cik=cik))
        if not isinstance(companyfacts, dict):
            raise ProviderError(f"Unexpected SEC companyfacts payload for {ticker}")

        eps_concept, annual_eps = self._extract_annual_eps(companyfacts, years)
        chart = self._get_yahoo_chart(ticker, annual_eps[0]["end"])
        current_price, price_by_date = self._build_price_series(chart)

        latest_eps = float(annual_eps[-1]["val"])
        eps_growth_history: list[float] = []
        pe_history: list[float] = []
        fiscal_years: list[str] = []

        for previous, current in zip(annual_eps[:-1], annual_eps[1:]):
            previous_eps = float(previous["val"])
            current_eps = float(current["val"])
            if previous_eps == 0:
                raise ProviderError(f"Cannot compute EPS growth from zero SEC EPS for {ticker}")
            eps_growth_history.append((current_eps - previous_eps) / abs(previous_eps))
            fiscal_years.append(str(current["fy"]))
            year_end_price = self._latest_price_on_or_before(str(current["end"]), price_by_date)
            pe_history.append(year_end_price / current_eps)

        if not eps_growth_history or not pe_history:
            raise ProviderError(f"Not enough SEC/Yahoo history to build a Buffett input for {ticker}")

        entity_name = companyfacts.get("entityName")
        company_name = str(entity_name or ticker.upper())
        return BuffettInput(
            ticker=ticker.upper(),
            company_name=company_name,
            latest_eps=latest_eps,
            eps_growth_history=eps_growth_history,
            pe_history=pe_history,
            current_price=current_price,
            fiscal_years=fiscal_years,
            sources=[
                DataSource(
                    label="SEC Companyfacts ticker mapping",
                    fields=["ticker", "company_name"],
                    url="https://www.sec.gov/files/company_tickers.json",
                    note="Ticker-to-CIK mapping from SEC.",
                ),
                DataSource(
                    label="SEC Companyfacts annual EPS",
                    fields=["latest_eps", "eps_growth_history"],
                    url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                    note=f"EPS growth derived from annual SEC XBRL concept `{eps_concept}`.",
                ),
                DataSource(
                    label="Yahoo Finance chart API",
                    fields=["current_price", "pe_history"],
                    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}",
                    note="Historical PE reconstructed from Yahoo daily closes and SEC annual EPS.",
                ),
            ],
        )
