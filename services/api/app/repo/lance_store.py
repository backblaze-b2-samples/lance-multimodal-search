"""LanceDB repo layer — multimodal vector store backed by B2 storage.

All ``lancedb`` / ``pyarrow`` SDK usage is confined to this module. The Lance
table, its data fragments, and the ANN index all live directly on Backblaze B2
via Lance's internal S3 client — there is no separate vector-database server.

B2 quirks (both proven necessary by the sibling agentic-rag sample):

1. ``AWS_S3_ALLOW_UNSAFE_RENAME=true`` — LanceDB commits on S3 normally use a
   conditional PUT (``If-None-Match``) that B2 does not support. We map B2
   credentials into ``AWS_*`` env vars and set this flag. Consequence:
   single-writer only. See ``docs/RELIABILITY.md``.
2. The Rust ``object_store`` backing LanceDB does not expose a user-agent
   override through LanceDB's public Python API, so Standard #2's custom-UA is
   satisfied for the boto3 client (``b2_client.py``) but not for Lance's
   internal client. Justified deviation — documented in ``ARCHITECTURE.md``.
"""

import functools
import logging
import os

import lancedb
import pyarrow as pa

from app.config import settings

logger = logging.getLogger(__name__)

# LanceDB reads AWS_* env vars for S3 auth. Map B2 credentials so Lance can
# connect to B2's S3-compatible API.
if settings.b2_application_key_id and not os.environ.get("AWS_ACCESS_KEY_ID"):
    os.environ["AWS_ACCESS_KEY_ID"] = settings.b2_application_key_id
    os.environ["AWS_SECRET_ACCESS_KEY"] = settings.b2_application_key
    os.environ["AWS_DEFAULT_REGION"] = settings.b2_region
    os.environ["AWS_ENDPOINT_URL"] = settings.b2_endpoint
    os.environ["AWS_S3_ALLOW_UNSAFE_RENAME"] = "true"
    logger.info(
        "B2->AWS env mapped for LanceDB: region=%s endpoint=%s",
        os.environ["AWS_DEFAULT_REGION"],
        os.environ["AWS_ENDPOINT_URL"],
    )

ASSETS_TABLE = "corpus_assets"
EMBEDDING_DIM = settings.embedding_dim  # 512 for clip-ViT-B-32

# One row per indexed image or PDF page. The vector is always the CLIP image
# embedding (a page is embedded via its rendered PNG).
ASSETS_SCHEMA = pa.schema(
    [
        pa.field("asset_id", pa.string()),  # unique id (source key or page key)
        pa.field("source_key", pa.string()),  # the corpus/ object this came from
        pa.field("source_filename", pa.string()),
        pa.field("content_type", pa.string()),  # image/* or application/pdf
        pa.field("kind", pa.string()),  # "image" | "pdf_page"
        pa.field("preview_key", pa.string()),  # B2 key to presign for preview
        pa.field("page_number", pa.int32()),  # 0 for images, 1..N for pdf pages
        pa.field("text_snippet", pa.string()),  # extracted page text (display only)
        pa.field("indexed_at", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
    ]
)


@functools.lru_cache(maxsize=1)
def get_db():
    """Connect to LanceDB using the configured URI (B2 S3 or local)."""
    uri = settings.lancedb_storage_uri
    logger.info("Connecting to LanceDB at %s", uri)
    db = lancedb.connect(uri)
    logger.info("LanceDB connected, existing tables: %s", db.table_names())
    return db


def _table_exists() -> bool:
    return ASSETS_TABLE in get_db().table_names()


def ensure_table_ready() -> None:
    """Startup check: ensure the assets table exists and is readable.

    Empty-schema ``create_table`` calls don't persist on S3 backends like B2,
    so we create the table *with* a seed row, then delete the row. If an
    existing table is broken (can't open / count), we drop and recreate it.
    """
    db = get_db()
    if ASSETS_TABLE in db.table_names():
        try:
            db.open_table(ASSETS_TABLE).count_rows()
            logger.info("LanceDB table '%s' is ready", ASSETS_TABLE)
            return
        except Exception:
            logger.warning(
                "LanceDB table '%s' exists but is broken — recreating",
                ASSETS_TABLE,
                exc_info=True,
            )
            db.drop_table(ASSETS_TABLE)

    logger.info("Creating LanceDB table '%s' with seed data", ASSETS_TABLE)
    seed = pa.table(
        {
            "asset_id": ["__seed__"],
            "source_key": [""],
            "source_filename": [""],
            "content_type": [""],
            "kind": ["image"],
            "preview_key": [""],
            "page_number": pa.array([0], type=pa.int32()),
            "text_snippet": [""],
            "indexed_at": [""],
            "vector": [([0.0] * EMBEDDING_DIM)],
        },
        schema=ASSETS_SCHEMA,
    )
    table = db.create_table(ASSETS_TABLE, seed)
    table.delete("asset_id = '__seed__'")
    logger.info("LanceDB table '%s' created (rows=%d)", ASSETS_TABLE, table.count_rows())


def add_rows(rows: list[dict]) -> int:
    """Insert asset/page rows (with embeddings) into the Lance table."""
    if not rows:
        return 0
    db = get_db()
    if _table_exists():
        db.open_table(ASSETS_TABLE).add(rows)
    else:
        # First insert — create table with data (reliable on S3/B2).
        logger.info("Creating LanceDB table with first %d rows", len(rows))
        db.create_table(ASSETS_TABLE, rows, schema=ASSETS_SCHEMA)
    logger.info("Stored %d rows in LanceDB", len(rows))
    return len(rows)


def get_indexed_keys() -> set[str]:
    """Return the set of source_key values already present in the table.

    Used by the library view (Indexed/Pending status) and to skip re-indexing.
    """
    if not _table_exists():
        return set()
    table = get_db().open_table(ASSETS_TABLE)
    if table.count_rows() == 0:
        return set()
    rows = table.search().select(["source_key"]).limit(1_000_000).to_list()
    return {r["source_key"] for r in rows if r.get("source_key")}


def search_vectors(query_vector: list[float], k: int | None = None) -> list[dict]:
    """Run kNN vector search over the multimodal table.

    Returns hits with a ``_distance`` field (LanceDB default L2). Lower is
    closer; the service layer converts this to a 0..1 similarity score.
    """
    if not _table_exists():
        logger.info("No assets table yet — empty search results")
        return []
    limit = k or settings.search_top_k
    table = get_db().open_table(ASSETS_TABLE)
    return table.search(query_vector).limit(limit).to_list()


def get_table_stats() -> dict:
    """Return basic stats about the assets table."""
    if not _table_exists():
        return {"total_vectors": 0, "table": ASSETS_TABLE}
    table = get_db().open_table(ASSETS_TABLE)
    return {"total_vectors": table.count_rows(), "table": ASSETS_TABLE}


def check_lancedb_connectivity() -> bool:
    """Check LanceDB reachability by listing tables."""
    try:
        get_db().table_names()
        return True
    except Exception:
        logger.warning("LanceDB connectivity check failed", exc_info=True)
        return False
