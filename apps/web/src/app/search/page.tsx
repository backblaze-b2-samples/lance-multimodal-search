import { SearchPanel } from "@/components/search/search-panel";

export default function SearchPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Search</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Semantic, multimodal search over your corpus — query by text or by
          example image. Results are nearest neighbors from the B2-resident
          Lance index, returned as presigned previews.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <SearchPanel />
      </div>
    </div>
  );
}
