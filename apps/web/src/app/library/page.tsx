import Link from "next/link";
import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CorpusGrid } from "@/components/library/corpus-grid";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="page-title">Library</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Your ingested images & PDFs (the <code>corpus/</code> prefix), each
            with its index status. Build the index to make new assets
            searchable.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/upload">
            <Upload className="h-3.5 w-3.5" />
            Add to corpus
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <CorpusGrid />
      </div>
    </div>
  );
}
