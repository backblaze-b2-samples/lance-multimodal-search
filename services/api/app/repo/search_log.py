"""Durable recent-searches log — a small JSON file on local disk.

Mirrors the starter kit's ``download_count.json`` durable-counter pattern: a
single JSON file holding the most recent search events for the dashboard's
recent-searches table. Not on the hot path, so a simple lock + atomic rewrite
is sufficient. No SDK use here.
"""

import contextlib
import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 50
_lock = Lock()


def _log_path() -> Path:
    p = Path(settings.query_log_file)
    if not p.is_absolute():
        # Anchor at services/api/ (three levels up from this file).
        p = Path(__file__).resolve().parents[2] / p
    return p


def _read_all() -> list[dict]:
    try:
        with open(_log_path()) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return []


def _write_all(entries: list[dict]) -> None:
    path = _log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(entries, f)
            os.replace(tmp, path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
    except OSError as e:
        logger.warning("Failed to persist search log: %s", e)


def log_search(mode: str, query: str, result_count: int, top_score: float | None) -> None:
    """Append a search event, keeping only the most recent _MAX_ENTRIES."""
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "mode": mode,
        "query": query,
        "result_count": result_count,
        "top_score": top_score,
    }
    with _lock:
        entries = _read_all()
        entries.insert(0, entry)
        _write_all(entries[:_MAX_ENTRIES])


def get_recent_searches(limit: int = 20) -> list[dict]:
    """Return the most recent search events (newest first)."""
    with _lock:
        return _read_all()[:limit]
