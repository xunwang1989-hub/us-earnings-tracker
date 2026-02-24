from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.models import Job
from app.schemas import JobCreateResponse, SummaryResponse
from app.services.pipeline import process_job
from app.storage.local import LocalJobStore

router = APIRouter(prefix="/jobs", tags=["jobs"])

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav"}


@router.post("", response_model=JobCreateResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    podcast_url: str | None = Form(default=None),
) -> JobCreateResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    settings = get_settings()
    store = LocalJobStore(settings.data_dir)

    job_id = str(uuid4())
    source = file.filename or "uploaded_file"
    if podcast_url:
        source = f"{source} | {podcast_url}"
    job = Job.new(job_id=job_id, input_type="upload", input_source=source)

    try:
        store.create_job(job)
    except FileExistsError as exc:
        raise HTTPException(status_code=500, detail="Job creation collision") from exc

    store.save_audio(job.id, file.filename or "input", payload)
    background_tasks.add_task(process_job, job.id)

    return JobCreateResponse(id=job.id, status=job.status.value)


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    store = LocalJobStore(get_settings().data_dir)
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/transcript", response_class=PlainTextResponse)
def get_transcript(job_id: str) -> str:
    store = LocalJobStore(get_settings().data_dir)
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    transcript = store.read_transcript(job_id)
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not available")
    return transcript


@router.get("/{job_id}/summary", response_model=SummaryResponse)
def get_summary(job_id: str) -> SummaryResponse:
    store = LocalJobStore(get_settings().data_dir)
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    payload = store.read_summary(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Summary not available")

    summary, markdown = payload
    return SummaryResponse(job=job, summary=summary, markdown=markdown)
