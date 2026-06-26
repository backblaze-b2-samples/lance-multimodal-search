import re

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

_B2_REGION_RE = re.compile(r"^[a-z]{2}(?:-[a-z]+)+-\d{3}$")
_B2_REGION_PLACEHOLDER = "your_b2_region"


class Settings(BaseSettings):
    # --- Backblaze B2 (Standard #3 env names) ---
    b2_region: str = ""
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_public_url_base: str = ""
    legacy_b2_endpoint: str = Field(default="", validation_alias="B2_ENDPOINT")
    legacy_b2_public_url: str = Field(
        default="",
        validation_alias="B2_PUBLIC_URL",
    )

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    # --- Multimodal search / vector store ---
    # LanceDB vector store lives on B2 (defaults to s3://{B2_BUCKET_NAME}/lancedb/).
    lancedb_uri: str = ""  # override with a custom S3 URI or local path
    # CLIP model — image + text into one shared embedding space (CPU, no API key).
    embedding_model: str = "clip-ViT-B-32"
    embedding_dim: int = 512
    # Prefixes inside the bucket.
    corpus_prefix: str = "corpus/"  # source images + PDFs the user uploads
    derived_prefix: str = "derived/pages/"  # machine-generated PDF page renders
    lancedb_prefix: str = "lancedb/"  # Lance table + ANN index
    # PDF rendering.
    max_pages_per_doc: int = 25
    pdf_render_dpi: int = 120
    # Search.
    search_top_k: int = 24
    max_search_image_pixels: int = 16_777_216  # 4096 x 4096 decoded pixels
    max_search_image_dimension: int = 8192
    # Durable query log for the dashboard recent-searches table.
    query_log_file: str = "data/search_log.json"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "forbid",
    }

    @field_validator("b2_region")
    @classmethod
    def validate_b2_region(cls, value: str) -> str:
        if not value:
            return value
        if value == _B2_REGION_PLACEHOLDER:
            return value
        if not _B2_REGION_RE.fullmatch(value):
            raise ValueError(
                "B2_REGION must be a Backblaze region like us-west-004"
            )
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    @property
    def b2_endpoint(self) -> str:
        """Derive the B2 S3-compatible endpoint from B2_REGION."""
        if not self.b2_region:
            return ""
        if self.b2_region == _B2_REGION_PLACEHOLDER:
            return ""
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def lancedb_storage_uri(self) -> str:
        """Resolve the LanceDB URI, defaulting to the B2 bucket path."""
        if self.lancedb_uri:
            return self.lancedb_uri
        return f"s3://{self.b2_bucket_name}/{self.lancedb_prefix}"


settings = Settings()
