<!-- last_verified: 2026-06-11 -->
# App Workflows

User journeys inside the application. The core loop is **ingest → build index → search → preview**.

## Ingest images & PDFs (Upload)

- User navigates to `/upload`
- Drops or selects images (`jpg/png/gif/webp`) and/or PDFs in the dropzone
- Client validates file size (max 100MB) and type (images + PDFs only)
- Progress bar shows per-file status; on success a toast confirms
- Files are stored under the `corpus/` prefix in B2 (distinct from machine-generated renders under `derived/`)
- See: [Corpus Ingest (Upload)](features/file-upload.md)

## Build / refresh the index (Library)

- User navigates to `/library`
- The page lists `corpus/` assets as a thumbnail grid, each tagged **Indexed ✓** or **Pending**
- User clicks **Build / refresh index** (`POST /index`)
- The backend lists the corpus, skips already-indexed keys, then for each new asset:
  - **Image** → embed directly with CLIP → one Lance row
  - **PDF** → render each page (capped at `MAX_PAGES_PER_DOC`) to a PNG via `pymupdf`, store the PNG under `derived/pages/`, embed the page render with CLIP → one Lance row per page
- On the **first** run, the CLIP model weights download from HuggingFace (one-time, no key) — this run is slower
- A toast reports assets indexed and vectors added; the status badges flip to Indexed
- See: [Corpus Library](features/corpus-library.md), [Document Page Indexing](features/document-indexing.md)

## Search by text or image

- User navigates to `/search`
- **Text query tab**: type a free-text description (e.g. "a red bicycle on a beach") → `POST /search/text`
- **Image query tab**: drop in an example image → `POST /search/image`
- The backend embeds the query (CLIP text or image), runs kNN over the B2-resident Lance table, and returns the nearest neighbors
- Results render as a gallery of presigned previews, each with a similarity score; a hit may be a standalone image or a PDF page (page number + source filename shown)
- The search is logged for the dashboard's recent-searches table
- See: [Semantic & Multimodal Search](features/semantic-search.md)

## View the dashboard

- User navigates to `/` (home)
- Stat cards show: corpus assets (and pending count), vectors indexed, vector-store size on B2 (`lancedb/` prefix), embedding model + dim
- The index-coverage chart shows indexed vs. pending assets
- The recent-searches table shows the latest queries with hit count and top score
- Empty states guide first-time users to upload and build the index
- See: [Dashboard](features/dashboard.md)

## Browse the full bucket (Files)

- User navigates to `/files`
- Full-bucket tree view shows everything: `corpus/`, `derived/`, and `lancedb/`
- Hover a row to preview / download / delete
- See: [File Browser](features/file-browser.md)
