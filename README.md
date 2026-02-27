# AI Tools MVP (Podcast + Earnings Tracker)

FastAPI app with two tools:
- Podcast Summarizer: upload audio, generate transcript and structured summary.
- US Earnings Tracker Web: find stocks that dropped after earnings and list upcoming earnings in the next 1-2 months.

## Features
- `POST /jobs` multipart audio upload (`.mp3`, `.m4a`, `.wav`)
- Background processing per job
- Local data persistence under `data/jobs/<job_id>/`
- `GET /jobs/{id}` for status and metadata
- `GET /jobs/{id}/transcript` for transcript text
- `GET /jobs/{id}/summary` for structured JSON + markdown summary
- Transcript artifacts include `transcript.txt` and `transcript.vtt` (VTT optional but generated when segment timing exists)
- `GET /stocks` web UI for earnings tracking
- `GET /stocks/analyze` API to return:
  - historical earnings events with post-earnings drop >= threshold
  - upcoming earnings events in future date window

## Job Model
```json
{
  "id": "string",
  "status": "queued | processing | done | failed",
  "created_at": "ISO datetime",
  "input_type": "upload",
  "input_source": "filename",
  "transcript_path": "string | null",
  "summary_path": "string | null",
  "status_message": "string | null",
  "error": "string | null"
}
```

## Quickstart
1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```
3. Configure environment:
   ```bash
   cp .env.example .env
   ```
   Set `OPENAI_API_KEY` for podcast summarization.
   Stock tracking is locked to FMP:
   - `MARKET_DATA_PROVIDER=fmp`
   - `FMP_API_KEY=<your_key>`
4. Run API:
   ```bash
   uvicorn app.main:app --reload
   ```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) for a minimal landing page.
Open [http://127.0.0.1:8000/stocks](http://127.0.0.1:8000/stocks) for the stock tracker web page.

## Sample Run
Create a job:
```bash
curl -X POST "http://127.0.0.1:8000/jobs" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/absolute/path/to/podcast.wav" \
  -F "podcast_url=https://example.com/episode"
```

Fetch job metadata:
```bash
curl "http://127.0.0.1:8000/jobs/<job_id>"
```

Fetch transcript:
```bash
curl "http://127.0.0.1:8000/jobs/<job_id>/transcript"
```

Fetch summary:
```bash
curl "http://127.0.0.1:8000/jobs/<job_id>/summary"
```

Stock tracker query:
```bash
curl "http://127.0.0.1:8000/stocks/analyze?lookback_days=30&future_days=60&drop_threshold_pct=10&reaction_days=5"
```

## Development Checks
Run before finalizing changes:
```bash
ruff format .
ruff check .
pytest
```

## Notes
- Storage is filesystem-backed for MVP and isolated in `app/storage/local.py` to simplify future S3 migration.
- ASR provider is separated under `app/services/asr/` so cloud ASR can be swapped in later.
- For best audio compatibility, install `ffmpeg`. The transcriber will convert non-wav inputs to wav when `ffmpeg` is available.
- If `ffmpeg` is unavailable, the app attempts direct transcription using the original upload format.
- Stock tracking data provider:
  - FMP only (`/stable/earnings-calendar` + `/stable/historical-price-eod/light`)
