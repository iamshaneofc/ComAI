"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Copy, RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/stores/app-store";

type StoreCreated = {
  id: string;
  api_key: string;
  name: string;
  platform: string;
  onboarding_status?: string;
};

type MeStatus = {
  onboarding_status: string;
  products_count: number;
  agent_ready: boolean;
};

function copyText(label: string, value: string) {
  void navigator.clipboard.writeText(value);
  toast.success(`${label} copied`);
}

export default function StoreSetupPage() {
  const {
    provisionSecret,
    setProvisionSecret,
    setApiKey,
    setStoreId,
    apiKey,
    storeId,
    pushAutomation,
  } = useAppStore();

  const [name, setName] = useState("Dev Store");
  const [platform, setPlatform] = useState<"shopify" | "custom">("custom");
  const [shopDomain, setShopDomain] = useState("");
  const [shopToken, setShopToken] = useState("");
  const [shopName, setShopName] = useState("");

  const statusQuery = useQuery({
    queryKey: ["store-me-status", apiKey],
    queryFn: async () => {
      const r = await apiFetch<MeStatus>({ path: "/stores/me/status" });
      if (!r.ok) throw new Error("Failed to load status");
      return r.data;
    },
    enabled: !!apiKey,
    refetchInterval: (q) => {
      const s = q.state.data?.onboarding_status;
      if (s === "syncing" || s === "connected") return 3000;
      return false;
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const r = await apiFetch<StoreCreated>({
        path: "/stores",
        method: "POST",
        provision: true,
        useApiKey: false,
        body: { name, platform },
      });
      return r;
    },
    onSuccess: (r) => {
      if (!r.ok) {
        toast.error("Create store failed");
        return;
      }
      const d = r.data;
      setApiKey(d.api_key);
      setStoreId(d.id);
      toast.success("Store created");
      pushAutomation("Store provisioned", d.name, d);
    },
  });

  const onboardMutation = useMutation({
    mutationFn: async () => {
      const r = await apiFetch<StoreCreated>({
        path: "/stores/onboard",
        method: "POST",
        provision: true,
        useApiKey: false,
        body: {
          platform: "shopify",
          domain: shopDomain.trim(),
          token: shopToken.trim(),
          name: shopName.trim() || undefined,
        },
      });
      return r;
    },
    onSuccess: (r) => {
      if (!r.ok) {
        toast.error("Shopify onboard failed");
        return;
      }
      const d = r.data;
      setApiKey(d.api_key);
      setStoreId(d.id);
      toast.success("Shopify connect queued");
      pushAutomation("Shopify onboarding queued", d.name, d);
      void statusQuery.refetch();
    },
  });

  const status = statusQuery.data;
  const statusLabel = status?.onboarding_status ?? "—";
  const uiStatus =
    statusLabel === "ready"
      ? "Completed"
      : statusLabel === "syncing"
        ? "Syncing"
        : statusLabel === "failed"
          ? "Error"
          : statusLabel === "connected"
            ? "Pending (worker)"
            : statusLabel === "created"
              ? "Pending"
              : statusLabel;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <Card title="Platform secret" description="Required for POST /stores and POST /stores/onboard (X-Provision-Secret).">
        <input
          type="password"
          className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
          value={provisionSecret}
          onChange={(e) => setProvisionSecret(e.target.value)}
          placeholder="APP_SECRET_KEY from backend .env"
          autoComplete="off"
        />
      </Card>

      <Card title="Create store" description="Provisioning endpoint — returns tenant API key once.">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <label className="flex flex-1 flex-col gap-1 text-sm">
            <span className="text-ink-muted">Store name</span>
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="flex w-full flex-col gap-1 text-sm sm:w-48">
            <span className="text-ink-muted">Platform</span>
            <select
              className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
              value={platform}
              onChange={(e) => setPlatform(e.target.value as "shopify" | "custom")}
            >
              <option value="shopify">Shopify</option>
              <option value="custom">Custom</option>
            </select>
          </label>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending || !provisionSecret}
          >
            {createMutation.isPending ? "Creating…" : "Create store"}
          </Button>
        </div>
        {createMutation.data?.ok === false && (
          <pre className="mt-3 overflow-auto rounded-lg bg-slate-50 p-3 text-xs dark:bg-slate-950">
            {JSON.stringify(createMutation.data.data, null, 2)}
          </pre>
        )}
      </Card>

      <Card
        title="Shopify onboarding"
        description="POST /stores/onboard — matches by domain or creates a new Shopify store, then queues sync + default chat agent."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm sm:col-span-2">
            <span className="text-ink-muted">Shopify domain</span>
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              value={shopDomain}
              onChange={(e) => setShopDomain(e.target.value)}
              placeholder="your-shop.myshopify.com"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm sm:col-span-2">
            <span className="text-ink-muted">Admin API access token</span>
            <input
              type="password"
              className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              value={shopToken}
              onChange={(e) => setShopToken(e.target.value)}
              placeholder="shpat_…"
              autoComplete="off"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm sm:col-span-2">
            <span className="text-ink-muted">Display name (optional)</span>
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
              value={shopName}
              onChange={(e) => setShopName(e.target.value)}
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button onClick={() => onboardMutation.mutate()} disabled={onboardMutation.isPending || !provisionSecret}>
            {onboardMutation.isPending ? "Connecting…" : "Connect Shopify"}
          </Button>
          <Button variant="secondary" type="button" onClick={() => void statusQuery.refetch()} disabled={!apiKey}>
            <RefreshCw className="h-4 w-4" />
            Refresh status
          </Button>
        </div>
        <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50/80 p-4 text-sm dark:border-slate-800 dark:bg-slate-950/50">
          <div className="font-medium text-ink dark:text-slate-100">Onboarding status</div>
          <dl className="mt-2 grid gap-2 sm:grid-cols-3">
            <div>
              <dt className="text-xs text-ink-muted">State</dt>
              <dd className="font-mono text-sm">{uiStatus}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-muted">Products</dt>
              <dd className="font-mono text-sm">{status?.products_count ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-muted">Chat agent</dt>
              <dd className="font-mono text-sm">{status?.agent_ready ? "Ready" : "Not ready"}</dd>
            </div>
          </dl>
          {statusQuery.error && (
            <p className="mt-2 text-xs text-coral">Set X-API-KEY in the top bar to poll /stores/me/status.</p>
          )}
        </div>
      </Card>

      <Card title="Credentials" description="Saved globally after create or onboard (also persisted locally).">
        <div className="space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-ink-muted">Store ID</span>
            <code className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs dark:bg-slate-800">
              {storeId || "—"}
            </code>
            {storeId ? (
              <button
                type="button"
                className="text-accent hover:underline"
                onClick={() => copyText("Store ID", storeId)}
              >
                <Copy className="inline h-3.5 w-3.5" />
              </button>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-ink-muted">API key</span>
            <span className="font-mono text-xs text-ink-muted">{apiKey ? "••••••••" + apiKey.slice(-6) : "—"}</span>
            {apiKey ? (
              <Button variant="secondary" className="py-1 text-xs" onClick={() => copyText("API key", apiKey)}>
                Copy API key
              </Button>
            ) : null}
          </div>
        </div>
      </Card>
    </div>
  );
}
