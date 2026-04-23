"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/stores/app-store";

export default function AutomationLogsPage() {
  const { automationLogs, pushAutomation, clearAutomationLogs } = useAppStore();

  const testEvent = useMutation({
    mutationFn: async () => {
      const r = await apiFetch({ path: "/events", method: "POST", body: { source: "admin", type: "ping" } });
      return r;
    },
    onSuccess: (r) => {
      pushAutomation("POST /events response", undefined, r.data);
      toast.message(r.ok ? "Event accepted (stub)" : "Event call failed");
    },
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Card
        title="Automation trail"
        description="Client-side log of automation-related responses. Backend automation is mostly async (Celery)."
      >
        <div className="mb-4 flex gap-2">
          <Button variant="secondary" onClick={() => testEvent.mutate()} disabled={testEvent.isPending}>
            POST test event (/events stub)
          </Button>
          <Button variant="ghost" onClick={() => clearAutomationLogs()}>
            Clear list
          </Button>
        </div>
        <div className="space-y-2">
          {automationLogs.length === 0 ? (
            <p className="text-sm text-ink-muted">No entries yet — create a store, connect Shopify, or send a test event.</p>
          ) : (
            automationLogs.map((e) => (
              <div
                key={e.id}
                className="rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-900/40"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-medium text-ink dark:text-slate-100">{e.title}</span>
                  <time className="font-mono text-[11px] text-ink-muted">{e.at}</time>
                </div>
                {e.detail && <p className="mt-1 text-xs text-ink-muted">{e.detail}</p>}
                {e.meta != null && (
                  <pre className="mt-2 max-h-32 overflow-auto rounded bg-slate-950 p-2 text-[11px] text-slate-100">
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
