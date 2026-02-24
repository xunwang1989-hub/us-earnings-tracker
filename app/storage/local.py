import json
from pathlib import Path

from app.models import Job


class LocalJobStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.jobs_dir = self.data_dir / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def _job_meta_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "job.json"

    def _summary_json_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "summary.json"

    def _summary_md_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "summary.md"

    def _transcript_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "transcript.txt"

    def _transcript_vtt_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "transcript.vtt"

    def create_job(self, job: Job) -> Job:
        job_dir = self._job_dir(job.id)
        job_dir.mkdir(parents=True, exist_ok=False)
        self._job_meta_path(job.id).write_text(job.model_dump_json(indent=2), encoding="utf-8")
        return job

    def get_job(self, job_id: str) -> Job | None:
        meta_path = self._job_meta_path(job_id)
        if not meta_path.exists():
            return None
        return Job.model_validate_json(meta_path.read_text(encoding="utf-8"))

    def update_job(self, job: Job) -> Job:
        self._job_meta_path(job.id).write_text(job.model_dump_json(indent=2), encoding="utf-8")
        return job

    def save_audio(self, job_id: str, source_name: str, content: bytes) -> Path:
        suffix = Path(source_name).suffix or ".bin"
        audio_path = self._job_dir(job_id) / f"input{suffix.lower()}"
        audio_path.write_bytes(content)
        return audio_path

    def save_transcript(self, job_id: str, transcript: str, vtt: str | None = None) -> Path:
        path = self._transcript_path(job_id)
        path.write_text(transcript, encoding="utf-8")
        if vtt is not None:
            self._transcript_vtt_path(job_id).write_text(vtt, encoding="utf-8")
        return path

    def save_summary(self, job_id: str, summary: dict, markdown: str) -> tuple[Path, Path]:
        json_path = self._summary_json_path(job_id)
        md_path = self._summary_md_path(job_id)
        json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        md_path.write_text(markdown, encoding="utf-8")
        return json_path, md_path

    def read_transcript(self, job_id: str) -> str | None:
        path = self._transcript_path(job_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def read_transcript_vtt(self, job_id: str) -> str | None:
        path = self._transcript_vtt_path(job_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def read_summary(self, job_id: str) -> tuple[dict, str] | None:
        json_path = self._summary_json_path(job_id)
        md_path = self._summary_md_path(job_id)
        if not json_path.exists() or not md_path.exists():
            return None
        summary = json.loads(json_path.read_text(encoding="utf-8"))
        markdown = md_path.read_text(encoding="utf-8")
        return summary, markdown

    def job_audio_path(self, job_id: str) -> Path | None:
        job_dir = self._job_dir(job_id)
        if not job_dir.exists():
            return None
        for candidate in job_dir.glob("input.*"):
            return candidate
        return None
