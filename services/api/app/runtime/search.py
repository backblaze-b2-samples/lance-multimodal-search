import logging

from fastapi import APIRouter, HTTPException, UploadFile

from app.config import settings
from app.service.search import SearchError, search_image, search_text
from app.types import SearchResponse, TextSearchRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search/text", response_model=SearchResponse)
async def search_text_endpoint(req: TextSearchRequest):
    """Search the corpus by free-text query (CLIP text embedding)."""
    try:
        result = search_text(req.query, top_k=req.top_k)
    except SearchError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    logger.info("Text search: query=%r hits=%d", req.query, result.count)
    return result


@router.post("/search/image", response_model=SearchResponse)
async def search_image_endpoint(file: UploadFile):
    """Search the corpus by example image (CLIP image embedding)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="Image too large")
        chunks.append(chunk)
    image_bytes = b"".join(chunks)

    try:
        result = search_image(image_bytes, file.filename or "", top_k=None)
    except SearchError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    logger.info("Image search: file=%s hits=%d", file.filename, result.count)
    return result
