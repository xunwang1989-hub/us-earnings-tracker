import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.stock_schemas import StockTrackerResponse


class DailyStockCache:
    def __init__(self, data_dir: Path):
        self.cache_dir = data_dir / "stock_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, day: date) -> Path:
        return self.cache_dir / f"{day.isoformat()}.json"

    def read(self, day: date) -> StockTrackerResponse | None:
        path = self._cache_path(day)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return StockTrackerResponse.model_validate(payload)

    def write(self, response: StockTrackerResponse, day: date | None = None) -> Path:
        cache_day = day or datetime.now(timezone.utc).date()
        path = self._cache_path(cache_day)
        path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        return path
