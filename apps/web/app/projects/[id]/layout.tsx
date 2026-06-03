"use client";

import { AppLayout } from "@/components/layout/app-layout";

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppLayout>{children}</AppLayout>;
}
