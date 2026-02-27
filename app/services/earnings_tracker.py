from datetime import date, datetime, timedelta, timezone

from app.stock_schemas import HistoricalDropItem, StockTrackerResponse, UpcomingEarningsItem
from app.services.market_data import MarketDataClient


class EarningsTrackerService:
    def __init__(self, market_data_client: MarketDataClient):
        self.market_data_client = market_data_client

    def analyze(
        self,
        lookback_days: int,
        future_days: int,
        drop_threshold_pct: float,
        reaction_days: int,
        max_events: int = 100,
        today: date | None = None,
        data_source: str = "unknown",
    ) -> StockTrackerResponse:
        reference_day = today or date.today()
        lookback_start = reference_day - timedelta(days=lookback_days)
        upcoming_end = reference_day + timedelta(days=future_days)

        historical_events = self.market_data_client.fetch_earnings_calendar(
            lookback_start, reference_day, historical=True
        )
        upcoming_events = self.market_data_client.fetch_earnings_calendar(
            reference_day + timedelta(days=1), upcoming_end, historical=False
        )

        deduped_historical = self._dedupe_events(historical_events)
        warnings: list[str] = []
        if len(deduped_historical) > max_events:
            warnings.append(
                f"Historical events are limited to the first {max_events} rows to control API usage."
            )
            deduped_historical = deduped_historical[:max_events]

        drop_floor = -abs(drop_threshold_pct)
        historical_drops: list[HistoricalDropItem] = []

        for event in deduped_historical:
            end_date = event.earnings_date + timedelta(days=max(reaction_days * 3, reaction_days + 7))
            prices = self.market_data_client.fetch_price_history(event.symbol, event.earnings_date, end_date)
            if len(prices) < 2:
                continue

            baseline = next((bar for bar in prices if bar.date >= event.earnings_date), None)
            if baseline is None or baseline.close <= 0:
                continue

            reaction_window = [bar for bar in prices if bar.date > baseline.date][:reaction_days]
            if not reaction_window:
                continue

            lowest = min(reaction_window, key=lambda bar: bar.close)
            drop_pct = round(((lowest.close - baseline.close) / baseline.close) * 100.0, 2)
            if drop_pct > drop_floor:
                continue

            historical_drops.append(
                HistoricalDropItem(
                    symbol=event.symbol,
                    earnings_date=event.earnings_date,
                    baseline_date=baseline.date,
                    baseline_close=round(baseline.close, 4),
                    lowest_date=lowest.date,
                    lowest_close=round(lowest.close, 4),
                    drop_pct=drop_pct,
                )
            )

        historical_drops.sort(key=lambda item: item.drop_pct)

        deduped_upcoming = self._dedupe_events(upcoming_events)
        upcoming_rows = [
            UpcomingEarningsItem(
                symbol=event.symbol,
                earnings_date=event.earnings_date,
                company_name=event.company_name,
                time=event.time,
            )
            for event in sorted(deduped_upcoming, key=lambda item: (item.earnings_date, item.symbol))
        ]

        return StockTrackerResponse(
            generated_at=datetime.now(timezone.utc),
            data_source=data_source,
            source_window_from=lookback_start,
            source_window_to=upcoming_end,
            lookback_days=lookback_days,
            future_days=future_days,
            drop_threshold_pct=abs(drop_threshold_pct),
            reaction_days=reaction_days,
            analyzed_events=len(deduped_historical),
            historical_drops=historical_drops,
            upcoming_earnings=upcoming_rows,
            warnings=warnings,
        )

    @staticmethod
    def _dedupe_events(events: list) -> list:
        unique: dict[tuple[str, date], object] = {}
        for event in events:
            unique[(event.symbol, event.earnings_date)] = event
        return sorted(unique.values(), key=lambda item: (item.earnings_date, item.symbol), reverse=True)
