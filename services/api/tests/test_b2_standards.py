"""Tests for mandatory Backblaze B2 integration standards."""

from app.config.settings import Settings
from app.repo import b2_client, lance_store
from app.repo.b2_standards import B2_USER_AGENT


def test_endpoint_is_derived_from_region():
    settings = Settings(_env_file=None, b2_region="sample-region-001")

    assert settings.b2_endpoint == "https://s3.sample-region-001.backblazeb2.com"


def test_boto3_client_uses_standard_user_agent(monkeypatch):
    captured = {}

    def fake_client(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(b2_client.settings, "b2_region", "sample-region-001")
    monkeypatch.setattr(
        b2_client.settings,
        "b2_application_key_id",
        "sample-key-id",
    )
    monkeypatch.setattr(b2_client.settings, "b2_application_key", "sample-key")
    monkeypatch.setattr(b2_client.boto3, "client", fake_client)
    b2_client.get_s3_client.cache_clear()

    try:
        b2_client.get_s3_client()
    finally:
        b2_client.get_s3_client.cache_clear()

    assert captured["args"] == ("s3",)
    assert captured["kwargs"]["endpoint_url"] == (
        "https://s3.sample-region-001.backblazeb2.com"
    )
    assert captured["kwargs"]["region_name"] == "sample-region-001"
    assert captured["kwargs"]["config"].user_agent_extra == B2_USER_AGENT


def test_lancedb_storage_options_use_b2_standard_names(monkeypatch):
    monkeypatch.setattr(lance_store.settings, "b2_region", "sample-region-001")
    monkeypatch.setattr(
        lance_store.settings,
        "b2_application_key_id",
        "sample-key-id",
    )
    monkeypatch.setattr(lance_store.settings, "b2_application_key", "sample-key")

    options = lance_store._lancedb_storage_options()

    assert options == {
        "region": "sample-region-001",
        "endpoint": "https://s3.sample-region-001.backblazeb2.com",
        "user_agent": B2_USER_AGENT,
        "aws_s3_allow_unsafe_rename": "true",
        "aws_access_key_id": "sample-key-id",
        "aws_secret_access_key": "sample-key",
    }
