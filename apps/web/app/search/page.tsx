"use client";

import { useState } from "react";
import { useMyOrgs, useProjects, useSearchPreview } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Search as SearchIcon, FileCode, FileText } from "lucide-react";

export default function SearchPage() {
  const { data: orgsData } = useMyOrgs();
  const firstOrg = orgsData?.organizations?.[0];
  const { data: projectsData } = useProjects(firstOrg?.id ?? null);
  const firstProject = projectsData?.projects?.[0];

  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"hybrid" | "vector" | "fts">("hybrid");
  const searchPreview = useSearchPreview();

  const results = searchPreview.data?.items ?? [];
  const took = searchPreview.data?.took_ms;

  const handleSearch = () => {
    if (!query.trim() || !firstProject?.id) return;
    searchPreview.mutate({
      project_id: firstProject.id,
      query,
      max_chunks: 20,
      mode,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="container px-6 py-8">
      <div className="mb-8">
        <h1 className="mb-2 text-3xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground">
          Search indexed repositories for code, documentation, and more.
        </p>
      </div>

      {/* Search bar */}
      <div className="mb-6 flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search your codebase..."
          className="flex-1 text-lg"
        />
        <Button onClick={handleSearch} disabled={searchPreview.isPending || !query.trim()}>
          {searchPreview.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <SearchIcon className="mr-2 h-4 w-4" />
          )}
          Search
        </Button>
      </div>

      {/* Mode selector */}
      <div className="mb-6 flex gap-2">
        {(["hybrid", "vector", "fts"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`rounded-md px-3 py-1 text-xs font-medium ${
              mode === m
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-accent"
            }`}
          >
            {m === "hybrid" ? "Hybrid" : m === "vector" ? "Vector" : "Full-Text"}
          </button>
        ))}
      </div>

      {/* Results */}
      {searchPreview.isPending && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {!searchPreview.isPending && searchPreview.data && results.length === 0 && (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <SearchIcon className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
          <p className="text-muted-foreground">No results found.</p>
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="mb-4 text-sm text-muted-foreground">
            Found {results.length} results{took ? ` (${took}ms)` : ""}
          </div>

          <div className="space-y-3">
            {results.map((r, i) => (
              <div key={i} className="rounded-lg border p-4">
                <div className="mb-1 flex items-center gap-2">
                  {r.source.source_type === "code" ? (
                    <FileCode className="h-4 w-4 text-blue-500" />
                  ) : (
                    <FileText className="h-4 w-4 text-green-500" />
                  )}
                  <span className="text-sm font-medium">{r.source.path}</span>
                  {r.source.symbol && (
                    <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                      {r.source.symbol}
                    </span>
                  )}
                  <span className="ml-auto text-xs text-muted-foreground">
                    score: {r.score.toFixed(3)}
                  </span>
                </div>

                {r.source.language && (
                  <span className="mr-2 inline-block rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                    {r.source.language}
                  </span>
                )}

                <span
                  className={`inline-block rounded px-1.5 py-0.5 text-xs ${
                    r.relevance === "high"
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : r.relevance === "medium"
                        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                        : "bg-gray-100 text-gray-500 dark:bg-gray-800"
                  }`}
                >
                  {r.relevance}
                </span>

                <p className="mt-2 text-sm text-muted-foreground">
                  {r.snippet.slice(0, 300)}
                  {r.snippet.length > 300 ? "..." : ""}
                </p>
              </div>
            ))}
          </div>
        </>
      )}

      {!searchPreview.data && !searchPreview.isPending && (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <SearchIcon className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Enter a query to search your indexed codebase.
          </p>
        </div>
      )}
    </div>
  );
}
