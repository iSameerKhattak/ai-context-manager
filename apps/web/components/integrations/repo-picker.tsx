"use client";

import { useState } from "react";
import { useInstallations, useGitHubInstallUrl } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Loader2, ExternalLink, GitBranch } from "lucide-react";

interface RepoPickerProps {
  orgId: string;
  orgSlug?: string;
  onReposSelected?: (repos: Array<{ id: number; full_name: string }>) => void;
  connectedRepos?: Set<string>;
}

export function RepoPicker({
  orgId,
  orgSlug,
  onReposSelected,
  connectedRepos = new Set(),
}: RepoPickerProps) {
  const { data: installData, isLoading: installsLoading } =
    useInstallations(orgId);
  const { data: urlData } = useGitHubInstallUrl(orgSlug);

  const installations = installData ?? [];
  const [expanded, setExpanded] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const toggleRepo = (repoId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(repoId)) next.delete(repoId);
      else next.add(repoId);
      return next;
    });
  };

  const handleConnect = () => {
    if (!onReposSelected) return;
    const repos: Array<{ id: number; full_name: string }> = [];
    for (const inst of installations) {
      for (const repo of inst.repos) {
        if (selected.has(repo.id)) {
          repos.push({ id: repo.id, full_name: repo.full_name });
        }
      }
    }
    onReposSelected(repos);
    setSelected(new Set());
  };

  if (installsLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (installations.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        <GitBranch className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
        <h3 className="mb-2 font-semibold">No GitHub installation found</h3>
        <p className="mb-4 text-sm text-muted-foreground">
          Install the ContextClaw GitHub App to connect repositories.
        </p>
        {urlData?.install_url && (
          <a href={urlData.install_url} target="_blank" rel="noopener noreferrer">
            <Button>
              <ExternalLink className="mr-2 h-4 w-4" />
              Install GitHub App
            </Button>
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {installations.map((inst) => (
        <div key={inst.id} className="rounded-lg border">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-left font-medium"
            onClick={() => setExpanded(expanded === inst.id ? null : inst.id)}
          >
            <span>{inst.account_login}</span>
            <span className="text-sm text-muted-foreground">
              {inst.repos.length} repos
            </span>
          </button>

          {expanded === inst.id && (
            <div className="border-t px-4 py-2">
              {inst.repos.length === 0 ? (
                <p className="py-4 text-sm text-muted-foreground">
                  No repositories available.
                </p>
              ) : (
                <div className="max-h-64 space-y-1 overflow-y-auto py-2">
                  {inst.repos.map((repo) => {
                    const alreadyConnected = connectedRepos.has(repo.full_name);
                    return (
                      <label
                        key={repo.id}
                        className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 hover:bg-accent"
                      >
                        <Checkbox
                          checked={selected.has(repo.id)}
                          onCheckedChange={() => toggleRepo(repo.id)}
                          disabled={alreadyConnected}
                        />
                        <div className="flex-1">
                          <span className="text-sm font-medium">
                            {repo.full_name}
                          </span>
                          {alreadyConnected && (
                            <span className="ml-2 text-xs text-muted-foreground">
                              (connected)
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {repo.language ?? ""}
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {onReposSelected && selected.size > 0 && (
        <Button onClick={handleConnect} className="w-full">
          Connect {selected.size} selected repo{selected.size !== 1 ? "s" : ""}
        </Button>
      )}
    </div>
  );
}
