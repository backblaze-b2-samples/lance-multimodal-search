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
import warnings

from app.config import settings

logger = logging.getLogger(__name__)


class InvalidImageError(Exception):
    """Raised when uploaded bytes cannot be decoded as an image."""


class ImageTooLargeError(InvalidImageError):
    """Raised when decoded image dimensions exceed the configured limit."""


@functools.lru_cache(maxsize=1)
def _get_model():
    """Lazily load the CLIP model once (heavy import + first-run download)."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading CLIP model '%s' (CPU, no API key)", settings.embedding_model)
    model = SentenceTransformer(settings.embedding_model, device="cpu")
    logger.info("CLIP model loaded")
    return model


def _validate_image_dimensions(width: int, height: int) -> None:
    pixels = width * height
    max_dimension = settings.max_search_image_dimension
    max_pixels = settings.max_search_image_pixels
    if width <= 0 or height <= 0:
        raise InvalidImageError("Invalid image dimensions")
    if width > max_dimension or height > max_dimension or pixels > max_pixels:
        raise ImageTooLargeError("Image dimensions too large")


def encode_image(image_bytes: bytes) -> list[float]:
    """Embed raw image bytes into the shared CLIP space."""
    from PIL import Image

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as image:
                _validate_image_dimensions(image.width, image.height)
                rgb_image = image.convert("RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise ImageTooLargeError("Image dimensions too large") from e
    except ImageTooLargeError:
        raise
    except (OSError, ValueError) as e:
        raise InvalidImageError("Invalid image data") from e

    vector = _get_model().encode(
        rgb_image, convert_to_numpy=True, normalize_embeddings=True
    )
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
