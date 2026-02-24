from pathlib import Path

from app.models import Job
from app.storage.local import LocalJobStore


def test_local_store_roundtrip(tmp_path: Path) -> None:
    store = LocalJobStore(tmp_path)

    job = Job.new(job_id="job-1", input_type="upload", input_source="sample.wav")
    store.create_job(job)
    store.save_audio(job.id, "sample.wav", b"abc")
    transcript_path = store.save_transcript(job.id, "hello world")
    summary_path, markdown_path = store.save_summary(
        job.id,
        {"executive_summary": "ok", "key_takeaways": [], "timeline": [], "quotes": []},
        "# Podcast Summary",
    )

    loaded = store.get_job(job.id)
    loaded_transcript = store.read_transcript(job.id)
    loaded_summary = store.read_summary(job.id)

    assert loaded is not None
    assert transcript_path.exists()
    assert summary_path.exists()
    assert markdown_path.exists()
    assert loaded_transcript == "hello world"
    assert loaded_summary is not None
    assert loaded_summary[0]["executive_summary"] == "ok"
