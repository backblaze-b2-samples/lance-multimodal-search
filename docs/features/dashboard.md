<!-- last_verified: 2026-06-11 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance overview of the corpus and its B2-resident vector index: how much is indexed, how big the vector store is, and what was recently searched.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /index/status`, `GET /dashboard/recent-searches`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards (corpus assets, vectors indexed, vector-store size on B2, embedding model + dim)
- `apps/web/src/components/dashboard/upload-chart.tsx` — `IndexCoverageChart` (indexed vs. pending)
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — `RecentSearchesTable` (last searches)
- `apps/web/src/lib/queries.ts` — `useIndexStatus()`, `useRecentSearches()`
- `services/api/app/runtime/index.py` — `GET /index/status`
- `services/api/app/runtime/dashboard.py` — `GET /dashboard/recent-searches`
- `services/api/app/service/indexing.py` — `get_index_status()` aggregation
- `services/api/app/repo/search_log.py` — durable recent-searches JSON log

## Canonical Files
- Stat cards: `apps/web/src/components/dashboard/stats-cards.tsx`
- Index-status aggregation: `services/api/app/service/indexing.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /index/status` → `IndexStatus`: `corpus_total, corpus_indexed, corpus_pending, total_vectors, embedding_model, embedding_dim, vector_store_size_bytes, vector_store_size_human`
- `GET /dashboard/recent-searches?limit=10` → `RecentSearch[]`: `ts, mode, query, result_count, top_score`

## Flow
- Page loads → `useIndexStatus()` + `useRecentSearches()` fire in parallel
- Stat cards show corpus assets (+ pending), vectors indexed, vector-store size on B2 (paginated byte sum under `lancedb/`), and the embedding model + dim
- The index-coverage chart shows indexed vs. pending assets
- The recent-searches table shows the latest queries with mode (text/image), hit count, and top score

## Edge Cases
- API unavailable → cards/chart/table show inline ErrorState (not misleading zeros)
- Empty corpus / no index → empty-state messages guiding the user to upload + build
- No searches yet → recent-searches empty state
- Large bucket → vector-store size paginates through `lancedb/` via `ContinuationToken`

## UX States
- Loading: skeleton placeholders for cards and table
- Empty: "Corpus is empty" / "Nothing indexed yet" / "No searches yet"
- Error: inline ErrorState with Retry
- Loaded: populated cards, coverage chart, recent-searches table

## Verification
- Test files: `services/api/tests/test_search_scoring.py` (scoring feeding `top_score`); manual for metrics
- Required cases: status reflects index state; recent searches logged after a query; API error fallback
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Corpus Library](corpus-library.md)
- [App Workflows](../app-workflows.md)
