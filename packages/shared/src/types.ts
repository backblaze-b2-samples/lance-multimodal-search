export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Multimodal search / vector index ---

export type AssetKind = "image" | "pdf";
export type HitKind = "image" | "pdf_page";
export type SearchMode = "text" | "image";

export interface SearchHit {
  asset_id: string;
  source_key: string;
  source_filename: string;
  content_type: string;
  kind: HitKind;
  page_number: number;
  text_snippet: string;
  score: number;
  preview_url: string | null;
}

export interface SearchResponse {
  query: string;
  mode: SearchMode;
  count: number;
  hits: SearchHit[];
}

export interface CorpusItem {
  key: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string;
  kind: AssetKind;
  indexed: boolean;
}

export interface IndexResult {
  indexed_assets: number;
  new_vectors: number;
  skipped_already_indexed: number;
  errors: string[];
}

export interface IndexStatus {
  corpus_total: number;
  corpus_indexed: number;
  corpus_pending: number;
  total_vectors: number;
  embedding_model: string;
  embedding_dim: number;
  vector_store_size_bytes: number;
  vector_store_size_human: string;
}

export interface RecentSearch {
  ts: string;
  mode: SearchMode;
  query: string;
  result_count: number;
  top_score: number | null;
}
