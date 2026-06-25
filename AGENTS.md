<!-- last_verified: 2026-06-25 -->
# AGENTS.md

This is the authoritative control surface for all coding agents. Read this first.

This is `lance-multimodal-search`: object-storage-native multimodal vector
search. The vector store (Lance table + ANN index) lives directly on Backblaze
B2; embeddings are computed locally on CPU with CLIP (no external API key).

## 1. Repository Map

```
apps/web/          Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
                   Search, Library, Dashboard, Upload, Files, Settings
services/api/      FastAPI backend (layered: types/config/repo/service/runtime)
packages/shared/   Shared TypeScript types
docs/              System of record (features, workflows, security, reliability)
docs/exec-plans/   Execution plans and tech debt tracker
infra/railway/     Deployment config
```

Key backend modules for this app:
- `app/repo/lance_store.py` — LanceDB vector store on B2 (all `lancedb`/`pyarrow` here)
- `app/repo/embedder.py` — CLIP adapter (all `sentence-transformers`/`torch` here)
- `app/service/indexing.py` — corpus → embeddings → Lance rows (PDF page render via `pymupdf`)
- `app/service/search.py` — query embed → kNN → presigned previews → query log

## 2. Building on This Starter Kit

When this repo is used as the foundation for a new app, the following pieces are part of the starter contract — keep them. Adapt only what the new use case actually requires.

**Keep as-is (do not strip, rename, or replace)**
- **UI kit / design system.** `apps/web/src/components/ui/` (shadcn primitives), the design tokens in `apps/web/src/app/globals.css`, and the `/design` reference page. Build new screens with these primitives; never edit the generated `components/ui/` files directly. Restyling happens through tokens in `globals.css`.
- **File Explorer.** `/files` route, `apps/web/src/app/files/`, and `apps/web/src/components/files/`. The Files sidebar entry in `apps/web/src/components/layout/app-sidebar.tsx` stays.
- **Upload.** `/upload` route, `apps/web/src/app/upload/`, and `apps/web/src/components/upload/`. The Upload sidebar entry stays.
- The shared sidebar nav (Dashboard, Upload, Files, Settings, plus the Design System utility link). This app **adds** Search and Library nav entries alongside them.

**This app's surface (built on the contract)**
- **Search.** `/search` route, `apps/web/src/components/search/`. Core feature: text-query and image-query tabs → nearest-neighbor gallery with similarity scores + presigned previews.
- **Library.** `/library` route, `apps/web/src/components/library/`. `corpus/`-scoped explorer with per-asset index status + a build/refresh action.
- **Dashboard (adapted).** `/` route and `apps/web/src/components/dashboard/` now show **corpus & index metrics** (corpus assets, vectors indexed, vector-store size on B2, embedding model), an index-coverage chart, and a recent-searches table backed by `app/repo/search_log.py`. All aggregations flow through `runtime -> service -> repo` and are exposed via TanStack Query hooks in `apps/web/src/lib/queries.ts` — no bare `useEffect + fetch`.
- Update `docs/features/dashboard.md` in the same PR as any dashboard change (see §9).

**Why this contract exists**
- The UI kit, Files, and Upload pages are the reusable B2-backed scaffolding — stripping them defeats the purpose. The dashboard is the screen explicitly designed to be rewritten per app.

## 3. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` outside `repo/`
- **`lancedb`/`pyarrow` only in `repo/lance_store.py`**; **`sentence-transformers`/`torch` only in `repo/embedder.py`** — external SDKs are contained in `repo/` (the structural test mechanically enforces only `boto3`-in-repo; honor the same intent for the rest). `pymupdf` is a render lib used only in `service/indexing.py`.
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

## 4. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 5. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 6. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 7. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §9).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 8. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 9. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Execution plans | `docs/exec-plans/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 10. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 11. When Unsure

- Prefer boring, stable libraries
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes
