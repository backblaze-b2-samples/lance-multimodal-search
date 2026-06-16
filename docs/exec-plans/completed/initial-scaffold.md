# Scaffold plan — `lance-multimodal-search`

> Source of truth for the delta: `.claude/scratch/vcsk-478508b8-ee91-422e-bfe1-ed324c7f2579/`
> (fresh `vibe-coding-starter-kit` clone). Parent standards: `../CLAUDE.md`.
> Technical reference for the LanceDB↔B2 mechanism: the sibling
> `agentic-rag-vector-starter-kit` already proved this exact stack against B2 —
> we reuse its hard-won B2 quirks (env mapping, unsafe-rename, seed-row create),
> but our sample is **fully local / no API key** (CLIP, not OpenAI) and **multimodal**.

---

## 1. Purpose

`lance-multimodal-search` is a B2 sample that demonstrates **object-storage-native
vector search**: the *entire* vector store — source images, embeddings, columnar
metadata, and the ANN index — lives on Backblaze B2, with **no vector-database
server** to run. A user ingests an image corpus into B2, embeds it locally on CPU
with an open-source CLIP model (`sentence-transformers`, `clip-ViT-B-32`, 512-dim),
and writes the vectors into a **Lance table stored directly on B2** via LanceDB.
They then search the corpus by **text** ("a red bicycle on a beach") or by **image**
(drop in a photo, get visually similar ones), and results come back as presigned B2
preview URLs. It's for **design teams, ML engineers, and data scientists** who want
semantic / multimodal search over a media corpus without standing up Pinecone,
Weaviate, or a Postgres+pgvector box. The headline: **B2 is the AI storage substrate,
not a downstream sink** — LanceDB reads and writes the Lance format directly against
B2's S3-compatible API. **Runs on B2 credentials only; no second API key, $0/run.**

---

## 2. Architecture delta from `vibe-coding-starter-kit`

Same monorepo shape: `apps/web` (Next.js 16 + shadcn/ui), `services/api` (FastAPI,
layered `types → config → repo → service → runtime`), `packages/shared` (TS types).
The starter kit is the ceiling — we strip RAG-irrelevant pieces and add the search/index surface.

| KEEP (as-is) | TRIM (remove from starter) | ADD (new for this sample) |
|---|---|---|
| **UI kit** `components/ui/*`, design tokens in `globals.css`, `/design` page (non-negotiable starter contract) | The two starter screenshots `docs/images/b2-starterkit-*.png` + the README "What it looks like" section (real screenshots added later by the publish flow — **do not generate binaries**) | **`/search` page** — core feature: text-query and image-query tabs → nearest-neighbor gallery with similarity scores + presigned previews |
| **Upload** `/upload` route + `components/upload/*` + sidebar entry (non-negotiable) — adapt copy to "add images & PDFs to the corpus", default key prefix → `corpus/` | Starter `docs/exec-plans/completed/*` (the 5 starter plans — not our history) | **`/library` page** — sample-specific asset explorer **scoped to the `corpus/` prefix**: thumbnail grid of ingested images with **index status** (Indexed ✓ / Pending) + a "Build / refresh index" action |
| **File Explorer** (full-bucket browse) `/files` route + `app/files/` + `components/files/*` + sidebar entry (**non-negotiable keep**) | RAG-only deps in `requirements.txt` if present (none in starter — starter has only the base stack) | **`repo/lance_store.py`** — LanceDB-on-B2 vector store (all `lancedb` SDK confined here) |
| **Settings** `/settings` + `components/settings/*` | — | **`repo/embedder.py`** — CLIP adapter (all `sentence-transformers`/`torch` confined here) |
| **Layered backend** + structural tests + observability (`/health`, `/metrics`, JSON logging) | — | **`service/indexing.py`**, **`service/search.py`** + **`runtime/index.py`**, **`runtime/search.py`** |
| **`repo/b2_client.py`** (boto3 layer) — kept, but env-renamed + `region_name` added + UA updated | — | New Pydantic types (`types/search.py`, `types/index.py`) + TS mirrors in `packages/shared` |
| `metadata.py` service + `metadata-extraction` feature (used at upload) | — | LanceDB connectivity added to `/health`; corpus/index metrics added to dashboard |
| TanStack Query data layer (`lib/queries.ts`, `lib/api-client.ts`) — extended, not replaced | — | Sidebar nav entries for **Search** and **Library** |
| **Dashboard** scaffolding — *adapted* (see below), not removed | — | — |

