import logging

from fastapi import APIRouter

from app.service.indexing import build_index, get_index_status, list_corpus
from app.types import CorpusItem, IndexResult, IndexStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/index", response_model=IndexResult)
async def build_index_endpoint():
    """Build / refresh the multimodal vector index from the corpus."""
    result = build_index()
    logger.info(
        "Index build: assets=%d vectors=%d skipped=%d errors=%d",
        result.indexed_assets,
        result.new_vectors,
        result.skipped_already_indexed,
        len(result.errors),
    )
    return result


@router.get("/index/status", response_model=IndexStatus)
async def index_status_endpoint():
    """Corpus + vector-store metrics (counts, model, B2 vector-store size)."""
    return get_index_status()


@router.get("/corpus", response_model=list[CorpusItem])
async def corpus_endpoint():
    """List source assets under corpus/ with per-item index status."""
    return list_corpus()
