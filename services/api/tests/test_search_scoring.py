"""Unit tests for search scoring and hit mapping (no model/vector deps)."""

from app.service import search as search_service


def test_distance_to_score_bounds():
    """Squared-L2 distance in [0, 4] maps to similarity in [0, 1]."""
    assert search_service._distance_to_score(0.0) == 1.0  # identical
    assert search_service._distance_to_score(4.0) == 0.0  # opposite
    mid = search_service._distance_to_score(2.0)
    assert 0.0 < mid < 1.0
    # Out-of-range distances are clamped, never negative or > 1.
    assert search_service._distance_to_score(10.0) == 0.0
    assert search_service._distance_to_score(-1.0) == 1.0


def test_to_hits_skips_seed_and_maps_fields(monkeypatch):
    """Seed rows are dropped; preview URLs come from preview_key."""
    monkeypatch.setattr(
        search_service, "get_presigned_url", lambda key: f"https://signed/{key}"
    )
    raw = [
        {"asset_id": "__seed__", "source_key": "", "preview_key": "", "_distance": 0.0},
        {
            "asset_id": "corpus/a.png",
            "source_key": "corpus/a.png",
            "source_filename": "a.png",
            "content_type": "image/png",
            "kind": "image",
            "preview_key": "corpus/a.png",
            "page_number": 0,
            "text_snippet": "",
            "_distance": 0.4,
        },
    ]
    hits = search_service._to_hits(raw)
    assert len(hits) == 1
    hit = hits[0]
    assert hit.asset_id == "corpus/a.png"
    assert hit.preview_url == "https://signed/corpus/a.png"
    assert 0.0 <= hit.score <= 1.0
