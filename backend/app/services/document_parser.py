from pathlib import Path

from pypdf import PdfReader


def parse_document(path: Path) -> list[tuple[int | None, str]]:
    extension = path.suffix.lower()

    if extension in {".txt", ".md", ".markdown"}:
        return [(None, path.read_text(encoding="utf-8"))]

    if extension == ".pdf":
        reader = PdfReader(path)
        return [
            (page_number, page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        ]

    raise ValueError(f"Unsupported file type: {extension}")
