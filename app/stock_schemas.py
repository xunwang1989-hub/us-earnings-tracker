from datetime import date, datetime

from pydantic import BaseModel, Field


class EarningsEvent(BaseModel):
    symbol: str
    earnings_date: date
    company_name: str | None = None
    time: str | None = None


class PriceBar(BaseModel):
    date: date
    close: float


class HistoricalDropItem(BaseModel):
    symbol: str
    earnings_date: date
    baseline_date: date
    baseline_close: float
    lowest_date: date
    lowest_close: float
    drop_pct: float


class UpcomingEarningsItem(BaseModel):
    symbol: str
    earnings_date: date
    company_name: str | None = None
    time: str | None = None


class StockTrackerResponse(BaseModel):
    generated_at: datetime
    data_source: str
    source_window_from: date
    source_window_to: date
    lookback_days: int
    future_days: int
    drop_threshold_pct: float = Field(description="Negative move threshold after earnings")
    reaction_days: int
    analyzed_events: int
    historical_drops: list[HistoricalDropItem]
    upcoming_earnings: list[UpcomingEarningsItem]
    warnings: list[str] = Field(default_factory=list)
