"use client";

import { useEffect } from "react";
import { Moon, Sun } from "lucide-react";
import { useAppStore } from "@/stores/app-store";

export function TopBar({ title }: { title: string }) {
  const { apiBaseUrl, apiKey, storeId, setApiBaseUrl, setApiKey, setStoreId, connectionStatus, setConnectionStatus } =
    useAppStore();

  useEffect(() => {
    let cancelled = false;
    async function ping() {
      if (!apiKey) {
        setConnectionStatus("idle");
        return;
      }
      const base = apiBaseUrl.replace(/\/+$/, "");
      try {
        const res = await fetch(`${base}/api/v1/stores/me`, {
          headers: { Accept: "application/json", "X-API-KEY": apiKey },
        });
        if (res.ok) {
          try {
            const data = (await res.json()) as { id?: string };
            if (data?.id && !useAppStore.getState().storeId) setStoreId(data.id);
          } catch {
            /* ignore */
          }
        }
        if (!cancelled) setConnectionStatus(res.ok ? "ok" : "error");
      } catch {
        if (!cancelled) setConnectionStatus("error");
      }
    }
    const t = setTimeout(ping, 400);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [apiKey, apiBaseUrl, setConnectionStatus, setStoreId]);

  const toggleTheme = () => {
    document.documentElement.classList.toggle("dark");
  };

  const statusDot =
    connectionStatus === "ok"
      ? "bg-emerald-500"
      : connectionStatus === "error"
        ? "bg-coral"
        : "bg-slate-300 dark:bg-slate-600";

  const statusLabel =
    connectionStatus === "ok"
      ? "Connected"
      : connectionStatus === "error"
        ? "Error"
        : apiKey
          ? "Checking…"
          : "No API key";

  return (
    <header className="flex min-h-14 shrink-0 flex-wrap items-center gap-4 border-b border-slate-200/80 bg-white/90 px-6 py-2 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
      <h1 className="text-lg font-semibold text-ink dark:text-slate-100">{title}</h1>
      <div className="ml-auto flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-ink-muted">
          <span className="hidden sm:inline">API base</span>
          <input
            className="h-8 w-40 rounded-lg border border-slate-200 bg-white px-2 text-ink shadow-sm dark:border-slate-700 dark:bg-slate-950 sm:w-52"
            value={apiBaseUrl}
            onChange={(e) => setApiBaseUrl(e.target.value)}
            placeholder="http://127.0.0.1:8000"
          />
        </label>
        <label className="flex items-center gap-2 text-xs text-ink-muted">
          <span>X-API-KEY</span>
          <input
            className="h-8 w-44 rounded-lg border border-slate-200 bg-white px-2 font-mono text-[11px] text-ink shadow-sm dark:border-slate-700 dark:bg-slate-950 sm:w-56"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Tenant API key"
            type="password"
            autoComplete="off"
          />
        </label>
        <label className="flex items-center gap-2 text-xs text-ink-muted">
          <span>Store ID</span>
          <input
            className="h-8 w-36 rounded-lg border border-slate-200 bg-slate-50 px-2 font-mono text-[11px] text-ink shadow-sm dark:border-slate-700 dark:bg-slate-950 sm:w-44"
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
            placeholder="from create store"
          />
        </label>
        <div
          className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium dark:border-slate-700 dark:bg-slate-950"
          title="Uses GET /stores/me when API key is set"
        >
          <span className={`h-2 w-2 rounded-full ${statusDot}`} />
          <span className="text-ink-muted">{statusLabel}</span>
        </div>
        <button
          type="button"
          onClick={toggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          aria-label="Toggle dark mode"
        >
          <span className="dark:hidden">
            <Moon className="h-4 w-4" />
          </span>
          <span className="hidden dark:inline">
            <Sun className="h-4 w-4" />
          </span>
        </button>
      </div>
    </header>
  );
}
