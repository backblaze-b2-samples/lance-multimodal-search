<!-- last_verified: 2026-06-26 -->
# Feature: Semantic & Multimodal Search

## Purpose
Search the corpus by free-text or by example image, returning the most visually/semantically similar assets — images or document pages — as presigned B2 previews.

## Used By
- UI: `/search` page (text-query and image-query tabs), result gallery
- API: `POST /search/text`, `POST /search/image`

## Core Functions
- `apps/web/src/components/search/search-panel.tsx` — text + image query tabs, drives the mutations
- `apps/web/src/components/search/result-gallery.tsx` — nearest-neighbor gallery with scores
- `apps/web/src/lib/queries.ts` — `useTextSearch()`, `useImageSearch()`
- `services/api/app/runtime/search.py` — HTTP handlers
- `services/api/app/service/search.py` — embed query → kNN → presign → log; distance→score mapping
- `services/api/app/repo/embedder.py` — `encode_text()` / `encode_image()` (CLIP)
- `services/api/app/repo/lance_store.py` — `search_vectors()` kNN over the B2-resident table

## Canonical Files
- Search service (scoring): `services/api/app/service/search.py`
- Query panel: `apps/web/src/components/search/search-panel.tsx`

## Inputs
- Text: `{ query: string, top_k?: number }` (JSON)
- Image: `file: File` (multipart)

## Outputs
- `SearchResponse`: `{ query, mode, count, hits[] }`
- Each `SearchHit`: `asset_id, source_key, source_filename, content_type, kind, page_number, text_snippet, score (0..1), preview_url`
- Side effect: one entry appended to the durable search log (dashboard recent-searches)

## Flow
- User submits a text query or drops an example image
- CLIP embeds the query into the shared 512-dim space (`encode_text` / `encode_image`)
- LanceDB runs kNN over the `corpus_assets` table (default `top_k = SEARCH_TOP_K = 24`)
- Squared-L2 distance (range `[0, 4]`, since CLIP vectors are L2-normalized) is mapped to a `0..1` similarity score
- Each hit's `preview_key` (the image, or the PDF page render) is turned into a presigned B2 URL
- The query is logged; the gallery renders previews + scores

## Edge Cases
- Empty text query → 400
- Empty image upload → 400
- Invalid image bytes → 400
- Image larger than 100MB → 413
- Decoded image larger than `MAX_SEARCH_IMAGE_PIXELS` or
  `MAX_SEARCH_IMAGE_DIMENSION` → 400
- No table yet / empty index → empty result list (UI shows "no matches / build the index")
- Presign failure for one hit → that hit returns `preview_url: null` (gallery shows a placeholder)

## UX States
- Empty: "No search yet" prompt
- Loading: spinner on the search button / dropzone
- Error: toast with the API error message
- Loaded: gallery of scored previews; PDF-page hits show source filename + page number

## Verification
- Test files: `services/api/tests/test_search_scoring.py`, `services/api/tests/test_error_handling.py`
- Required cases: distance→score bounds & clamping; seed-row skipped; hit field mapping & presign; invalid image upload returns 400; oversized decoded image returns 400 before model/vector work
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations
- Manual: build an index, run a text query and an image query, confirm scored previews

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Document Page Indexing](document-indexing.md)
- [Object-Storage-Native Vector Store](vector-store.md)
- [App Workflows](../app-workflows.md)
