from app.utils.chunking import chunk_text


def test_chunk_text_returns_multiple_chunks() -> None:
    text = "alpha beta gamma delta " * 100
    chunks = chunk_text(text, max_chars=80)

    assert len(chunks) > 1
    assert all(len(chunk) <= 80 for chunk in chunks)


def test_chunk_text_empty_input() -> None:
    assert chunk_text("   ", max_chars=100) == []
