"use client";

import { useParams } from "next/navigation";
import { useProjects } from "@/hooks/use-api";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: projectsData } = useProjects(params?.id ?? null);
  const project = projectsData?.projects?.find(
    (p) => p.id === params?.id,
  );

  return (
    <div className="container px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">
          {project?.name ?? "Project"}
        </h1>
        <p className="text-muted-foreground">{project?.description}</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="rounded-lg border p-4">
          <h3 className="mb-1 text-sm font-medium text-muted-foreground">
            Repositories
          </h3>
          <p className="text-2xl font-bold">0</p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="mb-1 text-sm font-medium text-muted-foreground">
            Documents Indexed
          </h3>
          <p className="text-2xl font-bold">0</p>
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="mb-1 text-sm font-medium text-muted-foreground">
            Memory Facts
          </h3>
          <p className="text-2xl font-bold">0</p>
        </div>
      </div>
    </div>
  );
}
