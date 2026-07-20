from app.services.text_splitter import split_text


def test_split_text_preserves_overlap() -> None:
    chunks = split_text("A" * 120, chunk_size=50, overlap=10)

    assert len(chunks) == 3
    assert all(len(chunk) <= 50 for chunk in chunks)
    assert chunks[0][-10:] == chunks[1][:10]
    assert chunks[1][-10:] == chunks[2][:10]


def test_split_text_ignores_empty_content() -> None:
    assert split_text("  \n\n  ", chunk_size=50, overlap=10) == []
