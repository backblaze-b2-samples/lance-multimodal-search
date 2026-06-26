"""Tests for mandatory Backblaze B2 integration standards."""

import pytest
from pydantic import ValidationError

from app.config.settings import Settings
from app.repo import b2_client, lance_store
from app.repo.b2_standards import B2_USER_AGENT

VALID_REGION = "aa-test-001"


def test_endpoint_is_derived_from_region():
    settings = Settings(_env_file=None, b2_region=VALID_REGION)

    assert settings.b2_endpoint == f"https://s3.{VALID_REGION}.backblazeb2.com"


def test_region_placeholder_is_allowed_for_startup_validation():
    settings = Settings(_env_file=None, b2_region="your_b2_region")

    assert settings.b2_endpoint == ""


@pytest.mark.parametrize(
    "payload",
    [
        f"{VALID_REGION}/evil",
        f"{VALID_REGION}:443",
        f"user@{VALID_REGION}",
        f"{VALID_REGION}?bucket=evil",
        f"{VALID_REGION}#fragment",
        "aa test 001",
        f"{VALID_REGION}\nother",
        f"{VALID_REGION}\t",
    ],
)
def test_unsafe_region_payloads_fail_settings_validation(payload):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, b2_region=payload)


def test_legacy_b2_dotenv_keys_do_not_block_settings(tmp_path):
    legacy_endpoint_key = "B2_" + "ENDPOINT"
    legacy_public_url_key = "B2_" + "PUBLIC_URL"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"{legacy_endpoint_key}=https://s3.{VALID_REGION}.backblazeb2.com",
                f"{legacy_public_url_key}=https://legacy.example.com",
                f"B2_REGION={VALID_REGION}",
                "B2_APPLICATION_KEY_ID=sample-key-id",
                "B2_APPLICATION_KEY=sample-key",
                "B2_BUCKET_NAME=sample-bucket",
                "B2_PUBLIC_URL_BASE=https://public.example.com",
            ]
        )
    )

    settings = Settings(_env_file=env_file)

    assert settings.b2_region == VALID_REGION
    assert settings.b2_endpoint == f"https://s3.{VALID_REGION}.backblazeb2.com"
    assert settings.b2_public_url_base == "https://public.example.com"


def test_boto3_client_uses_standard_user_agent(monkeypatch):
    captured = {}

    def fake_client(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(b2_client.settings, "b2_region", VALID_REGION)
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
        f"https://s3.{VALID_REGION}.backblazeb2.com"
    )
    assert captured["kwargs"]["region_name"] == VALID_REGION
    assert captured["kwargs"]["config"].user_agent_extra == B2_USER_AGENT


def test_lancedb_storage_options_use_b2_standard_names(monkeypatch):
    captured = {}

    class FakeDb:
        def table_names(self):
            return []

    def fake_connect(uri, *, storage_options):
        captured["uri"] = uri
        captured["storage_options"] = storage_options
        return FakeDb()

    monkeypatch.setattr(lance_store.settings, "b2_region", VALID_REGION)
    monkeypatch.setattr(lance_store.settings, "b2_bucket_name", "sample-bucket")
    monkeypatch.setattr(
        lance_store.settings,
        "b2_application_key_id",
        "sample-key-id",
    )
    monkeypatch.setattr(lance_store.settings, "b2_application_key", "sample-key")
    monkeypatch.setattr(lance_store.lancedb, "connect", fake_connect)
    lance_store.get_db.cache_clear()

    try:
        lance_store.get_db()
    finally:
        lance_store.get_db.cache_clear()

    assert captured["uri"] == "s3://sample-bucket/lancedb/"
    assert captured["storage_options"] == {
        "region": VALID_REGION,
        "endpoint": f"https://s3.{VALID_REGION}.backblazeb2.com",
        "user_agent": B2_USER_AGENT,
        "aws_s3_allow_unsafe_rename": "true",
        "aws_access_key_id": "sample-key-id",
        "aws_secret_access_key": "sample-key",
    }


def test_lancedb_omits_incomplete_credential_pair(monkeypatch):
    captured = {}

    class FakeDb:
        def table_names(self):
            return []

    def fake_connect(uri, *, storage_options):
        captured["storage_options"] = storage_options
        return FakeDb()

    monkeypatch.setattr(lance_store.settings, "b2_region", VALID_REGION)
    monkeypatch.setattr(lance_store.settings, "b2_bucket_name", "sample-bucket")
    monkeypatch.setattr(
        lance_store.settings,
        "b2_application_key_id",
        "sample-key-id",
    )
    monkeypatch.setattr(lance_store.settings, "b2_application_key", "")
    monkeypatch.setattr(lance_store.lancedb, "connect", fake_connect)
    lance_store.get_db.cache_clear()

    try:
        lance_store.get_db()
    finally:
        lance_store.get_db.cache_clear()

    assert "aws_access_key_id" not in captured["storage_options"]
    assert "aws_secret_access_key" not in captured["storage_options"]


def test_lancedb_local_uri_omits_storage_options(monkeypatch, tmp_path):
    captured = {}

    class FakeDb:
        def table_names(self):
            return []

    def fake_connect(uri, **kwargs):
        captured["uri"] = uri
        captured["kwargs"] = kwargs
        return FakeDb()

    monkeypatch.setattr(lance_store.settings, "lancedb_uri", str(tmp_path))
    monkeypatch.setattr(lance_store.settings, "b2_region", VALID_REGION)
    monkeypatch.setattr(
        lance_store.settings,
        "b2_application_key_id",
        "sample-key-id",
    )
    monkeypatch.setattr(lance_store.settings, "b2_application_key", "sample-key")
    monkeypatch.setattr(lance_store.lancedb, "connect", fake_connect)
    lance_store.get_db.cache_clear()

    try:
        lance_store.get_db()
    finally:
        lance_store.get_db.cache_clear()

    assert captured["uri"] == str(tmp_path)
    assert captured["kwargs"] == {}
