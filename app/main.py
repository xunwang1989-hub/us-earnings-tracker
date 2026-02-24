from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.jobs import router as jobs_router
from app.api.stocks import router as stocks_router
from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.include_router(jobs_router)
app.include_router(stocks_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
<!doctype html>
<html>
  <head>
    <title>Podcast Summarizer MVP</title>
    <style>
      body { font-family: sans-serif; max-width: 720px; margin: 2rem auto; line-height: 1.4; }
      code { background: #f4f4f4; padding: 0.1rem 0.3rem; border-radius: 4px; }
    </style>
  </head>
  <body>
    <h1>Podcast Summarizer MVP</h1>
    <p>Use <code>POST /jobs</code> to upload an audio file, then poll <code>GET /jobs/{id}</code>.</p>
    <p>Retrieve outputs with <code>GET /jobs/{id}/transcript</code> and <code>GET /jobs/{id}/summary</code>.</p>
    <p>Stock tracker UI: <a href="/stocks">/stocks</a>.</p>
  </body>
</html>
"""
