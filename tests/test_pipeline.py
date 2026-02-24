from pathlib import Path

from app.models import Job, JobStatus
from app.services.asr.base import TranscriptionResult, TranscriptChunk
from app.services.pipeline import process_job_with_dependencies
from app.storage.local import LocalJobStore


class MockASR:
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        assert audio_path.exists()
        return TranscriptionResult(
            transcript_text="Paragraph one.\n\nParagraph two.",
            vtt_text="WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\nParagraph one.",
            chunks=[
                TranscriptChunk(start=0.0, end=2.0, text="Paragraph one."),
                TranscriptChunk(start=2.1, end=4.0, text="Paragraph two."),
            ],
        )


class MockSummarizer:
    def summarize(self, transcript: str) -> tuple[dict, str]:
        assert "Paragraph one" in transcript
        summary = {
            "executive_summary": "Mock summary",
            "key_takeaways": ["Takeaway"],
            "timeline": [{"time_or_sequence": "0:00", "event": "Intro"}],
            "quotes": ["Quote"],
        }
        markdown = "# Podcast Summary\n\n## Executive summary\nMock summary"
        return summary, markdown


class FailingASR:
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        raise RuntimeError("transcription failed")


class TrackingLocalJobStore(LocalJobStore):
    def __init__(self, data_dir: Path):
        super().__init__(data_dir)
        self.status_history: list[JobStatus] = []

    def update_job(self, job: Job) -> Job:
        self.status_history.append(job.status)
        return super().update_job(job)


def test_pipeline_success_updates_job_status_and_artifacts(tmp_path: Path) -> None:
    store = TrackingLocalJobStore(tmp_path)
    job = Job.new(job_id="job-success", input_type="upload", input_source="sample.wav")
    store.create_job(job)
    store.save_audio(job.id, "sample.wav", b"fake-audio-bytes")

    process_job_with_dependencies(job.id, store, MockASR(), MockSummarizer())

    loaded = store.get_job(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.done
    assert loaded.status_message == "Completed"
    assert loaded.error is None
    assert loaded.transcript_path is not None
    assert loaded.summary_path is not None
    assert store.read_transcript(job.id) is not None
    assert store.read_transcript_vtt(job.id) is not None
    assert JobStatus.processing in store.status_history
    assert store.status_history[-1] == JobStatus.done


def test_pipeline_failure_sets_failed_status(tmp_path: Path) -> None:
    store = TrackingLocalJobStore(tmp_path)
    job = Job.new(job_id="job-failed", input_type="upload", input_source="sample.wav")
    store.create_job(job)
    store.save_audio(job.id, "sample.wav", b"fake-audio-bytes")

    process_job_with_dependencies(job.id, store, FailingASR(), MockSummarizer())

    loaded = store.get_job(job.id)
    assert loaded is not None
    assert loaded.status == JobStatus.failed
    assert loaded.status_message == "Failed"
    assert loaded.error == "transcription failed"
    assert JobStatus.processing in store.status_history
    assert store.status_history[-1] == JobStatus.failed
