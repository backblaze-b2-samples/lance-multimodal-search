<!-- last_verified: 2026-06-11 -->
# Feature: Corpus Library

## Purpose
A `corpus/`-scoped explorer of ingested images & PDFs with per-item index status and a one-click "build / refresh index" action.

## Used By
- UI: `/library` page, corpus grid
- API: `GET /corpus`, `POST /index`

## Core Functions
- `apps/web/src/components/library/corpus-grid.tsx` — thumbnail grid, status badges, build button
- `apps/web/src/lib/queries.ts` — `useCorpus()`, `useBuildIndex()`, `usePreviewUrl()`
- `services/api/app/runtime/index.py` — `GET /corpus`, `POST /index` handlers
- `services/api/app/service/indexing.py` — `list_corpus()`, `build_index()`
- `services/api/app/repo/lance_store.py` — `get_indexed_keys()` for status
- `services/api/app/repo/b2_client.py` — `list_files(prefix="corpus/")`

## Canonical Files
- Corpus grid: `apps/web/src/components/library/corpus-grid.tsx`
- Listing + status logic: `services/api/app/service/indexing.py`

## Inputs
- None for listing (`GET /corpus`)
- Build action: no body (`POST /index`)

## Outputs
- `CorpusItem[]`: `key, filename, content_type, size_bytes, size_human, uploaded_at, kind ("image"|"pdf"), indexed (bool)`
- Build action returns `IndexResult`: `indexed_assets, new_vectors, skipped_already_indexed, errors[]`

## Flow
- Page loads `GET /corpus`: lists `corpus/` (images + PDFs only), marks each as Indexed if its key is in the Lance table (`get_indexed_keys()`)
- Images get a presigned B2 thumbnail; PDFs show a document glyph (their page renders live under `derived/`)
- User clicks **Build / refresh index** → `POST /index` → indexer processes only Pending assets (idempotent/resumable)
- On success, the corpus + index-status caches are invalidated so badges and dashboard metrics refresh

## Edge Cases
- Empty corpus → empty-state prompt to upload
- All assets already indexed → "all indexed", build is a no-op (everything skipped)
- Partial failure during build → per-asset errors surfaced via toast; successful assets still indexed
- API unreachable → inline ErrorState with Retry

## UX States
- Loading: skeleton thumbnails
- Empty: "Corpus is empty"
- Error: inline ErrorState
- Loaded: grid with Indexed ✓ / Pending badges and a build button

## Verification
- Test files: `services/api/tests/test_structure.py` (layering); manual for the build action
- Required cases: list reflects index status; build indexes only pending; build is idempotent on re-run
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: tests green; manually, badges flip Pending → Indexed after a build

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Document Page Indexing](document-indexing.md)
- [Object-Storage-Native Vector Store](vector-store.md)
- [App Workflows](../app-workflows.md)
