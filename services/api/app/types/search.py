from pydantic import BaseModel


class SearchHit(BaseModel):
    asset_id: str
    source_key: str
    source_filename: str
    content_type: str
    kind: str  # "image" | "pdf_page"
    page_number: int  # 0 for images, 1..N for pdf pages
    text_snippet: str
    score: float  # 0..1 similarity (1.0 = closest)
    preview_url: str | None = None


class TextSearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class SearchResponse(BaseModel):
    query: str
    mode: str  # "text" | "image"
    count: int
    hits: list[SearchHit]


class RecentSearch(BaseModel):
    ts: str
    mode: str  # "text" | "image"
    query: str  # the text query, or the image filename for image search
    result_count: int
    top_score: float | None = None
