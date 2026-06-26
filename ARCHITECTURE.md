<!-- last_verified: 2026-06-25 -->
# Architecture

`lance-multimodal-search` demonstrates **object-storage-native vector search**: the entire vector store — source assets, embeddings, columnar metadata, and the ANN index — lives on Backblaze B2, with no vector-database server. Embeddings are computed locally on CPU with CLIP (no external API key).

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - **Search** — text-query and image-query tabs → nearest-neighbor gallery with similarity scores + presigned previews
  - **Library** — `corpus/`-scoped explorer of ingested images & PDFs with per-item index status + a build/refresh action
  - **Dashboard** — corpus & index metrics, index-coverage chart, recent-searches table
  - File upload (drag-and-drop into `corpus/`), full-bucket file browser, dark mode
- **services/api/** — FastAPI backend (layered architecture)
  - Indexing (corpus → embeddings → Lance rows) and search (query → kNN → presigned previews)
  - B2 S3 integration via boto3; LanceDB vector store on B2
  - PDF metadata extraction and page rendering (pymupdf); CLIP embeddings (sentence-transformers, CPU)
  - `/health` (B2 **and** LanceDB connectivity), JSON logging, `/metrics`
- **packages/shared/** — TypeScript types mirroring the Pydantic models

## Backend Layering

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access & external SDKs (boto3, lancedb, sentence-transformers) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` → `config` → `repo` → `service` → `runtime`
2. No backward imports (e.g. service must not import from runtime)
3. **External SDKs are contained in `repo/`**: `boto3` (S3 client), `lancedb`/`pyarrow` (vector store), and `sentence-transformers`/`torch` (CLIP) are each confined to a single repo module. The structural test mechanically enforces `boto3`-in-repo; the others follow the same "contain external SDKs" intent. `pymupdf` is the PDF library for rendering and metadata extraction in `service/indexing.py` and `service/metadata.py`.
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                   App entrypoint, middleware, router registration, LanceDB table init
  app/
    types/                  Pydantic models (files, upload, stats, search, index)
    config/                 Settings (B2 creds, LanceDB URI, CLIP model, prefixes, PDF/search knobs)
    repo/
      b2_client.py          boto3 S3 client (UA lance-multimodal-search (backblaze-b2-samples), region_name=B2_REGION)
      lance_store.py        LanceDB vector store on B2 — all lancedb/pyarrow confined here
      embedder.py           CLIP adapter — all sentence-transformers/torch confined here
      search_log.py         Durable recent-searches JSON log (dashboard table)
    service/
      indexing.py           list corpus → embed images / render+embed PDF pages → write Lance rows
      search.py             embed query (text/image) → kNN → presigned previews → log query
      upload.py, files.py, metadata.py, dashboard.py
    runtime/                FastAPI route handlers (search, index, files, upload, health, metrics, dashboard)
  tests/                    pytest (structural + integration + scoring)
```

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store. Three prefixes:
  - `corpus/` — source images & PDFs the user uploads (what the Library shows)
  - `derived/pages/` — machine-generated PDF page renders (PNGs), kept out of `corpus/`
  - `lancedb/` — the Lance table, data fragments, and ANN index
- **LanceDB on B2** — the vector store. Connected at `s3://{B2_BUCKET_NAME}/lancedb/`. Lance's internal Rust `object_store` client performs all GET/PUT/LIST/DELETE + multipart against B2's S3 API. There is **no separate database server**.

### The B2 ↔ LanceDB mechanism

`app/repo/lance_store.py` contains all the B2-specific wiring:

1. **B2 storage options.** LanceDB receives B2 credentials, region, derived endpoint, and the sample user agent through `storage_options`, not through extra public env aliases.
2. **`aws_s3_allow_unsafe_rename=true`.** LanceDB commits on S3 normally use a conditional PUT (`If-None-Match`) that **B2 does not support**; the unsafe-rename option bypasses it. **Consequence: single-writer only** — concurrent writers to the same table are unsafe. Fine for a single-user demo; see [docs/RELIABILITY.md](docs/RELIABILITY.md).
3. **Custom user agents.** The boto3 client and LanceDB object-store client both use `lance-multimodal-search (backblaze-b2-samples)` so B2 request logs identify this sample.

**Seed-row create.** Empty-schema `create_table` calls don't persist reliably on S3 backends, so `lance_store.py` creates the table *with* a seed row, then deletes the row (and includes open→`count_rows`→drop-if-broken recovery). See `ensure_table_ready()`.

### Embeddings

- Model: `clip-ViT-B-32` via `sentence-transformers`, **CPU, no API key**. `EMBEDDING_DIM = 512`.
- Both images and text embed into the same 512-dim space, which is what makes text↔image and image↔image search work with a single model.
- Vectors are L2-normalized; LanceDB's default squared-L2 distance (range `[0, 4]`) is mapped to a `0..1` similarity score in `service/search.py`.

## Data Flows

- **Upload (ingest)**: Browser → `POST /upload` (multipart, images/PDFs) → validated → `repo.upload_file` writes to `corpus/`.
- **Index**: Browser → `POST /index` → `service.indexing.build_index` lists `corpus/`, skips already-indexed keys, then for each asset: **image** → `embedder.encode_image` → one Lance row; **PDF** → render each page (`pymupdf`) → store PNG to `derived/pages/` → `embedder.encode_image` → one Lance row per page → `lance_store.add_rows`.
- **Text search**: Browser → `POST /search/text` → `embedder.encode_text` → `lance_store.search_vectors` → map hits to presigned previews → log query.
- **Image search**: Browser → `POST /search/image` (multipart) → `embedder.encode_image` → same path.
- **Status / metrics**: `GET /index/status` aggregates corpus counts, vector count (`lance_store.get_table_stats`), and vector-store byte size (`b2_client.get_prefix_size("lancedb/")`).
- **List / download / delete**: unchanged from the starter (full-bucket browse via S3 `list_objects_v2` / `head_object`, presigned URLs, `delete_object`).

## Observability

- Structured JSON logging on all requests with `request_id`; request timing middleware
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint — checks **both** B2 connectivity and LanceDB reachability

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently` (web `:3000`, API `:8000`)
- **Railway** — two services from the same repo; see `infra/railway/README.md`

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md).

- **Frontend → API** — CORS-restricted to configured origins
- **API → B2** — authenticated via application keys, signature v4
- **Client → B2** — short-lived presigned URLs for previews (no public bucket required)

## Canonical Files

- LanceDB vector store (B2 quirks): `services/api/app/repo/lance_store.py`
- CLIP embedder: `services/api/app/repo/embedder.py`
- Indexing service: `services/api/app/service/indexing.py`
- Search service (scoring): `services/api/app/service/search.py`
- B2 data access: `services/api/app/repo/b2_client.py`
- Config: `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client / hooks: `apps/web/src/lib/api-client.ts`, `apps/web/src/lib/queries.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — single-writer caveat, seed-row create, model download
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
