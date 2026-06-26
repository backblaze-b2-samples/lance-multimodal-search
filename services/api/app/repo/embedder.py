"""CLIP embedder — image + text into one shared 512-dim space.

All ``sentence-transformers`` / ``torch`` SDK usage is confined to this module.
Placed in ``repo/`` to contain the external ML SDK, mirroring how ``boto3`` and
``lancedb`` are contained. The structural test only mechanically enforces
boto3-in-repo, but we follow the AGENTS.md "contain external SDKs" intent.

The model (default ``clip-ViT-B-32``) runs locally on CPU — there is no
external API key. The first call downloads the model weights from HuggingFace
(a one-time, key-free fetch), after which it is cached on disk.
"""

import functools
import io
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class InvalidImageError(Exception):
    """Raised when uploaded bytes cannot be decoded as an image."""


@functools.lru_cache(maxsize=1)
def _get_model():
    """Lazily load the CLIP model once (heavy import + first-run download)."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading CLIP model '%s' (CPU, no API key)", settings.embedding_model)
    model = SentenceTransformer(settings.embedding_model, device="cpu")
    logger.info("CLIP model loaded")
    return model


def encode_image(image_bytes: bytes) -> list[float]:
    """Embed raw image bytes into the shared CLIP space."""
    from PIL import Image

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except (Image.DecompressionBombError, OSError, ValueError) as e:
        raise InvalidImageError("Invalid image data") from e

    vector = _get_model().encode(image, convert_to_numpy=True, normalize_embeddings=True)
    return vector.astype("float32").tolist()


def encode_text(text: str) -> list[float]:
    """Embed a free-text query into the shared CLIP space."""
    vector = _get_model().encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vector.astype("float32").tolist()


def check_model_ready() -> bool:
    """Return True if the CLIP model can be loaded (used by /health)."""
    try:
        _get_model()
        return True
    except Exception:
        logger.warning("CLIP model load failed", exc_info=True)
        return False
