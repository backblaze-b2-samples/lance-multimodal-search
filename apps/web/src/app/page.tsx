import Link from "next/link";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentSearchesTable } from "@/components/dashboard/recent-uploads-table";
import { IndexCoverageChart } from "@/components/dashboard/upload-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Your corpus and its B2-resident vector index at a glance.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/search">
            <Search className="h-3.5 w-3.5" />
            Search corpus
          </Link>
        </Button>
      </div>
      <StatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <IndexCoverageChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentSearchesTable />
        </div>
      </div>
    </div>
  );
}
