from datetime import date

from app.services.earnings_tracker import EarningsTrackerService
from app.stock_schemas import EarningsEvent, PriceBar


class FakeMarketDataClient:
    def fetch_earnings_calendar(self, start_date: date, end_date: date, historical: bool) -> list[EarningsEvent]:
        if historical:
            return [
                EarningsEvent(symbol="AAPL", earnings_date=date(2026, 1, 28), company_name="Apple"),
                EarningsEvent(symbol="MSFT", earnings_date=date(2026, 1, 29), company_name="Microsoft"),
            ]
        return [
            EarningsEvent(symbol="NVDA", earnings_date=date(2026, 3, 20), company_name="NVIDIA"),
        ]

    def fetch_price_history(self, symbol: str, start_date: date, end_date: date) -> list[PriceBar]:
        if symbol == "AAPL":
            return [
                PriceBar(date=date(2026, 1, 28), close=100.0),
                PriceBar(date=date(2026, 1, 29), close=95.0),
                PriceBar(date=date(2026, 1, 30), close=88.0),
                PriceBar(date=date(2026, 2, 2), close=90.0),
            ]

        return [
            PriceBar(date=date(2026, 1, 29), close=100.0),
            PriceBar(date=date(2026, 1, 30), close=99.0),
            PriceBar(date=date(2026, 2, 2), close=98.0),
        ]


def test_analyze_finds_drop_and_upcoming() -> None:
    service = EarningsTrackerService(FakeMarketDataClient())

    result = service.analyze(
        lookback_days=30,
        future_days=60,
        drop_threshold_pct=10.0,
        reaction_days=3,
        today=date(2026, 2, 10),
    )

    assert result.analyzed_events == 2
    assert len(result.historical_drops) == 1
    assert result.historical_drops[0].symbol == "AAPL"
    assert result.historical_drops[0].drop_pct == -12.0
    assert len(result.upcoming_earnings) == 1
    assert result.upcoming_earnings[0].symbol == "NVDA"
