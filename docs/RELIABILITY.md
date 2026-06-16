<!-- last_verified: 2026-06-11 -->
# Reliability

Reliability expectations and practices for this project.

## LanceDB on B2 — single-writer constraint

- The vector store lives on B2 via LanceDB's S3 backend. LanceDB commits on S3 normally use a conditional PUT (`If-None-Match`), which **B2 does not support**, so `app/repo/lance_store.py` sets `AWS_S3_ALLOW_UNSAFE_RENAME=true`.
- **Consequence: single-writer only.** Concurrent writers to the same Lance table are unsafe and can corrupt it. This sample is a single-user demo, so one indexing run at a time is the assumption. For multi-writer production use, front the table with a single writer process or a queue.
- **Seed-row create / recovery.** Empty-schema `create_table` calls don't persist on S3 backends, so the table is created **with a seed row** which is then deleted. `ensure_table_ready()` (called at startup) opens the table, counts rows, and **drops + recreates** it if it's broken.

## First-run model download

- Embeddings use `clip-ViT-B-32` via `sentence-transformers`, loaded **locally on CPU with no API key**.
- The model weights download lazily from HuggingFace on the **first** search/index call (a one-time, key-free fetch), then are cached on disk. The first indexing/search run is therefore slower; subsequent runs are fast.
- The model is a lazy singleton (`functools.lru_cache`) so it's loaded once per process.

## Health Checks

- `GET /health` verifies **both** B2 connectivity and LanceDB reachability, returning `healthy` or `degraded` with `b2_connected` / `lancedb_connected` flags
- Health endpoint is always available, even when B2 or LanceDB is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Search over an empty / missing index returns an empty result list (not an error)
- Indexing collects per-asset failures in `IndexResult.errors` and continues — one bad PDF doesn't abort the whole run
- A presign failure for a single search hit yields `preview_url: null` (placeholder thumbnail) rather than failing the response
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
