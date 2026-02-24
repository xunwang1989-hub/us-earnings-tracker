from datetime import date, datetime, timezone

from app.storage.stock_cache import DailyStockCache
from app.stock_schemas import StockTrackerResponse


def test_daily_stock_cache_roundtrip(tmp_path) -> None:
    cache = DailyStockCache(tmp_path)
    day = date(2026, 2, 24)
    payload = StockTrackerResponse(
        generated_at=datetime(2026, 2, 24, tzinfo=timezone.utc),
        lookback_days=7,
        future_days=14,
        drop_threshold_pct=10.0,
        reaction_days=3,
        analyzed_events=0,
        historical_drops=[],
        upcoming_earnings=[],
        warnings=[],
    )

    cache.write(payload, day)
    loaded = cache.read(day)

    assert loaded is not None
    assert loaded.generated_at == payload.generated_at
    assert loaded.lookback_days == 7
