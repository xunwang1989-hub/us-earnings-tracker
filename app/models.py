from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class Job(BaseModel):
    id: str
    status: JobStatus
    created_at: datetime
    input_type: str
    input_source: str
    transcript_path: str | None = None
    summary_path: str | None = None
    status_message: str | None = None
    error: str | None = None

    @classmethod
    def new(cls, job_id: str, input_type: str, input_source: str) -> "Job":
        return cls(
            id=job_id,
            status=JobStatus.queued,
            created_at=datetime.now(timezone.utc),
            input_type=input_type,
            input_source=input_source,
            status_message="Queued",
        )
