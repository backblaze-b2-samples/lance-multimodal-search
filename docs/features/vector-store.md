<!-- last_verified: 2026-06-26 -->
# Feature: Object-Storage-Native Vector Store

## Purpose
Run a complete vector store — the Lance table, data fragments, and ANN index — directly on Backblaze B2, with no separate vector-database server. This is the headline of the sample: **B2 is the AI storage substrate, not a downstream sink.**

## Used By
- API: every indexing and search call (the store is the backbone)
- Job: `ensure_table_ready()` at app startup
- UI: `/index/status` powers the dashboard vector-store metrics

## Core Functions
- `services/api/app/repo/lance_store.py` — all `lancedb`/`pyarrow` usage; connect, create, add, search, stats, connectivity
- `services/api/app/config/settings.py` — `lancedb_storage_uri` → `s3://{bucket}/lancedb/`
- `services/api/main.py` — calls `ensure_table_ready()` in the lifespan

## Canonical Files
- Vector store + B2 quirks: `services/api/app/repo/lance_store.py`

## Inputs
- B2 credentials and region, passed to LanceDB as storage options
- `LANCEDB_URI` (optional override; defaults to the B2 bucket path)

## Outputs
- A persistent Lance table `corpus_assets` on B2 under `lancedb/`
- Schema: `asset_id, source_key, source_filename, content_type, kind, preview_key, page_number, text_snippet, indexed_at, vector(list<float32>[512])`

## Flow & B2 specifics
- **B2 storage options.** `lance_store.py` passes the B2 credentials, region, derived endpoint, and sample user agent directly to LanceDB.
- **`aws_s3_allow_unsafe_rename=true`.** LanceDB commits on S3 normally use a conditional PUT (`If-None-Match`) that **B2 does not support**. This option bypasses it. **Consequence: single-writer only** (see [RELIABILITY.md](../RELIABILITY.md)).
- **Seed-row create.** Empty-schema `create_table` calls don't persist on S3 backends, so the table is created **with a seed row**, then the row is deleted. `ensure_table_ready()` also opens → `count_rows` → drops-if-broken for recovery.
- **Custom user agent.** Both the boto3 client and LanceDB object-store client use `lance-multimodal-search (backblaze-b2-samples)`.
- **kNN search.** `search_vectors(vector, k)` runs `table.search(vector).limit(k)`; the service maps the returned `_distance` to a `0..1` score.

## Edge Cases
- Table missing at first insert → created with data (reliable on S3/B2)
- Broken/half-written table → dropped and recreated by `ensure_table_ready()`
- Concurrent writers → unsafe (single-writer constraint); fine for a single-user demo
- B2 unreachable → `check_lancedb_connectivity()` returns False; `/health` reports `lancedb_connected: false`

## UX States
- Surfaced on the dashboard: "Vector Store on B2" stat card (bytes under `lancedb/`), vectors indexed, embedding model + dim

## Verification
- Test files: `services/api/tests/test_structure.py` (confines `lancedb`/`pyarrow` to repo); manual for B2 persistence
- Required cases: table persists across restarts; search returns rows; `/health` reports LanceDB status
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: tests green; manually, the Lance objects appear under `lancedb/` in the bucket and survive a restart

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [RELIABILITY.md](../RELIABILITY.md)
- [Semantic & Multimodal Search](semantic-search.md)