**Dashboard adaptation** (starter contract: the dashboard is the one screen meant to be rewritten):
replace the generic upload stats with **corpus/index metrics** —
stat cards (corpus images, vectors indexed, **vector-store size on B2** = bytes under the
`lancedb/` prefix, embedding model + dim), a chart (indexed vs. pending, or corpus-by-content-type),
and a recent-searches table (backed by a small JSON query log, mirroring the starter's
`download_count.json` durable-counter pattern). All new aggregations flow through
`runtime → service → repo` and are exposed via TanStack Query hooks (no bare `useEffect+fetch`).

**Scope decision (RESOLVED — user chose images + documents):** the corpus holds **both images
and documents (PDFs)**. CLIP embeds images and text into one shared 512-dim space but cannot embed
a PDF directly, so documents are handled by **rendering each page to an image and embedding the page
render with CLIP** — this keeps a single model, a single embedding space, CPU-only, and no API key.
Mechanics:
- **Images** under `corpus/` → embedded directly (one Lance row each).
- **PDFs** under `corpus/` → each page (capped at `MAX_PAGES_PER_DOC`) rendered to a PNG via
  **`pymupdf`/`fitz`** (ships its own libs — **no poppler/system deps**, unlike `pdf2image`), the page
  PNG stored back to B2 under a `derived/pages/{doc_stem}/{page:04d}.png` prefix, and the page render
  embedded with CLIP (one Lance row per page). A short extracted-text snippet (via `pymupdf`/PyPDF2)
  is stored as row metadata for display only — the **vector is always the CLIP image embedding**.
- A search hit may be a standalone image or a document page; the preview is the image or the page
  thumbnail (presigned), with source filename + page number in the metadata.
- **Prefix layout:** source uploads live in `corpus/`; machine-generated page renders live in
  `derived/pages/` (kept out of `corpus/` so the `/library` view shows source assets, not renders).
  The full-bucket `/files` explorer still shows everything (`corpus/`, `derived/`, `lancedb/`).

---

## 3. B2 surface (S3 operations)

