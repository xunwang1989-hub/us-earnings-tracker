from pathlib import Path
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class TranscriptChunk:
    start: float
    end: float
    text: str


@dataclass(slots=True)
class TranscriptionResult:
    transcript_text: str
    vtt_text: str | None
    chunks: list[TranscriptChunk]


class ASRProvider(Protocol):
    def transcribe(self, audio_path: Path) -> TranscriptionResult: ...
