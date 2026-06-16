from pydantic import BaseModel


class CorpusItem(BaseModel):
    """A source asset in the corpus/ prefix, with its index status."""

    key: str
    filename: str
    content_type: str
    size_bytes: int
    size_human: str
    uploaded_at: str
    kind: str  # "image" | "pdf"
    indexed: bool


class IndexResult(BaseModel):
    """Outcome of a build/refresh-index run."""

    indexed_assets: int  # source files newly processed this run
    new_vectors: int  # rows (images + pdf pages) added to the table
    skipped_already_indexed: int
    errors: list[str] = []


class IndexStatus(BaseModel):
    corpus_total: int
    corpus_indexed: int
    corpus_pending: int
    total_vectors: int
    embedding_model: str
    embedding_dim: int
    vector_store_size_bytes: int
    vector_store_size_human: str
