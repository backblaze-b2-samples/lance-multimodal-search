"use client";

import { Boxes, Cpu, Database, ImageIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useIndexStatus } from "@/lib/queries";

export function StatsCards() {
  const { data: status, isLoading, error, refetch } = useIndexStatus();

  // Surface fetch failures inline rather than rendering zeros — that would lie
  // about the index state when really the API is just unreachable.
  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    {
      title: "Corpus Assets",
      value: status?.corpus_total ?? 0,
      sub: status ? `${status.corpus_pending} pending` : "",
      icon: ImageIcon,
    },
    {
      title: "Vectors Indexed",
      value: status?.total_vectors ?? 0,
      sub: "images + PDF pages",
      icon: Boxes,
    },
    {
      title: "Vector Store on B2",
      value: status?.vector_store_size_human ?? "0 B",
      sub: "lancedb/ prefix",
      icon: Database,
    },
    {
      title: "Embedding Model",
      value: status?.embedding_model ?? "—",
      sub: status ? `${status.embedding_dim}-dim · CPU · $0` : "",
      icon: Cpu,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 px-4 pb-2 pt-4">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-5">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="stat-value truncate" title={String(card.value)}>
                  {card.value}
                </div>
                {card.sub && (
                  <div className="mt-0.5 text-[11px] text-muted-foreground">
                    {card.sub}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
