from __future__ import annotations


def chunk_text(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")

    stripped = text.strip()
    if not stripped:
        return []

    chunks: list[str] = []
    cursor = 0
    while cursor < len(stripped):
        end = min(cursor + max_chars, len(stripped))
        if end < len(stripped):
            split_at = stripped.rfind("\n", cursor, end)
            if split_at <= cursor:
                split_at = stripped.rfind(" ", cursor, end)
            if split_at > cursor:
                end = split_at
        chunk = stripped[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        cursor = max(end, cursor + 1)

    return chunks
