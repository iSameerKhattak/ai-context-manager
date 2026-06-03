"use client";

import { UserButton, useUser } from "@clerk/nextjs";

export default function SettingsPage() {
  const { user } = useUser();

  return (
    <div className="container max-w-2xl px-6 py-8">
      <h1 className="mb-8 text-3xl font-bold tracking-tight">Settings</h1>

      <div className="space-y-8">
        <section className="rounded-lg border p-6">
          <h2 className="mb-4 text-lg font-semibold">Profile</h2>
          <div className="flex items-center gap-4">
            <UserButton afterSignOutUrl="/sign-in" />
            <div>
              <p className="font-medium">{user?.fullName ?? user?.emailAddresses?.[0]?.emailAddress}</p>
              <p className="text-sm text-muted-foreground">
                {user?.emailAddresses?.[0]?.emailAddress}
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-lg border p-6">
          <h2 className="mb-4 text-lg font-semibold">Integrations</h2>
          <p className="text-sm text-muted-foreground">
            Manage GitHub App installations and other integrations.
          </p>
          <div className="mt-4">
            <a
              href="/repositories"
              className="text-sm font-medium text-primary hover:underline"
            >
              Manage Repositories →
            </a>
          </div>
        </section>

        <section className="rounded-lg border p-6">
          <h2 className="mb-4 text-lg font-semibold">Organization</h2>
          <p className="text-sm text-muted-foreground">
            Manage your organization settings, members, and billing.
          </p>
        </section>
      </div>
    </div>
  );
}