**All B2 access is via the S3-compatible API — no b2-native API anywhere** (satisfies Standard #1).

- **boto3 client** (`repo/b2_client.py`, UA `b2ai-lance-multimodal-search`, `region_name=B2_REGION`):
  `put_object` (ingest source files **+ rendered PDF page thumbnails under `derived/pages/`**),
  `list_objects_v2` (corpus listing, full-bucket browse, stats, vector-store byte size under `lancedb/`),
  `get_object` (download source bytes for embedding), `head_object`, `delete_object`,
  `generate_presigned_url` (serve corpus + page-render + result previews), `head_bucket` (health).
- **LanceDB object_store** (Lance's internal S3 client, `lancedb/` prefix): GET/PUT/LIST/DELETE +
  multipart for Lance manifest, data fragments, and ANN index files. Also pure S3 API.

**Two flagged B2 specifics** (both proven necessary by the sibling sample; both documented):
1. **`AWS_S3_ALLOW_UNSAFE_RENAME=true`** — LanceDB commits on S3 normally use conditional PUT
   (`If-None-Match`), which **B2 does not support**. We map B2 creds into `AWS_*` env vars in
   `lance_store.py` and set this flag. Consequence: **single-writer only** — concurrent writers
   to the same table are unsafe. Fine for a single-user demo; documented in `docs/RELIABILITY.md`.
2. **Custom user agent on the LanceDB client** — the Rust `object_store` backing LanceDB does
   **not** expose a UA override through LanceDB's public Python API. So Standard #2's "custom UA on
   every S3 client" is satisfied for the **boto3** client but not for Lance's internal client.
   **Justified deviation**, documented in `ARCHITECTURE.md`. (The sibling sample accepts the same.)

**Empty-schema tables don't persist on B2** — `lance_store.py` creates the table *with data*
(seed-row pattern, then deletes the seed) and includes the open→`count_rows`→drop-if-broken
recovery, exactly as the sibling does, because empty `create_table` calls don't survive on S3.

---

## 4. Key features (seed README list + `docs/features/*.md` stubs)

1. **Semantic & multimodal search** (`semantic-search.md`) — query the corpus by free-text or by
   example image; CLIP puts both in the same 512-dim space; LanceDB ANN over the B2-resident table.
   Hits may be images or document pages.
2. **Document page indexing** (`document-indexing.md`) — PDFs are rendered page-by-page to images
   (`pymupdf`), page thumbnails stored to B2 under `derived/pages/`, each page embedded with CLIP
   (one Lance row per page) so documents are searchable in the same multimodal space.
3. **Corpus library** (`corpus-library.md`) — scoped explorer of ingested images & PDFs with per-item
   index status and a one-click "build / refresh index".
4. **Object-storage-native vector store** (`vector-store.md`) — how the Lance table + ANN index
   live on B2, the AWS_* env mapping, the unsafe-rename / single-writer caveat, seed-row create.
5. **Corpus ingest (upload)** (`file-upload.md`, adapted) — drag-drop images & PDFs into `corpus/`.
6. **File browser** (`file-browser.md`, kept) — full-bucket browse/preview/download/delete.
   *(Dashboard `dashboard.md` rewritten to corpus/index metrics — adaptation, counted under §2.)*

**External API provider: NONE.** Embeddings are computed **locally on CPU** with
`sentence-transformers` (`clip-ViT-B-32`, 512-dim). First run downloads the model from
HuggingFace (~one-time, no key). **Estimated cost for one full demo run: $0** (B2 storage only).
No provider env var needed. This is a deliberate selling point of the sample, consistent with the
api-provider-selection rules (no external API to wire).

**New backend modules (layer placement + rationale):**
- `repo/lance_store.py` — LanceDB vector store on B2; **all `lancedb`/`pyarrow` SDK use confined here**.
- `repo/embedder.py` — CLIP adapter (lazy singleton; `encode_image(bytes) → vec`, `encode_text(str) → vec`);
  **all `sentence-transformers`/`torch` use confined here.** Placed in `repo/` to *contain the external
  ML SDK*, mirroring how boto3 and lancedb are contained — the structural test only mechanically
  enforces boto3-in-repo, but we follow the AGENTS.md "contain external SDKs" intent. Documented so the reviewer doesn't flag it.
- `service/indexing.py` — list corpus via b2_client → for each not-yet-indexed asset: **images** → embed directly;
  **PDFs** → render pages (`pymupdf`), store page PNGs to `derived/pages/`, embed each page → write rows to lance_store; returns index result/status.
- `service/search.py` — embed query (text or image) → `lance_store.search_vectors` → map hits to presigned URLs → log query.
- `runtime/index.py` — `POST /index` (build/refresh), `GET /index/status`.
- `runtime/search.py` — `POST /search/text`, `POST /search/image`.
- `runtime/health.py` — extended to also check LanceDB connectivity.

**New config** (`config/settings.py`): `lancedb_uri` (default `s3://{bucket}/lancedb/`),
`embedding_model` (default `clip-ViT-B-32`), `embedding_dim` (512), `corpus_prefix` (default `corpus/`),
`derived_prefix` (default `derived/pages/`), `max_pages_per_doc` (default e.g. 25), `pdf_render_dpi`
(default e.g. 120), `search_top_k` (default e.g. 24), `query_log_file`, derived `lancedb_storage_uri`.
Env renamed to Standard #3 (§6).

---

## 5. Doc transforms

- **README.md** — rewrite for `lance-multimodal-search`: purpose, "no vector DB server / $0 / B2-only"
  angle, quick start (B2 creds + first-run model download), search & library features, updated commands,
  UTM → `b2ai-lance-multimodal-search`. Remove the "What it looks like" screenshot section (added later by publish).
- **ARCHITECTURE.md** — add `lance_store` + `embedder` repo modules; LanceDB-on-B2 as a data store;
  the AWS_* env mapping + unsafe-rename/single-writer note + UA-deviation note; search/index data flows; EMBEDDING_DIM=512.
- **AGENTS.md** — update repo map + invariants ("`lancedb`/`pyarrow` only in `repo/lance_store.py`;
  `sentence-transformers`/`torch` only in `repo/embedder.py`"), commands.
- **docs/features/** — KEEP+adapt `file-upload.md`, KEEP `file-browser.md`, KEEP `metadata-extraction.md`;
  REWRITE `dashboard.md`; ADD `semantic-search.md`, `document-indexing.md`, `corpus-library.md`, `vector-store.md`.
- **docs/app-workflows.md** — rewrite journeys: ingest (images + PDFs) → build index (PDFs → page renders) → search (text/image) → preview.
- **docs/SECURITY.md** — presigned-URL preview model; corpus prefix validation; rename references.
- **docs/RELIABILITY.md** — LanceDB single-writer caveat (unsafe-rename), seed-row create, first-run model download.
- **docs/dev-workflows.md** — keep; note model download on first run + how to test search/index; fix the `--filter @…/web` package name.
- **docs/exec-plans/completed/** — remove the 5 starter plans; this plan lands here at finalize as `initial-scaffold.md`.

---

## 6. Rename table

| Kind | From (`vibe-coding-starter-kit`) | To (`lance-multimodal-search`) |
|---|---|---|
| Kebab name (repo, README title slug, image tags, workflow slugs) | `vibe-coding-starter-kit` | `lance-multimodal-search` |
| Title Case | `Vibe Coding Starter Kit` | `Lance Multimodal Search` |
| Root pkg `name` (`package.json`) | `vibe-coding-starter-kit` | `lance-multimodal-search` |
| Web pkg `name` | `@vibe-coding-starter-kit/web` | `@lance-multimodal-search/web` |
| Shared pkg `name` | `@vibe-coding-starter-kit/shared` | `@lance-multimodal-search/shared` |
| All TS imports `@vibe-coding-starter-kit/shared` (8+ files) | `@vibe-coding-starter-kit/shared` | `@lance-multimodal-search/shared` |
| `next.config.ts` `transpilePackages` | `@vibe-coding-starter-kit/shared` | `@lance-multimodal-search/shared` |
| All `pnpm --filter @vibe-coding-starter-kit/web …` (package.json, README, dev-workflows) | `@vibe-coding-starter-kit/web` | `@lance-multimodal-search/web` |
| Header brand string (`components/layout/header.tsx`) | `oss-starter-kit` | `lance-multimodal-search` (or "Lance Multimodal Search") |
| boto3 `user_agent_extra` (`repo/b2_client.py`) | `b2ai-oss-start` | `b2ai-lance-multimodal-search` |
| UTM `utm_content=` (sidebar, README ×3, doctor.mjs) | `b2ai-oss-start` | `b2ai-lance-multimodal-search` |
| Env var | `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` (Standard #3) |
| Env var | `B2_ENDPOINT` (keep name) | `B2_ENDPOINT` |
| Env var | *(none)* | **ADD `B2_REGION`** (Standard #3; LanceDB needs it; boto3 `region_name`) |
| Settings fields (`config/settings.py`) | `b2_key_id` | `b2_application_key_id`; add `b2_region` |
| Clone URL in README | `…/vibe-coding-starter-kit.git` | `…/lance-multimodal-search.git` |
| `docs/SECURITY.md` prose | "vibe-coding-starter-kit" | "lance-multimodal-search" |

**Standard #3 env contract (final):** `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`,
`B2_BUCKET_NAME`, `B2_REGION`, `B2_ENDPOINT` (+ optional `B2_PUBLIC_URL`). `.env.example` rewritten
to match, with fake reference values. (Note: starter uses `B2_KEY_ID`/no region; sibling uses
`B2_S3_ENDPOINT`/derived region — we follow the parent **Standard #3** names, which is neither verbatim.)

---

## 7. Build/verify gates (for the builder)

- `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure` must pass.
- Structural tests still pass: boto3 only in `repo/`, layers intact, files < 300 lines, no backward imports.
- New deps in `services/api/requirements.txt`: `lancedb~=0.20.0`, `pyarrow>=18.0.0`,
  `sentence-transformers>=3.0.0` (pulls CPU `torch`), `pymupdf>=1.24.0` (PDF page render, bundles its
  own libs — no system deps). Keep `Pillow` (image handling), `PyPDF2` (text snippet/metadata), `boto3`, base stack.
- `.env.example`, README quick start, and `config/settings.py` agree on the Standard #3 env names.
- No real secrets anywhere (placeholders only); `.env` stays gitignored.
