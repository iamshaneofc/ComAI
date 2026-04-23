"use client";

import { useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Send, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";
import { useAppStore, type ChatMessage } from "@/stores/app-store";

type ChatResponse = {
  message: string;
  intent: string;
  products: Record<string, unknown>[];
};

type ChatAgentConfig = {
  id: string;
  name: string;
  model: string;
  temperature: number;
};

function productImage(p: Record<string, unknown>) {
  const images = p.images as { url?: string }[] | undefined;
  const url = images?.[0]?.url;
  return typeof url === "string" ? url : null;
}

export default function ChatTestingPage() {
  const {
    sessionId,
    setSessionId,
    memoryEnabled,
    setMemoryEnabled,
    chatMessages,
    setChatMessages,
    clearChat,
    lastChatDebug,
    setLastChatDebug,
    testAgentLabel,
    setTestAgentLabel,
    apiKey,
  } = useAppStore();

  const [input, setInput] = useState("Show me something under 5000");

  useEffect(() => {
    if (!sessionId && memoryEnabled) {
      setSessionId(`sess_${crypto.randomUUID().slice(0, 8)}`);
    }
  }, [sessionId, memoryEnabled, setSessionId]);

  const effectiveSession = memoryEnabled ? sessionId || undefined : undefined;

  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      const body: { message: string; session_id?: string } = { message };
      if (effectiveSession) body.session_id = effectiveSession;

      const [chatRes, agentRes] = await Promise.all([
        apiFetch<ChatResponse>({ path: "/chat", method: "POST", body }),
        apiFetch<ChatAgentConfig>({ path: "/agents/chat" }),
      ]);

      return { chatRes, agentRes };
    },
    onSuccess: ({ chatRes, agentRes }, message) => {
      if (!chatRes.ok) {
        toast.error("Chat request failed");
        setLastChatDebug({
          rawResponse: chatRes.data,
          intent: undefined,
          memoryNote: memoryEnabled
            ? `session_id=${effectiveSession ?? ""} (preferences may load when implemented)`
            : "Memory disabled — session_id omitted",
          agentSummary: "—",
          activeChatAgent: agentRes.ok ? agentRes.data : null,
        });
        return;
      }
      const data = chatRes.data;
      const agent = agentRes.ok ? agentRes.data : null;
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        at: new Date().toISOString(),
      };
      const asst: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.message,
        intent: data.intent,
        products: data.products,
        at: new Date().toISOString(),
      };
      setChatMessages((prev) => [...prev, userMsg, asst]);
      setInput("");
      setLastChatDebug({
        rawResponse: data,
        intent: data.intent,
        memoryNote: memoryEnabled
          ? `session_id sent; backend may load MemoryService preferences for this user.`
          : "session_id omitted — no cross-turn memory path.",
        agentSummary: agent
          ? `${agent.name} · model ${agent.model} · temp ${agent.temperature}`
          : "Could not load GET /agents/chat",
        activeChatAgent: agent,
      });
    },
  });

  const send = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    if (!apiKey) {
      toast.error("Set X-API-KEY in the top bar");
      return;
    }
    chatMutation.mutate(trimmed);
  };

  const cards = useMemo(() => {
    const last = [...chatMessages].reverse().find((m) => m.role === "assistant" && m.products?.length);
    return last?.products ?? [];
  }, [chatMessages]);

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      {testAgentLabel && (
        <div className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
          <span>
            Testing focus: <strong>{testAgentLabel}</strong> — chat API still resolves the store&apos;s active chat
            agent server-side.
          </span>
          <Button variant="ghost" className="text-xs" onClick={() => setTestAgentLabel(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Chat simulator" description="POST /chat — tenant from X-API-KEY only." className="lg:col-span-1">
          <div className="flex h-[420px] flex-col rounded-lg border border-slate-100 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-950/40">
            <div className="flex-1 space-y-3 overflow-y-auto p-3">
              {chatMessages.length === 0 && (
                <p className="text-sm text-ink-muted">Send a message to see the assistant reply here.</p>
              )}
              {chatMessages.map((m) => (
                <div
                  key={m.id}
                  className={
                    m.role === "user"
                      ? "ml-8 rounded-xl bg-white px-3 py-2 text-sm shadow-sm dark:bg-slate-900"
                      : "mr-8 rounded-xl bg-blue-50/80 px-3 py-2 text-sm dark:bg-blue-950/40"
                  }
                >
                  <div className="text-xs font-medium uppercase text-ink-muted">{m.role}</div>
                  <div className="mt-1 whitespace-pre-wrap text-ink dark:text-slate-100">{m.content}</div>
                  {m.intent && (
                    <div className="mt-2 font-mono text-[11px] text-accent">intent: {m.intent}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
            <label className="flex flex-1 min-w-[160px] flex-col gap-1 text-xs text-ink-muted">
              Session ID
              <input
                className="rounded-lg border border-slate-200 px-2 py-1.5 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                disabled={!memoryEnabled}
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-ink-muted">
              <input type="checkbox" checked={memoryEnabled} onChange={(e) => setMemoryEnabled(e.target.checked)} />
              Enable memory
            </label>
            <Button variant="secondary" type="button" onClick={() => clearChat()}>
              <Trash2 className="h-4 w-4" />
              Clear chat
            </Button>
          </div>
          <div className="mt-3 flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
              placeholder="User message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
            />
            <Button onClick={send} disabled={chatMutation.isPending}>
              <Send className="h-4 w-4" />
              Send
            </Button>
          </div>
        </Card>

        <div className="flex flex-col gap-4">
          <Card title="Product cards" description="From the latest assistant turn (retrieval + LLM).">
            <div className="grid gap-3 sm:grid-cols-2">
              {cards.length === 0 ? (
                <p className="text-sm text-ink-muted">No products in the last reply.</p>
              ) : (
                cards.map((p, idx) => {
                  const id = String(p.id ?? idx);
                  const title = String(p.title ?? "—");
                  const price = typeof p.price === "number" ? p.price : Number(p.price);
                  const currency = String(p.currency ?? "");
                  const img = productImage(p);
                  return (
                    <div
                      key={id}
                      className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900"
                    >
                      <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-slate-100 dark:bg-slate-800">
                        {img ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={img} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <div className="flex h-full items-center justify-center text-[10px] text-ink-muted">
                            No img
                          </div>
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="truncate font-medium text-ink dark:text-slate-100">{title}</div>
                        <div className="mt-1 font-mono text-sm text-ink-muted">
                          {currency} {Number.isFinite(price) ? price.toFixed(2) : "—"}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </Card>

          <Card title="Debug panel" description="Intent, raw payload, memory hint, resolved chat agent.">
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-xs font-medium text-ink-muted">Intent</dt>
                <dd className="font-mono text-sm">{lastChatDebug?.intent ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-ink-muted">Memory</dt>
                <dd className="text-ink-muted">{lastChatDebug?.memoryNote ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-ink-muted">Agent (GET /agents/chat)</dt>
                <dd className="break-all text-ink-muted">{lastChatDebug?.agentSummary ?? "—"}</dd>
              </div>
            </dl>
            <pre className="mt-4 max-h-56 overflow-auto rounded-lg bg-slate-950 p-3 text-[11px] leading-relaxed text-slate-100">
              {lastChatDebug ? JSON.stringify(lastChatDebug.rawResponse, null, 2) : "// send a message"}
            </pre>
            {lastChatDebug?.activeChatAgent != null && (
              <details className="mt-3 text-xs text-ink-muted">
                <summary className="cursor-pointer font-medium text-ink">Active chat agent (full)</summary>
                <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-100 p-2 dark:bg-slate-900">
                  {JSON.stringify(lastChatDebug.activeChatAgent, null, 2)}
                </pre>
              </details>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
