import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.config import Settings
from app.services.asr.base import TranscriptChunk, TranscriptionResult


@dataclass(slots=True)
class _RawSegment:
    start: float
    end: float
    text: str


class FasterWhisperASR:
    def __init__(self, settings: Settings):
        self.settings = settings

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Install dependencies before running jobs."
            ) from exc

        prepared_audio_path, cleanup_path = self._prepare_audio(audio_path)
        model = WhisperModel(
            self.settings.whisper_model_size,
            device=self.settings.whisper_device,
            compute_type=self.settings.whisper_compute_type,
        )
        try:
            segments, _ = model.transcribe(str(prepared_audio_path), vad_filter=True)
            raw_segments = [
                _RawSegment(start=float(seg.start), end=float(seg.end), text=seg.text.strip())
                for seg in segments
                if seg.text and seg.text.strip()
            ]
            if not raw_segments:
                raise RuntimeError("ASR produced an empty transcript")

            chunks = self._chunk_by_time(raw_segments)
            transcript_text = "\n\n".join(chunk.text for chunk in chunks).strip()
            vtt_text = self._to_vtt(raw_segments)
            return TranscriptionResult(
                transcript_text=transcript_text,
                vtt_text=vtt_text,
                chunks=chunks,
            )
        finally:
            if cleanup_path and cleanup_path.exists():
                cleanup_path.unlink(missing_ok=True)

    @staticmethod
    def _chunk_by_time(
        segments: list[_RawSegment], gap_seconds: float = 2.5, max_chars: int = 900
    ) -> list[TranscriptChunk]:
        chunks: list[TranscriptChunk] = []
        current_start = segments[0].start
        current_end = segments[0].end
        current_parts: list[str] = [segments[0].text]

        for seg in segments[1:]:
            current_text = " ".join(current_parts).strip()
            should_split = (seg.start - current_end) >= gap_seconds or len(current_text) >= max_chars

            if should_split:
                chunks.append(
                    TranscriptChunk(start=current_start, end=current_end, text=current_text)
                )
                current_start = seg.start
                current_parts = [seg.text]
            else:
                current_parts.append(seg.text)
            current_end = seg.end

        final_text = " ".join(current_parts).strip()
        chunks.append(TranscriptChunk(start=current_start, end=current_end, text=final_text))
        return chunks

    @staticmethod
    def _to_vtt(segments: list[_RawSegment]) -> str:
        lines = ["WEBVTT", ""]
        for index, seg in enumerate(segments, start=1):
            lines.append(str(index))
            lines.append(f"{_format_vtt_time(seg.start)} --> {_format_vtt_time(seg.end)}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

    def _prepare_audio(self, audio_path: Path) -> tuple[Path, Path | None]:
        # Convert non-wav files to wav when ffmpeg is available to improve compatibility.
        if audio_path.suffix.lower() == ".wav":
            return audio_path, None
        if not shutil.which("ffmpeg"):
            return audio_path, None

        temp = NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp.name)
        temp.close()
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            str(temp_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            temp_path.unlink(missing_ok=True)
            return audio_path, None
        return temp_path, temp_path


def _format_vtt_time(seconds: float) -> str:
    total_ms = int(max(seconds, 0) * 1000)
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
