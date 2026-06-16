"use client";

import Image from "next/image";
import { toast } from "sonner";
import { CheckCircle2, Clock, FileText, ImageIcon, Loader2, RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useBuildIndex, useCorpus, usePreviewUrl } from "@/lib/queries";
import type { CorpusItem } from "@lance-multimodal-search/shared";

function CorpusThumb({ item }: { item: CorpusItem }) {
  // Only images get a B2 preview thumbnail; PDFs show a document glyph
  // (their page renders are searchable but live under derived/).
  const isImage = item.kind === "image";
  const { data } = usePreviewUrl(isImage ? item.key : undefined, isImage);

  return (
    <Card className="overflow-hidden p-0">
      <div className="relative aspect-square w-full bg-muted">
        {isImage && data?.url ? (
          <Image
            src={data.url}
            alt={item.filename}
            fill
            sizes="(max-width: 768px) 50vw, 25vw"
            className="object-cover"
            unoptimized
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
            {isImage ? (
              <ImageIcon className="h-6 w-6" />
            ) : (
              <FileText className="h-6 w-6" />
            )}
          </div>
        )}
        <span className="absolute right-2 top-2">
          {item.indexed ? (
            <Badge className="gap-1 bg-[var(--success)]/15 text-[var(--success)] hover:bg-[var(--success)]/15">
              <CheckCircle2 className="h-3 w-3" />
              Indexed
            </Badge>
          ) : (
            <Badge variant="secondary" className="gap-1">
              <Clock className="h-3 w-3" />
              Pending
            </Badge>
          )}
        </span>
      </div>
      <div className="space-y-1 p-3">
        <span className="block truncate text-xs font-medium" title={item.filename}>
          {item.filename}
        </span>
        <span className="text-[11px] text-muted-foreground">
          {item.kind === "pdf" ? "PDF" : "Image"} · {item.size_human}
        </span>
      </div>
    </Card>
  );
}

export function CorpusGrid() {
  const { data: corpus = [], isLoading, error, refetch } = useCorpus();
  const buildIndex = useBuildIndex();

  const pending = corpus.filter((c) => !c.indexed).length;

  const handleBuild = () => {
    buildIndex.mutate(undefined, {
      onSuccess: (res) => {
        toast.success(
          `Indexed ${res.indexed_assets} asset(s) → ${res.new_vectors} vector(s)` +
            (res.errors.length ? ` (${res.errors.length} error(s))` : ""),
        );
        if (res.errors.length) {
          for (const e of res.errors.slice(0, 3)) toast.error(e);
        }
      },
      onError: (err) => toast.error(err.message),
    });
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {corpus.length} asset(s) in the corpus
          {pending > 0 ? ` · ${pending} pending` : " · all indexed"}
        </p>
        <Button size="sm" onClick={handleBuild} disabled={buildIndex.isPending}>
          {buildIndex.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          Build / refresh index
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-square w-full rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : corpus.length === 0 ? (
        <EmptyState
          icon={ImageIcon}
          title="Corpus is empty"
          description="Upload images or PDFs to populate the corpus, then build the index."
        />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {corpus.map((item) => (
            <CorpusThumb key={item.key} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
