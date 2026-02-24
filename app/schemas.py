from pydantic import BaseModel

from app.models import Job


class JobCreateResponse(BaseModel):
    id: str
    status: str


class SummaryResponse(BaseModel):
    job: Job
    summary: dict
    markdown: str
