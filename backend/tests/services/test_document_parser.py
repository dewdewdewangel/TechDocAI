from pathlib import Path

from app.services.document_parser import parse_document


def test_parse_text_document(tmp_path: Path) -> None:
    document_path = tmp_path / "guide.txt"
    document_path.write_text("TechDoc AI test content", encoding="utf-8")

    assert parse_document(document_path) == [(None, "TechDoc AI test content")]


def test_parse_markdown_document(tmp_path: Path) -> None:
    document_path = tmp_path / "guide.md"
    document_path.write_text("# Heading\n\nBody", encoding="utf-8")

    assert parse_document(document_path) == [(None, "# Heading\n\nBody")]


def test_reject_unsupported_document(tmp_path: Path) -> None:
    document_path = tmp_path / "guide.docx"
    document_path.write_bytes(b"unsupported")

    try:
        parse_document(document_path)
    except ValueError as exc:
        assert "Unsupported file type" in str(exc)
    else:
        raise AssertionError("Expected unsupported file type to fail")
