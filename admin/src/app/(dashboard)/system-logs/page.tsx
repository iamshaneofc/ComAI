"use client";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAppStore } from "@/stores/app-store";

export default function SystemLogsPage() {
  const { systemLogs, clearSystemLogs } = useAppStore();

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Card
        title="System & API log"
        description="Populated from this tab’s fetch wrapper (status codes, errors, rate limits). Use alongside browser Network for full detail."
      >
        <Button variant="secondary" className="mb-4" onClick={() => clearSystemLogs()}>
          Clear log
        </Button>
        <div className="space-y-2">
          {systemLogs.length === 0 ? (
            <p className="text-sm text-ink-muted">No entries yet — run any API action from this console.</p>
          ) : (
            systemLogs.map((e) => (
              <div
                key={e.id}
                className="rounded-lg border border-slate-100 bg-white px-3 py-2 text-sm shadow-sm dark:border-slate-800 dark:bg-slate-900"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={
                      e.kind === "error"
                        ? "rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-bold uppercase text-red-700 dark:bg-red-950/50 dark:text-red-300"
                        : "rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-ink-muted dark:bg-slate-800"
                    }
                  >
                    {e.kind}
                  </span>
                  <span className="font-medium text-ink dark:text-slate-100">{e.title}</span>
                  <time className="ml-auto font-mono text-[11px] text-ink-muted">{e.at}</time>
                </div>
                {e.detail && <p className="mt-1 font-mono text-xs text-ink-muted">{e.detail}</p>}
                {e.meta != null && (
                  <pre className="mt-2 max-h-40 overflow-auto rounded bg-slate-950 p-2 text-[11px] text-slate-100">
                    {JSON.stringify(e.meta, null, 2)}
                  </pre>
                )}
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
