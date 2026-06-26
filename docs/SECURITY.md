<!-- last_verified: 2026-06-26 -->
# Security

Security principles and implementation for lance-multimodal-search.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4 (boto3 client). LanceDB's internal S3 client uses the same credentials via storage options in `app/repo/lance_store.py`.
- **Client -> B2**: Short-lived presigned URLs for previews — no public bucket required

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against the allowlist
- Chunked streaming with size enforcement (100MB default)
- Content-type allowlist is **images + PDFs only** (the searchable corpus); other types are rejected (415)
- Empty file rejection
- Source assets are written under the `corpus/` prefix; machine-generated PDF page renders go under `derived/pages/`

## Preview Model

- Search results, library thumbnails, and file previews are served via **presigned B2 URLs** generated server-side (`generate_presigned_url`), so the bucket can stay private
- Presigned URLs are short-lived; the frontend re-fetches them as needed (TanStack Query, short staleTime)

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The corpus listing is scoped to the `corpus/` prefix; the full-bucket Files explorer intentionally shows everything (`corpus/`, `derived/`, `lancedb/`)
- The bucket is the access boundary — add stricter prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
