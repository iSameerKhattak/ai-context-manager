"use client";

import { useState } from "react";
import { Plus, FolderKanban, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useMyOrgs, useProjects, useCreateProject } from "@/hooks/use-api";
import Link from "next/link";

export default function ProjectsPage() {
  const { data: orgsData } = useMyOrgs();
  const firstOrg = orgsData?.organizations?.[0];
  const orgId = firstOrg?.id;

  const { data: projectsData, isLoading } = useProjects(orgId ?? null);
  const createProject = useCreateProject(orgId ?? "");
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");

  const projects = projectsData?.projects ?? [];

  const handleCreate = async () => {
    if (!newName || !newSlug) return;
    await createProject.mutateAsync({
      name: newName,
      slug: newSlug,
    });
    setOpen(false);
    setNewName("");
    setNewSlug("");
  };

  return (
    <div className="container px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">
            Manage your projects and connected repositories
          </p>
        </div>
        {firstOrg && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                New Project
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Project</DialogTitle>
                <DialogDescription>
                  Create a new project inside {firstOrg.name}.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Name</label>
                  <Input
                    placeholder="My Project"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Slug</label>
                  <Input
                    placeholder="my-project"
                    value={newSlug}
                    onChange={(e) => setNewSlug(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={handleCreate}
                  disabled={!newName || !newSlug}
                >
                  Create
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {!firstOrg ? (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <h3 className="mb-2 text-lg font-semibold">No organization yet</h3>
          <p className="mb-4 text-sm text-muted-foreground">
            Create an organization to get started.
          </p>
          <Button>Create Organization</Button>
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : projects.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <FolderKanban className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
          <h3 className="mb-2 text-lg font-semibold">No projects yet</h3>
          <p className="mb-4 text-sm text-muted-foreground">
            Create your first project and connect a GitHub repository to start
            indexing your knowledge.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="group rounded-lg border p-4 transition-colors hover:border-primary hover:shadow-sm"
            >
              <h3 className="font-semibold group-hover:text-primary">
                {project.name}
              </h3>
              {project.description && (
                <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                  {project.description}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
