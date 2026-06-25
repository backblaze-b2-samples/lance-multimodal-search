<!-- last_verified: 2026-06-25 -->
# Feature: Metadata Extraction

## Purpose
Extract rich metadata from uploaded files and return it alongside upload results.

## Used By
- API: `POST /upload` (called after B2 upload)
- UI: upload results, file metadata panel

## Core Functions
- `services/api/app/service/metadata.py` — `extract_metadata()`, `_extract_image_metadata()`, `_extract_pdf_metadata()`
- `apps/web/src/components/files/file-metadata-panel.tsx` — displays metadata in structured card

## Canonical Files
- Metadata extraction pattern: `services/api/app/service/metadata.py`
- Metadata display component: `apps/web/src/components/files/file-metadata-panel.tsx`

## Inputs
- file_data: bytes
- filename: string
- content_type: string

## Outputs
- `FileMetadataDetail`: filename, size_bytes, size_human, mime_type, extension, md5, sha256, uploaded_at
- Image-specific (optional): image_width, image_height, exif dict
- PDF-specific (optional): pdf_pages, pdf_author, pdf_title

## Flow
- Upload route receives file and stores in B2
- `extract_metadata()` called with file bytes, filename, content type
- Computes MD5 and SHA-256 hashes
- If image: opens with Pillow, extracts dimensions and EXIF data
- If PDF: opens with `pymupdf`/`fitz`, reads page count from the document, and extracts author/title from document metadata
- Returns `FileMetadataDetail` model
- Frontend displays metadata in file-metadata-panel component

## Edge Cases
- Corrupt image → Pillow metadata extraction logs a warning, image fields remain null
- Corrupt PDF → `pymupdf` metadata extraction logs a warning, PDF fields remain null
- Unknown content type → only common fields populated (hashes, size, extension)
- Audio/video files → `duration_seconds`, `codec`, and `bitrate` response fields exist but remain null
- EXIF contains binary data → decoded as UTF-8 with replace, converted to string
- Large file → hashing may be slow (computed in-memory)

## UX States
- Not applicable (metadata is part of upload response and file preview)

## Verification
- Test files: `services/api/tests/test_metadata.py`
- Covered cases: PDF with metadata, PDF metadata normalization, corrupt PDF handling
- Additional recommended cases: image with EXIF, image without EXIF, PDF without metadata, unknown file type
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [File Upload](file-upload.md)
