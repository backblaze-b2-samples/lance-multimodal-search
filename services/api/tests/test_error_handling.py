"""Tests for error handling across the API."""

from io import BytesIO

import pytest

from app.service import files as files_service


def _png_bytes(width: int, height: int) -> BytesIO:
    from PIL import Image

    data = BytesIO()
    Image.new("RGB", (width, height), color=(0, 0, 0)).save(data, format="PNG")
    data.seek(0)
    return data


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500(client, monkeypatch):
    """Global handler catches unhandled exceptions and returns 500 JSON."""

    def explode(**kwargs):
        raise RuntimeError("B2 exploded")

    monkeypatch.setattr(files_service, "list_files", explode)

    response = await client.get("/files")
    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Internal server error"
    # Ensure raw error message is NOT leaked to the client
    assert "B2 exploded" not in body["detail"]


@pytest.mark.asyncio
async def test_stats_b2_failure_returns_500(client, monkeypatch):
    """Stats endpoint returns 500 when B2 is unreachable."""

    def explode():
        raise RuntimeError("B2 stats query failed")

    monkeypatch.setattr(files_service, "get_upload_stats", explode)

    response = await client.get("/files/stats")
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"


@pytest.mark.asyncio
async def test_download_not_found_returns_404(client, monkeypatch):
    """Download for a missing file returns 404 with detail."""
    monkeypatch.setattr(files_service, "get_file_metadata", lambda key: None)

    response = await client.get("/files/uploads/missing.txt/download")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_traversal_keys_are_rejected():
    """validate_key blocks empty keys and path-traversal patterns."""
    from app.service.files import FileKeyError, validate_key

    bad_keys = [
        "",
        "uploads/../secret.txt",
        "../etc/passwd",
        "uploads\\secret.txt",
        "uploads/%2e%2e/secret",
        "uploads/\x00null",
    ]
    for bad in bad_keys:
        with pytest.raises(FileKeyError):
            validate_key(bad)

    # Sanity: ordinary keys (including those outside uploads/) pass.
    validate_key("uploads/file.txt")
    validate_key("photos/2026/vacation.jpg")
    validate_key("readme.md")


@pytest.mark.asyncio
async def test_upload_empty_file_returns_400(client):
    """Uploading an empty file returns 400 with explanation."""

    response = await client.post(
        "/upload",
        files={"file": ("empty.png", BytesIO(b""), "image/png")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_image_search_invalid_image_returns_400(client):
    """Invalid example-image bytes are rejected instead of surfacing a 500."""
    response = await client.post(
        "/search/image",
        files={"file": ("bad.png", BytesIO(b"not an image"), "image/png")},
    )

    assert response.status_code == 400
    assert "invalid image" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_image_search_oversized_decoded_image_returns_400(
    client, monkeypatch
):
    """Decoded image limits reject compressed inputs before model or vector work."""
    from PIL import Image

    from app.repo import embedder
    from app.service import search as search_service

    image_data = _png_bytes(33, 33)

    def fail_rgb_conversion(*_args, **_kwargs):
        raise AssertionError("RGB conversion should not run")

    def fail_model_load():
        raise AssertionError("CLIP model should not load")

    def fail_vector_search(*_args, **_kwargs):
        raise AssertionError("vector search should not run")

    monkeypatch.setattr(embedder.settings, "max_search_image_pixels", 1_024)
    monkeypatch.setattr(Image.Image, "convert", fail_rgb_conversion)
    monkeypatch.setattr(embedder, "_get_model", fail_model_load)
    monkeypatch.setattr(search_service, "search_vectors", fail_vector_search)

    response = await client.post(
        "/search/image",
        files={"file": ("large.png", image_data, "image/png")},
    )

    assert response.status_code == 400
    assert "dimensions" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_image_search_decompression_warning_returns_400(
    client, monkeypatch
):
    """Pillow decompression warnings promoted to errors return bounded 400s."""
    from PIL import Image

    from app.repo import embedder
    from app.service import search as search_service

    image_data = _png_bytes(11, 10)

    def fail_rgb_conversion(*_args, **_kwargs):
        raise AssertionError("RGB conversion should not run")

    def fail_model_load():
        raise AssertionError("CLIP model should not load")

    def fail_vector_search(*_args, **_kwargs):
        raise AssertionError("vector search should not run")

    monkeypatch.setattr(embedder.settings, "max_search_image_pixels", 10_000)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    monkeypatch.setattr(Image.Image, "convert", fail_rgb_conversion)
    monkeypatch.setattr(embedder, "_get_model", fail_model_load)
    monkeypatch.setattr(search_service, "search_vectors", fail_vector_search)

    response = await client.post(
        "/search/image",
        files={"file": ("warning.png", image_data, "image/png")},
    )

    assert response.status_code == 400
    assert "dimensions" in response.json()["detail"].lower()
