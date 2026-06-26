<!-- last_verified: 2026-06-26 -->
# Feature: Document Page Indexing

## Purpose
Make PDFs searchable in the same multimodal space as images by rendering each page to an image and embedding the page render with CLIP — one Lance row per page.

## Used By
- API: `POST /index` (PDF branch of the build)
- Job: indexing run triggered from the Library

## Core Functions
- `services/api/app/service/indexing.py` — `_render_pdf_rows()` renders pages (`pymupdf`/`fitz`), stores PNGs, embeds each
- `services/api/app/repo/b2_client.py` — `upload_file()` writes page PNGs under `derived/pages/`
- `services/api/app/repo/embedder.py` — `encode_image()` on each page render
- `services/api/app/repo/lance_store.py` — `add_rows()` writes one row per page

## Canonical Files
- PDF render + embed: `services/api/app/service/indexing.py`

## Inputs
- A PDF object under `corpus/` (raw bytes fetched via `get_object_bytes`)
- Config: `MAX_PAGES_PER_DOC` (default 25), `PDF_RENDER_DPI` (default 120)

## Outputs
- Page PNGs stored at `derived/pages/{doc_stem}/{page:04d}.png` in B2
- One Lance row per page: `kind="pdf_page"`, `page_number`, `preview_key` (the PNG), `text_snippet` (extracted page text, display only), `vector` (CLIP image embedding of the page render)

## Flow
- Indexer encounters a `corpus/` object with content type `application/pdf`
- `pymupdf` opens the PDF from bytes (it bundles its own libs — no poppler/system deps)
- For each page up to `MAX_PAGES_PER_DOC`: render to a pixmap at `PDF_RENDER_DPI`, encode to PNG
- Upload the PNG to `derived/pages/`, extract a short text snippet, embed the render with CLIP
- Append the row to the page-rows batch; the indexer writes the batch to the Lance table
- Page renders live under `derived/` so the Library (scoped to `corpus/`) keeps showing source assets, not renders

## Edge Cases
- PDF with more pages than `MAX_PAGES_PER_DOC` → only the first N pages are indexed
- Encrypted/corrupt PDF → the asset's error is collected in `IndexResult.errors`; indexing continues for other assets
- Rendered page exceeds `MAX_SEARCH_IMAGE_PIXELS` or `MAX_SEARCH_IMAGE_DIMENSION` → the asset's error is collected in `IndexResult.errors`; indexing continues for other assets
- Scanned PDF with no extractable text → `text_snippet` is empty; the **vector is still the page image embedding**, so the page remains searchable

## UX States
- Surfaced through the Library: assets show Pending → Indexed; the build toast reports vectors added (which exceeds asset count when PDFs expand into pages)

## Verification
- Test files: `services/api/tests/test_structure.py` (layering); manual end-to-end for rendering
- Required cases: multi-page PDF expands to N rows; page PNGs appear under `derived/pages/`; a page hit is returned by search
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: tests green; manually, a PDF page is returned for a relevant text or image query

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Semantic & Multimodal Search](semantic-search.md)
- [Corpus Library](corpus-library.md)
- [App Workflows](../app-workflows.md)
