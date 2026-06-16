"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useIndexStatus } from "@/lib/queries";

const chartConfig = {
  count: { label: "Assets", color: "var(--chart-1)" },
} satisfies ChartConfig;

// Index coverage: how many corpus assets are indexed vs. still pending.
export function IndexCoverageChart() {
  const { data: status, error, refetch } = useIndexStatus();

  const data = useMemo(
    () =>
      status
        ? [
            { label: "Indexed", count: status.corpus_indexed },
            { label: "Pending", count: status.corpus_pending },
          ]
        : [],
    [status],
  );

  const hasData = (status?.corpus_total ?? 0) > 0;

  return (
    <Card>
      <CardHeader className="border-b border-border px-5 py-4">
        <CardTitle className="card-title">Index Coverage</CardTitle>
        <CardDescription className="text-xs">
          Corpus assets indexed vs. pending
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : !hasData ? (
          <EmptyState
            icon={BarChart3}
            title="Nothing indexed yet"
            description="Upload images or PDFs and build the index to see coverage."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="coverage-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-count)" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="var(--color-count)" stopOpacity={0.55} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={10} fontSize={11} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} tickMargin={6} fontSize={11} width={28} />
              <ChartTooltip cursor={{ fill: "var(--accent-subtle)" }} content={<ChartTooltipContent />} />
              <Bar
                dataKey="count"
                fill="url(#coverage-fill)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
