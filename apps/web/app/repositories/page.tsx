"use client";

import { useState } from "react";
import { useMyOrgs } from "@/hooks/use-api";
import { RepoPicker } from "@/components/integrations/repo-picker";
import { GitBranch, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function RepositoriesPage() {
  const { data: orgsData } = useMyOrgs();
  const firstOrg = orgsData?.organizations?.[0];
  const [showPicker, setShowPicker] = useState(false);

  return (
    <div className="container px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Repositories</h1>
          <p className="text-muted-foreground">
            Connect GitHub repositories to index your project knowledge
          </p>
        </div>
        {firstOrg && (
          <Button onClick={() => setShowPicker(!showPicker)}>
            <GitBranch className="mr-2 h-4 w-4" />
            {showPicker ? "Hide Picker" : "Connect Repos"}
          </Button>
        )}
      </div>

      {showPicker && firstOrg && (
        <div className="mb-8">
          <RepoPicker
            orgId={firstOrg.id}
            orgSlug={firstOrg.slug}
            onReposSelected={(repos) => {
              console.log("Selected repos:", repos);
              setShowPicker(false);
            }}
          />
        </div>
      )}

      <div className="rounded-lg border border-dashed p-12 text-center">
        <Globe className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
        <h3 className="mb-2 text-lg font-semibold">
          {showPicker ? "Select repositories above" : "No repositories connected"}
        </h3>
        <p className="mb-4 text-sm text-muted-foreground">
          Connect a GitHub repository to start indexing. ContextClaw will analyze
          your code, docs, and pull requests.
        </p>
        <Link href="/projects">
          <Button variant="outline">Back to Projects</Button>
        </Link>
      </div>
    </div>
  );
}
