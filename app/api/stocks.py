from datetime import datetime, timezone

from fastapi import APIRouter, Form, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.services.earnings_tracker import EarningsTrackerService
from app.services.market_data import FMPClient, YahooClient
from app.storage.stock_cache import DailyStockCache
from app.stock_schemas import StockTrackerResponse

router = APIRouter(prefix="/stocks", tags=["stocks"])


def _tracker_service() -> EarningsTrackerService:
    settings = get_settings()
    provider = settings.market_data_provider.lower().strip()

    if provider == "fmp":
        if not settings.fmp_api_key:
            raise HTTPException(
                status_code=503,
                detail="FMP_API_KEY is not configured. Add it in your .env file before using provider=fmp.",
            )
        client = FMPClient(
            api_key=settings.fmp_api_key,
            base_url=settings.fmp_base_url,
            timeout_seconds=settings.fmp_timeout_seconds,
        )
    elif provider == "yahoo":
        symbols = [
            item.strip().upper()
            for item in settings.yahoo_universe_symbols.split(",")
            if item.strip()
        ]
        if not symbols:
            raise HTTPException(
                status_code=503,
                detail="YAHOO_UNIVERSE_SYMBOLS is empty. Add at least one ticker symbol.",
            )
        client = YahooClient(universe_symbols=symbols)
    else:
        raise HTTPException(
            status_code=503,
            detail="Unsupported MARKET_DATA_PROVIDER. Use 'yahoo' or 'fmp'.",
        )

    return EarningsTrackerService(client)


