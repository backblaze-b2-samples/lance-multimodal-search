"""Indexing service — build/refresh the multimodal vector index from the corpus.

Flow: list ``corpus/`` via the B2 repo -> for each not-yet-indexed asset:
  * images   -> embed the image directly (one Lance row)
  * PDFs     -> render each page (capped at MAX_PAGES_PER_DOC) to a PNG via
                pymupdf, store the page PNG to B2 under ``derived/pages/``,
                embed the page render with CLIP (one Lance row per page)
Then write the rows to the Lance store.

pymupdf/fitz is a rendering library (it ships its own libs — no poppler/system
deps) and is used only here in the service layer; the structural test enforces
boto3-in-repo, and all storage/ML/vector SDKs stay in repo/.
"""

import logging
from datetime import UTC, datetime

from app.config import settings
from app.repo import (
    add_rows,
    encode_image,
    ensure_table_ready,
    get_indexed_keys,
    get_object_bytes,
    get_prefix_size,
    get_table_stats,
    list_files,
    upload_file,
)
from app.types import CorpusItem, IndexResult, IndexStatus

logger = logging.getLogger(__name__)

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_PDF_TYPE = "application/pdf"


def _kind_for(content_type: str) -> str | None:
    if content_type in _IMAGE_TYPES:
        return "image"
    if content_type == _PDF_TYPE:
        return "pdf"
    return None


def _doc_stem(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return stem.replace("/", "_")


def list_corpus() -> list[CorpusItem]:
    """List source assets under the corpus/ prefix with their index status."""
    indexed = get_indexed_keys()
    items: list[CorpusItem] = []
    for f in list_files(prefix=settings.corpus_prefix, max_keys=1000):
        kind = _kind_for(f.content_type)
        if kind is None:
            continue
        items.append(
            CorpusItem(
                key=f.key,
                filename=f.filename,
                content_type=f.content_type,
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                uploaded_at=f.uploaded_at.isoformat(),
                kind=kind,
                indexed=f.key in indexed,
            )
        )
    return items


def _render_pdf_rows(key: str, filename: str, data: bytes) -> list[dict]:
    """Render each PDF page to a PNG, store it to B2, and build embedded rows."""
    import fitz  # pymupdf — bundles its own libs, no system deps

    rows: list[dict] = []
    stem = _doc_stem(filename)
    zoom = settings.pdf_render_dpi / 72.0
    now = datetime.now(UTC).isoformat()
    with fitz.open(stream=data, filetype="pdf") as doc:
        page_count = min(doc.page_count, settings.max_pages_per_doc)
        for i in range(page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            png_bytes = pix.tobytes("png")
            page_num = i + 1
            preview_key = f"{settings.derived_prefix}{stem}/{page_num:04d}.png"
            upload_file(png_bytes, preview_key, "image/png")
            snippet = page.get_text("text").strip().replace("\n", " ")[:500]
            rows.append(
                {
                    "asset_id": preview_key,
                    "source_key": key,
                    "source_filename": filename,
                    "content_type": _PDF_TYPE,
                    "kind": "pdf_page",
                    "preview_key": preview_key,
                    "page_number": page_num,
                    "text_snippet": snippet,
                    "indexed_at": now,
                    "vector": encode_image(png_bytes),
                }
            )
    return rows


def _image_row(key: str, filename: str, content_type: str, data: bytes) -> dict:
    return {
        "asset_id": key,
        "source_key": key,
        "source_filename": filename,
        "content_type": content_type,
        "kind": "image",
        "preview_key": key,
        "page_number": 0,
        "text_snippet": "",
        "indexed_at": datetime.now(UTC).isoformat(),
        "vector": encode_image(data),
    }


def build_index() -> IndexResult:
    """Index every not-yet-indexed corpus asset. Idempotent and resumable."""
    ensure_table_ready()
    indexed = get_indexed_keys()
    indexed_assets = 0
    new_vectors = 0
    skipped = 0
    errors: list[str] = []

    for item in list_corpus():
        if item.key in indexed:
            skipped += 1
            continue
        try:
            data = get_object_bytes(item.key)
            if item.kind == "image":
                rows = [_image_row(item.key, item.filename, item.content_type, data)]
            else:
                rows = _render_pdf_rows(item.key, item.filename, data)
            if rows:
                add_rows(rows)
                indexed_assets += 1
                new_vectors += len(rows)
        except Exception as e:  # collect per-asset failures, keep indexing
            logger.warning("Indexing failed for %s: %s", item.key, e, exc_info=True)
            errors.append(f"{item.filename}: {e}")

    logger.info(
        "Index build complete: assets=%d vectors=%d skipped=%d errors=%d",
        indexed_assets,
        new_vectors,
        skipped,
        len(errors),
    )
    return IndexResult(
        indexed_assets=indexed_assets,
        new_vectors=new_vectors,
        skipped_already_indexed=skipped,
        errors=errors,
    )


def get_index_status() -> IndexStatus:
    """Aggregate corpus + vector-store metrics for the dashboard / library."""
    corpus = list_corpus()
    corpus_indexed = sum(1 for c in corpus if c.indexed)
    table = get_table_stats()
    store = get_prefix_size(settings.lancedb_prefix)
    return IndexStatus(
        corpus_total=len(corpus),
        corpus_indexed=corpus_indexed,
        corpus_pending=len(corpus) - corpus_indexed,
        total_vectors=table["total_vectors"],
        embedding_model=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
        vector_store_size_bytes=store["total_size_bytes"],
        vector_store_size_human=store["total_size_human"],
    )
