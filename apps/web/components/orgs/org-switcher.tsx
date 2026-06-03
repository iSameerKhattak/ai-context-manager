"use client";

import { useMyOrgs, useCreateOrg } from "@/hooks/use-api";
import { useState } from "react";
import { ChevronsUpDown, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function OrgSwitcher({
  selectedOrgId,
  onOrgChange,
}: {
  selectedOrgId?: string;
  onOrgChange?: (orgId: string) => void;
}) {
  const { data, isLoading } = useMyOrgs();
  const createOrg = useCreateOrg();
  const orgs = data?.organizations ?? [];
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");

  const handleCreateOrg = async () => {
    if (!newName || !newSlug) return;
    await createOrg.mutateAsync({ name: newName, slug: newSlug });
    setOpen(false);
    setNewName("");
    setNewSlug("");
  };

  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        <select
          value={selectedOrgId}
          onChange={(e) => onOrgChange?.(e.target.value)}
          className="flex h-8 items-center gap-2 rounded-md border border-transparent bg-transparent px-2 text-sm font-medium hover:border-input appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="" disabled>
            {isLoading ? "Loading..." : "Select org"}
          </option>
          {orgs.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
        <ChevronsUpDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent"
          >
            <Plus className="h-4 w-4" />
          </button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Organization</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Name</label>
              <Input
                placeholder="My Company"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Slug</label>
              <Input
                placeholder="my-company"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button onClick={handleCreateOrg} disabled={!newName || !newSlug}>
              Create
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