@router.get("", response_class=HTMLResponse)
def stocks_home() -> str:
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Earnings Tracker</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1100px; margin: 24px auto; padding: 0 12px; line-height: 1.4; }
      h1 { margin-bottom: 0.5rem; }
      .grid { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 10px; margin: 16px 0; }
      .field { display: flex; flex-direction: column; }
      label { font-size: 0.9rem; color: #2f3c4a; }
      input { border: 1px solid #cad4df; border-radius: 6px; padding: 8px; margin-top: 4px; }
      button { background: #0b63ce; color: #fff; border: 0; border-radius: 6px; padding: 10px 16px; cursor: pointer; }
      button:disabled { opacity: 0.6; cursor: wait; }
      table { border-collapse: collapse; width: 100%; margin-top: 10px; }
      th, td { border: 1px solid #e3e8ef; padding: 8px; text-align: left; font-size: 0.9rem; }
      th { background: #f5f8fc; }
      .section { margin-top: 24px; }
      .warn { color: #8d5d00; background: #fff7e5; border: 1px solid #f4dda8; padding: 8px; border-radius: 6px; margin-top: 10px; }
      .muted { color: #5d6b7a; font-size: 0.9rem; }
      @media (max-width: 860px) { .grid { grid-template-columns: repeat(2, minmax(140px, 1fr)); } }
    </style>
  </head>
  <body>
    <h1>US Earnings Tracker</h1>
    <p class="muted">Find U.S. stocks that dropped beyond a threshold after earnings, and view upcoming earnings for the next 1-2 months.</p>

    <form id="tracker-form">
      <div class="grid">
        <div class="field">
          <label for="lookback_days">Lookback Days</label>
          <input id="lookback_days" name="lookback_days" type="number" min="7" max="120" value="30" required />
        </div>
        <div class="field">
          <label for="future_days">Future Window (Days)</label>
          <input id="future_days" name="future_days" type="number" min="7" max="90" value="60" required />
        </div>
        <div class="field">
          <label for="drop_threshold_pct">Drop Threshold (%)</label>
          <input id="drop_threshold_pct" name="drop_threshold_pct" type="number" min="1" max="40" value="10" step="0.1" required />
        </div>
        <div class="field">
          <label for="reaction_days">Post-Earnings Trading Days</label>
          <input id="reaction_days" name="reaction_days" type="number" min="1" max="20" value="5" required />
        </div>
      </div>
      <button id="run-button" type="submit">Run Scan</button>
    </form>

    <div id="meta" class="section"></div>
    <div id="warnings"></div>

    <div class="section">
      <h2>Post-Earnings Drops Beyond Threshold</h2>
      <table id="drop-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Earnings Date</th>
            <th>Baseline Date</th>
            <th>Baseline Close</th>
            <th>Lowest Date</th>
            <th>Lowest Close</th>
            <th>Drop %</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>

    <div class="section">
      <h2>Upcoming Earnings Calendar</h2>
      <table id="upcoming-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Date</th>
            <th>Company</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>

    <script>
      const form = document.getElementById('tracker-form');
      const runButton = document.getElementById('run-button');

      function fillTableBody(tableId, rows, renderer) {
        const tbody = document.querySelector(`#${tableId} tbody`);
        tbody.innerHTML = rows.map(renderer).join('');
      }

      function td(v) { return `<td>${v ?? ''}</td>`; }

      async function runTracker(params) {
        const query = new URLSearchParams(params);
        const response = await fetch(`/stocks/analyze?${query.toString()}`);
        const contentType = response.headers.get('content-type') || '';
        const payload = contentType.includes('application/json')
          ? await response.json()
          : { detail: await response.text() };

        if (!response.ok) {
          throw new Error(payload.detail || 'Request failed');
        }

        document.getElementById('meta').innerHTML = `<p>Generated At: ${payload.generated_at} | Historical Events Analyzed: ${payload.analyzed_events}</p>`;

        const warnings = document.getElementById('warnings');
        warnings.innerHTML = (payload.warnings || []).map((item) => `<p class='warn'>${item}</p>`).join('');

        fillTableBody('drop-table', payload.historical_drops, (item) => `<tr>${td(item.symbol)}${td(item.earnings_date)}${td(item.baseline_date)}${td(item.baseline_close)}${td(item.lowest_date)}${td(item.lowest_close)}${td(item.drop_pct)}</tr>`);

        fillTableBody('upcoming-table', payload.upcoming_earnings, (item) => `<tr>${td(item.symbol)}${td(item.earnings_date)}${td(item.company_name)}${td(item.time)}</tr>`);
      }

      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        runButton.disabled = true;
        runButton.textContent = 'Running...';

        const formData = new FormData(form);
        const params = {
          lookback_days: formData.get('lookback_days'),
          future_days: formData.get('future_days'),
          drop_threshold_pct: formData.get('drop_threshold_pct'),
          reaction_days: formData.get('reaction_days'),
        };

        try {
          await runTracker(params);
        } catch (error) {
          document.getElementById('meta').innerHTML = `<p class='warn'>${error.message}</p>`;
        } finally {
          runButton.disabled = false;
          runButton.textContent = 'Run Scan';
        }
      });
    </script>
  </body>
</html>
"""


@router.get("/analyze", response_model=StockTrackerResponse)
def analyze_stocks(
    lookback_days: int = Query(default=30, ge=7, le=120),
    future_days: int = Query(default=60, ge=7, le=90),
    drop_threshold_pct: float = Query(default=10.0, ge=1.0, le=40.0),
    reaction_days: int = Query(default=5, ge=1, le=20),
    max_events: int = Query(default=100, ge=10, le=300),
    use_cache: bool = Query(default=True),
    force_refresh: bool = Query(default=False),
) -> StockTrackerResponse:
    today = datetime.now(timezone.utc).date()
    cache = DailyStockCache(get_settings().data_dir)
    if use_cache and not force_refresh:
        cached = cache.read(today)
        if cached is not None:
            return cached

    service = _tracker_service()
    try:
        result = service.analyze(
            lookback_days=lookback_days,
            future_days=future_days,
            drop_threshold_pct=drop_threshold_pct,
            reaction_days=reaction_days,
            max_events=max_events,
        )
        if use_cache:
            cache.write(result, today)
        return result
    except RuntimeError as exc:
        if use_cache:
            cached = cache.read(today)
            if cached is not None:
                cached.warnings.append("External provider failed; returned cached result for today.")
                return cached
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/analyze", response_model=StockTrackerResponse)
def analyze_stocks_form(
    lookback_days: int = Form(default=30),
    future_days: int = Form(default=60),
    drop_threshold_pct: float = Form(default=10.0),
    reaction_days: int = Form(default=5),
    max_events: int = Form(default=100),
    use_cache: bool = Form(default=True),
    force_refresh: bool = Form(default=False),
) -> StockTrackerResponse:
    return analyze_stocks(
        lookback_days=lookback_days,
        future_days=future_days,
        drop_threshold_pct=drop_threshold_pct,
        reaction_days=reaction_days,
        max_events=max_events,
        use_cache=use_cache,
        force_refresh=force_refresh,
    )
