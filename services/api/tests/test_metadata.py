import fitz

from app.service.metadata import _clean_pdf_metadata_value, extract_metadata


def _pdf_bytes(metadata: dict[str, str] | None = None) -> bytes:
    doc = fitz.open()
    try:
        doc.new_page()
        if metadata:
            doc.set_metadata(metadata)
        return doc.tobytes()
    finally:
        doc.close()


def test_extract_pdf_metadata_with_pymupdf() -> None:
    metadata = extract_metadata(
        _pdf_bytes({"author": "Backblaze", "title": "Corpus Guide"}),
        "guide.pdf",
        "application/pdf",
    )

    assert metadata.pdf_pages == 1
    assert metadata.pdf_author == "Backblaze"
    assert metadata.pdf_title == "Corpus Guide"


def test_extract_pdf_metadata_ignores_corrupt_pdf() -> None:
    metadata = extract_metadata(b"not a pdf", "bad.pdf", "application/pdf")

    assert metadata.pdf_pages is None
    assert metadata.pdf_author is None
    assert metadata.pdf_title is None


def test_clean_pdf_metadata_value_trims_and_normalizes_empty() -> None:
    assert _clean_pdf_metadata_value("  Backblaze  ") == "Backblaze"
    assert _clean_pdf_metadata_value("   ") is None
    assert _clean_pdf_metadata_value(None) is None
