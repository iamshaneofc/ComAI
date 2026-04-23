"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/stores/app-store";

type AgentRow = {
  id: string;
  name: string;
  type: string;
  model: string;
  temperature: number;
  system_prompt: string;
  is_active: boolean;
};

export default function AgentsPage() {
  const qc = useQueryClient();
  const setTestAgentLabel = useAppStore((s) => s.setTestAgentLabel);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [type, setType] = useState<"chat" | "whatsapp" | "call">("chat");
  const [model, setModel] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [systemPrompt, setSystemPrompt] = useState("You are a helpful shopping assistant.");

  const listQuery = useQuery({
    queryKey: ["agents"],
    queryFn: async () => {
      const r = await apiFetch<AgentRow[]>({ path: "/agents" });
      if (!r.ok) throw new Error("list failed");
      return r.data;
    },
  });

  const selected = listQuery.data?.find((a) => a.id === selectedId);

  useEffect(() => {
    if (selected) {
      setName(selected.name);
      setType(selected.type as "chat" | "whatsapp" | "call");
      setModel(selected.model || "");
      setTemperature(selected.temperature);
      setSystemPrompt(selected.system_prompt);
    }
  }, [selected]);

  const createMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        name,
        type,
        temperature,
        system_prompt: systemPrompt,
      };
      if (model.trim()) body.model = model.trim();
      const r = await apiFetch<AgentRow>({ path: "/agents", method: "POST", body });
      return r;
    },
    onSuccess: (r) => {
      if (!r.ok) {
        toast.error("Create agent failed");
        return;
      }
      toast.success("Agent created");
      void qc.invalidateQueries({ queryKey: ["agents"] });
      setSelectedId(r.data.id);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedId) throw new Error("no id");
      const body: Record<string, unknown> = {
        name,
        type,
        temperature,
        system_prompt: systemPrompt,
      };
      if (model.trim()) body.model = model.trim();
      const r = await apiFetch<AgentRow>({ path: `/agents/${selectedId}`, method: "PATCH", body });
      return r;
    },
    onSuccess: (r) => {
      if (!r.ok) {
        toast.error("Update failed");
        return;
      }
      toast.success("Agent updated");
      void qc.invalidateQueries({ queryKey: ["agents"] });
    },
  });

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <Card title="Agents" description="GET/POST/PATCH /agents — tenant scoped.">
        {listQuery.isLoading && <p className="text-sm text-ink-muted">Loading…</p>}
        {listQuery.error && <p className="text-sm text-coral">Could not list agents (check API key).</p>}
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50/80 text-xs uppercase text-ink-muted dark:border-slate-800 dark:bg-slate-900/50">
              <tr>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Model</th>
                <th className="px-3 py-2">Temp</th>
                <th className="px-3 py-2">Active</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {(listQuery.data ?? []).map((a) => (
                <tr
                  key={a.id}
                  className={selectedId === a.id ? "bg-blue-50/50 dark:bg-blue-950/20" : ""}
                  onClick={() => setSelectedId(a.id)}
                >
                  <td className="cursor-pointer px-3 py-2 font-medium">{a.name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{a.type}</td>
                  <td className="max-w-[140px] truncate px-3 py-2 font-mono text-xs">{a.model || "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{a.temperature}</td>
                  <td className="px-3 py-2">{a.is_active ? "yes" : "no"}</td>
                  <td className="px-3 py-2">
                    <Link
                      href="/chat"
                      className="text-sm font-medium text-accent hover:underline"
                      onClick={(e) => {
                        e.stopPropagation();
                        setTestAgentLabel(`${a.name} (${a.type})`);
                      }}
                    >
                      Test in chat
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title={selectedId ? "Edit agent" : "Create agent"} description="Voice channel maps to type call in the API.">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Name</span>
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Type</span>
            <select
              className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
              value={type}
              onChange={(e) => setType(e.target.value as typeof type)}
            >
              <option value="chat">chat</option>
              <option value="whatsapp">whatsapp</option>
              <option value="call">call (voice)</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Model (optional)</span>
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Store default if empty"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Temperature</span>
            <input
              type="number"
              step="0.1"
              min={0}
              max={2}
              className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm sm:col-span-2">
            <span className="text-ink-muted">System prompt</span>
            <textarea
              className="min-h-[140px] rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            Create agent
          </Button>
          <Button
            variant="secondary"
            onClick={() => updateMutation.mutate()}
            disabled={!selectedId || updateMutation.isPending}
          >
            Save changes
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setSelectedId(null);
              setName("New agent");
              setType("chat");
              setModel("");
              setTemperature(0.7);
              setSystemPrompt("You are a helpful shopping assistant.");
            }}
          >
            New form
          </Button>
        </div>
      </Card>
    </div>
  );
}
