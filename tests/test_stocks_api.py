from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.stock_schemas import StockTrackerResponse


class StubService:
    def analyze(
        self,
        lookback_days: int,
        future_days: int,
        drop_threshold_pct: float,
        reaction_days: int,
        max_events: int,
    ) -> StockTrackerResponse:
        return StockTrackerResponse(
            generated_at=datetime(2026, 2, 24, tzinfo=timezone.utc),
            data_source="fmp:/stable/earnings-calendar",
            source_window_from=date(2026, 1, 25),
            source_window_to=date(2026, 4, 9),
            lookback_days=lookback_days,
            future_days=future_days,
            drop_threshold_pct=drop_threshold_pct,
            reaction_days=reaction_days,
            analyzed_events=1,
            historical_drops=[
                {
                    "symbol": "AAPL",
                    "earnings_date": date(2026, 1, 28),
                    "baseline_date": date(2026, 1, 28),
                    "baseline_close": 100.0,
                    "lowest_date": date(2026, 1, 30),
                    "lowest_close": 89.0,
                    "drop_pct": -11.0,
                }
            ],
            upcoming_earnings=[
                {
                    "symbol": "NVDA",
                    "earnings_date": date(2026, 3, 20),
                    "company_name": "NVIDIA",
                    "time": "amc",
                }
            ],
            warnings=[],
        )


def test_stocks_page_renders() -> None:
    client = TestClient(app)
    response = client.get("/stocks")
    assert response.status_code == 200
    assert "US Earnings Tracker" in response.text


def test_stocks_analyze_endpoint(monkeypatch) -> None:
    from app.api import stocks

    monkeypatch.setattr(stocks, "_tracker_service", lambda: StubService())

    client = TestClient(app)
    response = client.get(
        "/stocks/analyze",
        params={
            "lookback_days": 30,
            "future_days": 45,
            "drop_threshold_pct": 10,
            "reaction_days": 5,
            "max_events": 100,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analyzed_events"] == 1
    assert payload["historical_drops"][0]["symbol"] == "AAPL"
    assert payload["upcoming_earnings"][0]["symbol"] == "NVDA"
