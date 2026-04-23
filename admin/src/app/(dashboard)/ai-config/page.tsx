"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";

type ConfigRes = {
  id: string | null;
  store_id: string;
  provider: string;
  default_model: string;
  has_tenant_api_key: boolean;
};

export default function AiConfigPage() {
  const qc = useQueryClient();
  const [provider, setProvider] = useState<"openai" | "gemini">("openai");
  const [defaultModel, setDefaultModel] = useState("gpt-4o");
  const [apiKeyField, setApiKeyField] = useState("");

  const q = useQuery({
    queryKey: ["ai-config"],
    queryFn: async () => {
      const r = await apiFetch<ConfigRes>({ path: "/ai-config" });
      if (!r.ok) throw new Error("bad");
      return r.data;
    },
  });

  useEffect(() => {
    if (q.data) {
      setProvider(q.data.provider as "openai" | "gemini");
      setDefaultModel(q.data.default_model);
    }
  }, [q.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = { provider, default_model: defaultModel };
      if (apiKeyField.trim()) body.api_key = apiKeyField.trim();
      const r = await apiFetch<ConfigRes>({ path: "/ai-config", method: "PATCH", body });
      return r;
    },
    onSuccess: (r) => {
      if (!r.ok) {
        toast.error("Save failed");
        return;
      }
      toast.success("AI config saved");
      setApiKeyField("");
      void qc.invalidateQueries({ queryKey: ["ai-config"] });
    },
  });

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <Card title="Store AI config" description="GET/PATCH /ai-config — API key is write-only and never returned.">
        {q.isLoading && <p className="text-sm text-ink-muted">Loading…</p>}
        {q.error && <p className="text-sm text-coral">Failed to load (tenant key required).</p>}
        {q.data && (
          <p className="text-xs text-ink-muted">
            Store <span className="font-mono">{q.data.store_id}</span> · tenant key stored:{" "}
            <strong>{q.data.has_tenant_api_key ? "yes" : "no"}</strong>
          </p>
        )}
        <div className="mt-4 space-y-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Provider</span>
            <select
              className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
              value={provider}
              onChange={(e) => setProvider(e.target.value as typeof provider)}
            >
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Default model</span>
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Provider API key (optional update)</span>
            <input
              type="password"
              className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              value={apiKeyField}
              onChange={(e) => setApiKeyField(e.target.value)}
              placeholder="Leave blank to keep existing"
              autoComplete="off"
            />
          </label>
        </div>
        <Button className="mt-4" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          Save
        </Button>
      </Card>
    </div>
  );
}
