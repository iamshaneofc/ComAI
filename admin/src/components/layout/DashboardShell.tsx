"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

const TITLES: Record<string, string> = {
  "/store-setup": "Store Setup",
  "/platform-stores": "All stores (platform)",
  "/products": "Products",
  "/chat": "Chat Testing",
  "/agents": "Agents",
  "/ai-config": "AI Config",
  "/automation-logs": "Automation Logs",
  "/webhooks": "Webhooks",
  "/system-logs": "System Logs",
};

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const title = TITLES[pathname] || "Dashboard";

  return (
    <div className="flex min-h-screen bg-surface dark:bg-slate-950">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={title} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
