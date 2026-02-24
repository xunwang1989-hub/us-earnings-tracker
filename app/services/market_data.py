import json
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.stock_schemas import EarningsEvent, PriceBar


class MarketDataClient(Protocol):
    def fetch_earnings_calendar(self, start_date: date, end_date: date, historical: bool) -> list[EarningsEvent]:
        ...

    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> list[PriceBar]:
        ...


@dataclass
class FMPClient:
    api_key: str
    base_url: str = "https://financialmodelingprep.com"
    timeout_seconds: float = 20.0

    def _get_json(self, path: str, params: dict[str, str]) -> list[dict] | dict:
        query = dict(params)
        query["apikey"] = self.api_key
        encoded = urlencode(query)
        url = f"{self.base_url.rstrip('/')}{path}?{encoded}"
        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:  # noqa: S310
                payload = response.read().decode("utf-8")
            return json.loads(payload)
        except (URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Unable to read market data from FMP endpoint: {path}. Cause: {exc}"
            ) from exc

    def fetch_earnings_calendar(self, start_date: date, end_date: date, historical: bool) -> list[EarningsEvent]:
        # FMP moved legacy /api/v3 calendar endpoints to /stable.
        # We use the same stable endpoint for both historical and upcoming windows.
        payload = self._get_json(
            "/stable/earnings-calendar",
            {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
        )
        if not isinstance(payload, list):
            return []

        events: list[EarningsEvent] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "").upper().strip()
            date_text = str(row.get("date") or row.get("publishedDate") or "").strip()
            if not symbol or not date_text:
                continue
            try:
                events.append(
                    EarningsEvent(
                        symbol=symbol,
                        earnings_date=date.fromisoformat(date_text),
                        company_name=row.get("company") or row.get("name") or row.get("companyName"),
                        time=row.get("time"),
                    )
                )
            except ValueError:
                continue
        return events

    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> list[PriceBar]:
        payload = self._get_json(
            "/stable/historical-price-eod/light",
            {
                "symbol": symbol,
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
        )
        if not isinstance(payload, list):
            return []

        prices: list[PriceBar] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            day_text = str(row.get("date") or "").strip()
            close = row.get("close") or row.get("price")
            if not day_text or close is None:
                continue
            try:
                prices.append(PriceBar(date=date.fromisoformat(day_text), close=float(close)))
            except (TypeError, ValueError):
                continue

        prices.sort(key=lambda item: item.date)
        return prices
