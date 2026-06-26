"""Search service — text or image query over the multimodal Lance table.

Embeds the query (CLIP text or CLIP image) into the shared 512-dim space, runs
kNN over the B2-resident Lance table, maps each hit to a presigned B2 preview
URL, and logs the query for the dashboard's recent-searches table.
"""

import logging

from app.config import settings
from app.repo import (
    ImageTooLargeError,
    InvalidImageError,
    encode_image,
    encode_text,
    get_presigned_url,
    log_search,
    search_vectors,
)
from app.types import SearchHit, SearchResponse

logger = logging.getLogger(__name__)

# CLIP embeddings are L2-normalized, so LanceDB's default squared-L2 distance
# d lies in [0, 4]. Map it to a 0..1 similarity for display (1.0 = identical).
_MAX_L2_SQ = 4.0


class SearchError(Exception):
    """Raised when a search request is invalid."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _distance_to_score(distance: float) -> float:
    score = 1.0 - (distance / _MAX_L2_SQ)
    return round(max(0.0, min(1.0, score)), 4)


def _to_hits(raw: list[dict]) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for r in raw:
        if r.get("asset_id") == "__seed__":
            continue
        preview_key = r.get("preview_key") or r.get("source_key", "")
        try:
            preview_url = get_presigned_url(preview_key) if preview_key else None
        except RuntimeError:
            preview_url = None
        hits.append(
            SearchHit(
                asset_id=r.get("asset_id", ""),
                source_key=r.get("source_key", ""),
                source_filename=r.get("source_filename", ""),
                content_type=r.get("content_type", ""),
                kind=r.get("kind", "image"),
                page_number=r.get("page_number", 0),
                text_snippet=r.get("text_snippet", ""),
                score=_distance_to_score(r.get("_distance", _MAX_L2_SQ)),
                preview_url=preview_url,
            )
        )
    return hits


def search_text(query: str, top_k: int | None = None) -> SearchResponse:
    """Free-text query -> CLIP text embedding -> ANN over the corpus."""
    cleaned = query.strip()
    if not cleaned:
        raise SearchError("Query must not be empty")
    vector = encode_text(cleaned)
    hits = _to_hits(search_vectors(vector, k=top_k or settings.search_top_k))
    top_score = hits[0].score if hits else None
    log_search("text", cleaned, len(hits), top_score)
    return SearchResponse(query=cleaned, mode="text", count=len(hits), hits=hits)


def search_image(
    image_bytes: bytes, filename: str, top_k: int | None = None
) -> SearchResponse:
    """Example image -> CLIP image embedding -> ANN over the corpus."""
    if not image_bytes:
        raise SearchError("Empty image")
    try:
        vector = encode_image(image_bytes)
    except ImageTooLargeError:
        raise SearchError("Image dimensions too large") from None
    except InvalidImageError:
        raise SearchError("Invalid image upload") from None
    hits = _to_hits(search_vectors(vector, k=top_k or settings.search_top_k))
    top_score = hits[0].score if hits else None
    log_search("image", filename or "(uploaded image)", len(hits), top_score)
    return SearchResponse(
        query=filename or "(uploaded image)", mode="image", count=len(hits), hits=hits
    )
