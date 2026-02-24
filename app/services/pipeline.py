from typing import Protocol

from app.config import get_settings
from app.models import Job, JobStatus
from app.services.asr.base import ASRProvider
from app.services.asr.faster_whisper_provider import FasterWhisperASR
from app.services.summarizer import OpenAIMapReduceSummarizer
from app.storage.local import LocalJobStore


def process_job(job_id: str) -> None:
    settings = get_settings()
    store = LocalJobStore(settings.data_dir)
    asr = FasterWhisperASR(settings)
    summarizer = OpenAIMapReduceSummarizer(settings)
    process_job_with_dependencies(job_id, store, asr, summarizer)


class SummarizerProvider(Protocol):
    def summarize(self, transcript: str) -> tuple[dict, str]: ...


def process_job_with_dependencies(
    job_id: str,
    store: LocalJobStore,
    asr: ASRProvider,
    summarizer: SummarizerProvider,
) -> None:
    job = store.get_job(job_id)
    if not job:
        return

    try:
        _set_progress(store, job, "Starting job processing")
        job.status = JobStatus.processing
        job.error = None
        store.update_job(job)

        _set_progress(store, job, "Loading audio")
        audio_path = store.job_audio_path(job.id)
        if not audio_path:
            raise RuntimeError("Audio file is missing")

        _set_progress(store, job, "Transcribing audio with faster-whisper")
        transcription = asr.transcribe(audio_path)
        transcript_path = store.save_transcript(
            job.id,
            transcription.transcript_text,
            transcription.vtt_text,
        )

        _set_progress(store, job, "Generating summary")
        summary, markdown = summarizer.summarize(transcription.transcript_text)
        summary_path, _ = store.save_summary(job.id, summary, markdown)

        job.transcript_path = str(transcript_path)
        job.summary_path = str(summary_path)
        job.status = JobStatus.done
        job.status_message = "Completed"
        job.error = None
        store.update_job(job)
    except Exception as exc:  # noqa: BLE001
        job.status = JobStatus.failed
        job.status_message = "Failed"
        job.error = str(exc)
        store.update_job(job)


def _set_progress(store: LocalJobStore, job: Job, message: str) -> None:
    job.status_message = message
    store.update_job(job)
