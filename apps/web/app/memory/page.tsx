"use client";

import { useState } from "react";
import { useMyOrgs, useProjects, useFacts, useAssertFact, useDeleteFact } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Loader2, Brain, Plus, Trash2, User, Bot } from "lucide-react";

export default function MemoryPage() {
  const { data: orgsData } = useMyOrgs();
  const firstOrg = orgsData?.organizations?.[0];
  const { data: projectsData } = useProjects(firstOrg?.id ?? null);
  const firstProject = projectsData?.projects?.[0];

  const [newStatement, setNewStatement] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: factsData, isLoading } = useFacts(firstProject?.id ?? null);
  const assertFact = useAssertFact();
  const deleteFact = useDeleteFact();

  const facts = factsData?.facts ?? [];

  const handleAdd = () => {
    if (!newStatement.trim() || !firstProject?.id) return;
    assertFact.mutate(
      { project_id: firstProject.id, statement: newStatement },
      { onSuccess: () => { setNewStatement(""); setDialogOpen(false); } },
    );
  };

  const handleDelete = (factId: string) => {
    deleteFact.mutate(factId);
  };

  return (
    <div className="container px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="mb-2 text-3xl font-bold tracking-tight">Memory</h1>
          <p className="text-muted-foreground">
            Project-level facts that ContextClaw remembers across sessions.
          </p>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button disabled={!firstProject}>
              <Plus className="mr-2 h-4 w-4" />
              Add Fact
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add a Memory Fact</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-2">
              <Input
                value={newStatement}
                onChange={(e) => setNewStatement(e.target.value)}
                placeholder='e.g. "The API uses Clerk for authentication"'
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
              <Button onClick={handleAdd} disabled={!newStatement.trim() || assertFact.isPending} className="w-full">
                {assertFact.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Save Fact
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {!isLoading && facts.length === 0 && (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <Brain className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
          <h3 className="mb-2 text-lg font-semibold">No memory facts yet</h3>
          <p className="mb-4 text-sm text-muted-foreground">
            Add facts about your project architecture, decisions, and conventions
            so ContextClaw remembers them.
          </p>
          <Button variant="outline" onClick={() => setDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Your First Fact
          </Button>
        </div>
      )}

      {facts.length > 0 && (
        <div className="space-y-3">
          {facts.map((fact) => (
            <div key={fact.id} className="flex items-start gap-3 rounded-lg border p-4">
              <div className="mt-0.5">
                {fact.source === "auto" ? (
                  <Bot className="h-4 w-4 text-blue-500" />
                ) : (
                  <User className="h-4 w-4 text-green-500" />
                )}
              </div>
              <div className="flex-1">
                <p>{fact.statement}</p>
                <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="rounded bg-muted px-1.5 py-0.5">
                    {fact.scope}
                  </span>
                  <span>confidence: {(fact.confidence * 100).toFixed(0)}%</span>
                  <span>source: {fact.source}</span>
                  <span>{new Date(fact.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleDelete(fact.id)}
                disabled={deleteFact.isPending}
              >
                <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
