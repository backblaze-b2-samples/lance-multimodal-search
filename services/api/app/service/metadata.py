import hashlib
import io
import logging
from datetime import UTC, datetime

from app.types import FileMetadataDetail
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


def _extract_image_metadata(file_data: bytes) -> dict:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(io.BytesIO(file_data))
        result: dict = {
            "image_width": img.width,
            "image_height": img.height,
        }

        exif_data = {}
        raw_exif = img.getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="replace")
                    except Exception:
                        value = str(value)
                exif_data[str(tag)] = str(value)
            result["exif"] = exif_data if exif_data else None
        return result
    except Exception:
        logger.warning("Image metadata extraction failed", exc_info=True)
        return {}


def _extract_pdf_metadata(file_data: bytes) -> dict:
    try:
        import fitz  # pymupdf

        with fitz.open(stream=file_data, filetype="pdf") as doc:
            info = doc.metadata or {}
            return {
                "pdf_pages": doc.page_count,
                "pdf_author": _clean_pdf_metadata_value(info.get("author")),
                "pdf_title": _clean_pdf_metadata_value(info.get("title")),
            }
    except Exception:
        logger.warning("PDF metadata extraction failed", exc_info=True)
        return {}


def _clean_pdf_metadata_value(value: str | None) -> str | None:
    cleaned = value.strip() if value else ""
    return cleaned or None


def extract_metadata(
    file_data: bytes,
    filename: str,
    content_type: str,
) -> FileMetadataDetail:
    md5 = hashlib.md5(file_data, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(file_data).hexdigest()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    extra: dict = {}

    if content_type.startswith("image/"):
        extra = _extract_image_metadata(file_data)
    elif content_type == "application/pdf":
        extra = _extract_pdf_metadata(file_data)

    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=md5,
        sha256=sha256,
        uploaded_at=datetime.now(UTC),
        **extra,
    )
