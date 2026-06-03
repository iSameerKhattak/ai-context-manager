"use client";

import { useState } from "react";
import { UserButton } from "@clerk/nextjs";
import { Sidebar } from "@/components/layout/sidebar";
import { OrgSwitcher } from "@/components/orgs/org-switcher";
import { useMyOrgs } from "@/hooks/use-api";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const [selectedOrgId, setSelectedOrgId] = useState<string | undefined>();
  const selectedOrg = useMyOrgs().data?.organizations?.find(
    (o) => o.id === selectedOrgId,
  );

  return (
    <div className="flex h-screen">
      <Sidebar orgSlug={selectedOrg?.slug} />
      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b px-4">
          <OrgSwitcher
            selectedOrgId={selectedOrgId}
            onOrgChange={setSelectedOrgId}
          />
          <div className="flex items-center gap-3">
            <UserButton afterSignOutUrl="/sign-in" />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
