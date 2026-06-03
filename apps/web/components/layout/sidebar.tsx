"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  Search,
  BookOpen,
  GitBranch,
  LayoutDashboard,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/projects", label: "Projects", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/search", label: "Search", icon: Search },
  { href: "/memory", label: "Memory", icon: BookOpen },
  { href: "/repositories", label: "Repos", icon: GitBranch },
  { href: "/agents", label: "Agents", icon: Bot },
];

export function Sidebar({ orgSlug }: { orgSlug?: string }) {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 flex-col border-r bg-muted/30">
      <div className="flex h-16 items-center border-b px-4">
        <Link
          href="/projects"
          className="text-lg font-bold tracking-tight"
        >
          ContextClaw
        </Link>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={orgSlug ? `/orgs/${orgSlug}${item.href}` : item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-3">
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent"
        >
          <span className="text-xs">Settings</span>
        </Link>
      </div>
    </aside>
  );
}
