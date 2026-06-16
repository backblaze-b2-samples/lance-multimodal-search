"use client";

import Image from "next/image";
import { FileText, ImageOff, SearchX } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import type { SearchHit } from "@lance-multimodal-search/shared";

function scoreTone(score: number) {
  if (score >= 0.85) return "bg-[var(--success)]/15 text-[var(--success)]";
  if (score >= 0.7) return "bg-primary/10 text-primary";
  return "bg-muted text-muted-foreground";
}

function ResultCard({ hit }: { hit: SearchHit }) {
  const label =
    hit.kind === "pdf_page"
      ? `${hit.source_filename} · p.${hit.page_number}`
      : hit.source_filename;

  return (
    <Card className="group overflow-hidden p-0">
      <div className="relative aspect-square w-full bg-muted">
        {hit.preview_url ? (
          <Image
            src={hit.preview_url}
            alt={label}
            fill
            sizes="(max-width: 768px) 50vw, 25vw"
            className="object-cover"
            unoptimized
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <ImageOff className="h-6 w-6" />
          </div>
        )}
        <span
          className={`absolute right-2 top-2 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums ${scoreTone(
            hit.score,
          )}`}
        >
          {(hit.score * 100).toFixed(0)}%
        </span>
      </div>
      <div className="space-y-1 p-3">
        <div className="flex items-center gap-1.5">
          {hit.kind === "pdf_page" && (
            <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate text-xs font-medium" title={label}>
            {label}
          </span>
        </div>
        {hit.kind === "pdf_page" && hit.text_snippet ? (
          <p className="line-clamp-2 text-[11px] leading-snug text-muted-foreground">
            {hit.text_snippet}
          </p>
        ) : (
          <Badge variant="secondary" className="text-[10px]">
            {hit.kind === "pdf_page" ? "PDF page" : "Image"}
          </Badge>
        )}
      </div>
    </Card>
  );
}

export function ResultGallery({
  hits,
  hasSearched,
}: {
  hits: SearchHit[];
  hasSearched: boolean;
}) {
  if (!hasSearched) {
    return (
      <EmptyState
        icon={SearchX}
        title="No search yet"
        description="Search by text or drop in an image to find visually similar assets."
      />
    );
  }
  if (hits.length === 0) {
    return (
      <EmptyState
        icon={SearchX}
        title="No matches"
        description="Nothing in the index matched. Try a different query, or build the index from the Library."
      />
    );
  }
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {hits.map((hit) => (
        <ResultCard key={hit.asset_id} hit={hit} />
      ))}
    </div>
  );
}
