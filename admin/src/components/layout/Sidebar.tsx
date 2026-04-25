"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const NAV = [
  { href: "/store-setup", label: "Store Setup" },
  { href: "/platform-stores", label: "All stores (platform)" },
  { href: "/products", label: "Products" },
  { href: "/chat", label: "Chat Testing" },
  { href: "/agents", label: "Agents" },
  { href: "/ai-config", label: "AI Config" },
  { href: "/automation-logs", label: "Automation Logs" },
  { href: "/webhooks", label: "Webhooks" },
  { href: "/system-logs", label: "System Logs" },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200/80 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="border-b border-slate-200/80 px-5 py-4 dark:border-slate-800">
        <div className="text-xs font-semibold uppercase tracking-wide text-ink-muted">ComAI</div>
        <div className="text-lg font-semibold text-ink dark:text-slate-100">Dev Console</div>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        <p className="px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
          Modules
        </p>
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-blue-50 text-accent dark:bg-blue-950/50 dark:text-blue-300"
                  : "text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800/80"
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-slate-200/80 p-4 text-xs text-ink-muted dark:border-slate-800">
        Internal testing UI — not for store customers.
      </div>
    </aside>
  );
}
