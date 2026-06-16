"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { ImageUp, Loader2, Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useImageSearch, useTextSearch } from "@/lib/queries";
import { ResultGallery } from "./result-gallery";
import type { SearchHit } from "@lance-multimodal-search/shared";

export function SearchPanel() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const textSearch = useTextSearch();
  const imageSearch = useImageSearch();
  const isSearching = textSearch.isPending || imageSearch.isPending;

  const runTextSearch = useCallback(() => {
    const q = query.trim();
    if (!q) return;
    textSearch.mutate(
      { query: q },
      {
        onSuccess: (res) => {
          setHits(res.hits);
          setHasSearched(true);
        },
        onError: (err) => toast.error(err.message),
      },
    );
  }, [query, textSearch]);

  const onDrop = useCallback(
    (files: File[]) => {
      const file = files[0];
      if (!file) return;
      imageSearch.mutate(file, {
        onSuccess: (res) => {
          setHits(res.hits);
          setHasSearched(true);
          toast.success(`Found ${res.count} similar assets`);
        },
        onError: (err) => toast.error(err.message),
      });
    },
    [imageSearch],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [] },
    maxFiles: 1,
    disabled: isSearching,
  });

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-5">
          <Tabs defaultValue="text">
            <TabsList>
              <TabsTrigger value="text">
                <Search className="mr-1.5 h-3.5 w-3.5" />
                Text query
              </TabsTrigger>
              <TabsTrigger value="image">
                <ImageUp className="mr-1.5 h-3.5 w-3.5" />
                Image query
              </TabsTrigger>
            </TabsList>

            <TabsContent value="text" className="mt-4">
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && runTextSearch()}
                  placeholder='e.g. "a red bicycle on a beach"'
                  disabled={isSearching}
                />
                <Button onClick={runTextSearch} disabled={isSearching || !query.trim()}>
                  {textSearch.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  Search
                </Button>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                CLIP embeds your text into the same space as the corpus images
                and PDF pages — no keywords or tags required.
              </p>
            </TabsContent>

            <TabsContent value="image" className="mt-4">
              <div
                {...getRootProps()}
                className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                  isDragActive
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <input {...getInputProps()} />
                {imageSearch.isPending ? (
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                ) : (
                  <ImageUp className="h-6 w-6 text-muted-foreground" />
                )}
                <p className="text-sm font-medium">
                  Drop an image, or click to choose
                </p>
                <p className="text-xs text-muted-foreground">
                  Finds visually similar images and document pages in the corpus.
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <ResultGallery hits={hits} hasSearched={hasSearched} />
    </div>
  );
}
