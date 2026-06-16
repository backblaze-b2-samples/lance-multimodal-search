"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  buildIndex,
  deleteFile,
  getCorpus,
  getFiles,
  getFileStats,
  getIndexStatus,
  getPreviewUrl,
  getRecentSearches,
  getUploadActivity,
  searchImage,
  searchText,
} from "@/lib/api-client";
import type {
  CorpusItem,
  FileMetadata,
  IndexStatus,
  RecentSearch,
} from "@lance-multimodal-search/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  indexStatus: () => [...qk.all, "index", "status"] as const,
  corpus: () => [...qk.all, "corpus"] as const,
  recentSearches: (limit: number) =>
    [...qk.all, "recent-searches", limit] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Multimodal search / index ---

export function useIndexStatus() {
  return useQuery<IndexStatus, ApiError>({
    queryKey: qk.indexStatus(),
    queryFn: getIndexStatus,
  });
}

export function useCorpus() {
  return useQuery<CorpusItem[], ApiError>({
    queryKey: qk.corpus(),
    queryFn: getCorpus,
  });
}

export function useRecentSearches(limit = 20) {
  return useQuery<RecentSearch[], ApiError>({
    queryKey: qk.recentSearches(limit),
    queryFn: () => getRecentSearches(limit),
  });
}

// Build / refresh the index. On success, invalidate corpus + index status so
// the Library status badges and dashboard metrics reflect the new vectors.
export function useBuildIndex() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => buildIndex(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.corpus() });
      qc.invalidateQueries({ queryKey: qk.indexStatus() });
    },
  });
}

// Text search — exposed as a mutation since it's user-triggered and writes a
// query-log entry server-side (not a cacheable idempotent read).
export function useTextSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) =>
      searchText(query, topK),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.recentSearches(20) });
    },
  });
}

// Image search — same rationale as text search.
export function useImageSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => searchImage(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.recentSearches(20) });
    },
  });
}
