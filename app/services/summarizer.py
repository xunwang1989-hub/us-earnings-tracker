import json
from typing import Any

from app.config import Settings
from app.utils.chunking import chunk_text


class OpenAIMapReduceSummarizer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def summarize(self, transcript: str) -> tuple[dict[str, Any], str]:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed") from exc

        client = OpenAI(api_key=self.settings.openai_api_key)

        chunks = chunk_text(transcript, self.settings.map_chunk_chars)
        if not chunks:
            raise RuntimeError("Cannot summarize an empty transcript")

        mapped: list[dict[str, Any]] = []
        for idx, chunk in enumerate(chunks, start=1):
            map_prompt = (
                "Summarize this podcast transcript chunk into strict JSON with keys: "
                "executive_summary (string), key_takeaways (array of strings), "
                "timeline (array of {time_or_sequence, event}), quotes (array of strings). "
                "Keep details factual from the chunk only."
            )
            response = client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": "You are a precise podcast summarization engine. Return JSON only.",
                    },
                    {
                        "role": "user",
                        "content": f"Chunk {idx}/{len(chunks)}:\n\n{chunk}\n\n{map_prompt}",
                    },
                ],
            )
            mapped.append(self._parse_json(response.output_text))

        reduce_prompt = (
            "Merge these partial summaries into one final strict JSON with keys: "
            "executive_summary (string), key_takeaways (array of strings), "
            "timeline (array of {time_or_sequence, event}), quotes (array of strings). "
            "Deduplicate and keep concise."
        )
        reduced = client.responses.create(
            model=self.settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": "You consolidate podcast summaries. Return JSON only.",
                },
                {
                    "role": "user",
                    "content": f"Partials JSON:\n{json.dumps(mapped)}\n\n{reduce_prompt}",
                },
            ],
        )
        summary = self._parse_json(reduced.output_text)
        markdown = self._to_markdown(summary)
        return summary, markdown

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI did not return valid JSON") from exc

        if not isinstance(data, dict):
            raise RuntimeError("Summary response must be a JSON object")
        return data

    @staticmethod
    def _to_markdown(summary: dict[str, Any]) -> str:
        executive = summary.get("executive_summary", "")
        key_takeaways = summary.get("key_takeaways", [])
        timeline = summary.get("timeline", [])
        quotes = summary.get("quotes", [])

        lines = ["# Podcast Summary", "", "## Executive summary", str(executive), ""]

        lines.append("## Key takeaways")
        if key_takeaways:
            lines.extend([f"- {item}" for item in key_takeaways])
        else:
            lines.append("- None")
        lines.append("")

        lines.append("## Timeline")
        if timeline:
            for point in timeline:
                if isinstance(point, dict):
                    seq = point.get("time_or_sequence", "Point")
                    evt = point.get("event", "")
                    lines.append(f"- **{seq}:** {evt}")
                else:
                    lines.append(f"- {point}")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("## Quotes")
        if quotes:
            lines.extend([f"> {quote}" for quote in quotes])
        else:
            lines.append("> None")
        lines.append("")

        return "\n".join(lines)
