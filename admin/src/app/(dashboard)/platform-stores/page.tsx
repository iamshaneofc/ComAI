"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/stores/app-store";

type PlatformStoreRow = {
  id: string;
  name: string;
  slug: string;
  platform: string;
  domain: string | null;
  onboarding_status: string;
  is_active: boolean;
  created_at: string;
  api_key: string;
};

type PaginatedPlatform = {
  items: PlatformStoreRow[];
  total: number;
  offset: number;
  limit: number;
};

type StoreMe = {
  id: string;
  name: string;
  slug: string;
  platform: string;
  domain: string | null;
  onboarding_status: string;
};

type MeStatus = {
  onboarding_status: string;
  products_count: number;
  agent_ready: boolean;
};

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export default function PlatformStoresPage() {
  const queryClient = useQueryClient();
  const { provisionSecret, apiKey, storeId, setApiKey, setStoreId } = useAppStore();
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const listQuery = useQuery({
    queryKey: ["platform-stores", provisionSecret, offset, limit],
    queryFn: async () => {
      const params = new URLSearchParams({
        offset: String(offset),
        limit: String(limit),
        active_only: "true",
      });
      const r = await apiFetch<PaginatedPlatform>({
        path: `/platform/stores?${params.toString()}`,
        provision: true,
        useApiKey: false,
      });
      if (!r.ok) throw new Error("list failed");
      return r.data;
    },
    enabled: !!provisionSecret.trim(),
  });

  const deleteMutation = useMutation({
    mutationFn: async (row: PlatformStoreRow) => {
      const r = await apiFetch<unknown>({
        path: `/platform/stores/${row.id}`,
        method: "DELETE",
        provision: true,
        useApiKey: false,
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return row;
    },
    onSuccess: (row) => {
      void queryClient.invalidateQueries({ queryKey: ["platform-stores"] });
      if (apiKey === row.api_key || storeId === row.id) {
        setApiKey("");
        setStoreId("");
      }
      toast.success(`Store deactivated: ${row.name}`);
    },
    onError: (e) => {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    },
  });

  const smokeMutation = useMutation({
    mutationFn: async () => {
      const key = useAppStore.getState().apiKey;
      if (!key) throw new Error("no_api_key");

      const me = await apiFetch<StoreMe>({ path: "/stores/me" });
      if (!me.ok) throw new Error(`stores/me: ${me.status}`);

      const st0 = await apiFetch<MeStatus>({ path: "/stores/me/status" });
      if (!st0.ok) throw new Error(`stores/me/status: ${st0.status}`);

      const sync = await apiFetch<unknown>({ path: "/stores/me/sync", method: "POST" });
      if (!sync.ok && sync.status !== 202) throw new Error(`stores/me/sync: ${sync.status}`);

      let last: MeStatus | null = null;
      for (let i = 0; i < 12; i++) {
        await sleep(2000);
        const st = await apiFetch<MeStatus>({ path: "/stores/me/status" });
        if (!st.ok) throw new Error(`poll status: ${st.status}`);
        last = st.data;
        if (last.onboarding_status === "ready" || last.onboarding_status === "failed") break;
      }
      return { me: me.data, last };
    },
    onSuccess: (d) => {
      toast.success(
        `Smoke done — status: ${d.last?.onboarding_status ?? "?"}, products: ${d.last?.products_count ?? "?"}, agent: ${d.last?.agent_ready ? "yes" : "no"}`
      );
    },
    onError: (e) => {
      toast.error(e instanceof Error ? e.message : "Smoke failed");
    },
  });

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <Card
        title="All stores (platform)"
        description="GET /api/v1/platform/stores and DELETE /api/v1/platform/stores/{id} — require Platform secret (X-Provision-Secret). Delete soft-deactivates the tenant (API key stops working). Never expose these routes on the public internet."
      >
        <p className="mb-3 text-sm text-ink-muted">
          Set <strong>Platform secret</strong> on{" "}
          <Link href="/store-setup" className="text-accent underline">
            Store Setup
          </Link>{" "}
          first, then load the list.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => void listQuery.refetch()} disabled={!provisionSecret.trim() || listQuery.isFetching}>
            {listQuery.isFetching ? "Loading…" : "Load / refresh stores"}
          </Button>
          <Button
            variant="secondary"
            type="button"
            onClick={() => setOffset((o) => Math.max(0, o - limit))}
            disabled={offset === 0 || listQuery.isFetching}
          >
            Previous page
          </Button>
          <Button
            variant="secondary"
            type="button"
            onClick={() => setOffset((o) => o + limit)}
            disabled={
              listQuery.isFetching ||
              !listQuery.data ||
              offset + limit >= listQuery.data.total
            }
          >
            Next page
          </Button>
          <span className="text-xs text-ink-muted">
            offset {offset} · limit {limit}
            {listQuery.data != null ? ` · total ${listQuery.data.total}` : ""}
          </span>
        </div>
        {listQuery.error && (
          <p className="mt-2 text-sm text-coral">Failed to load — check provision secret matches backend APP_SECRET_KEY.</p>
        )}
        {listQuery.data && (
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/80 text-xs uppercase text-ink-muted dark:border-slate-800 dark:bg-slate-900/50">
                <tr>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Slug</th>
                  <th className="px-3 py-2">Platform</th>
                  <th className="px-3 py-2">Domain</th>
                  <th className="px-3 py-2">Onboarding</th>
                  <th className="px-3 py-2">Active</th>
                  <th className="px-3 py-2">Created</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {listQuery.data.items.map((row, i) => (
                  <tr key={row.id} className={i % 2 ? "bg-slate-50/40 dark:bg-slate-900/30" : ""}>
                    <td className="px-3 py-2 font-medium">{row.name}</td>
                    <td className="px-3 py-2 font-mono text-xs">{row.slug}</td>
                    <td className="px-3 py-2">{row.platform}</td>
                    <td className="max-w-[200px] truncate px-3 py-2 font-mono text-xs">{row.domain ?? "—"}</td>
                    <td className="px-3 py-2 font-mono text-xs">{row.onboarding_status}</td>
                    <td className="px-3 py-2">{row.is_active ? "yes" : "no"}</td>
                    <td className="px-3 py-2 text-xs text-ink-muted">
                      {row.created_at ? new Date(row.created_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="secondary"
                          className="py-1 text-xs"
                          type="button"
                          onClick={() => {
                            void navigator.clipboard.writeText(row.api_key);
                            toast.success("API key copied");
                          }}
                        >
                          Copy API key
                        </Button>
                        <Button
                          className="py-1 text-xs"
                          type="button"
                          onClick={() => {
                            setApiKey(row.api_key);
                            setStoreId(row.id);
                            toast.success("Top bar updated — X-API-KEY is set for this store");
                          }}
                        >
                          Use store
                        </Button>
                        <Button
                          variant="danger"
                          className="py-1 text-xs"
                          type="button"
                          disabled={deleteMutation.isPending}
                          onClick={() => {
                            if (
                              !window.confirm(
                                `Deactivate store "${row.name}"? Its API key will stop working. This cannot be undone from the admin UI.`
                              )
                            ) {
                              return;
                            }
                            deleteMutation.mutate(row);
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {listQuery.data.items.length === 0 && (
              <p className="p-4 text-sm text-ink-muted">No stores returned.</p>
            )}
          </div>
        )}
      </Card>

      <Card
        title="Smoke test (tenant session)"
        description="Uses current X-API-KEY from the top bar: GET /stores/me → GET /stores/me/status → POST /stores/me/sync → poll status (up to ~24s)."
      >
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            onClick={() => smokeMutation.mutate()}
            disabled={!apiKey.trim() || smokeMutation.isPending}
          >
            {smokeMutation.isPending ? "Running…" : "Run smoke (current API key)"}
          </Button>
          <Link href="/products">
            <Button variant="secondary" type="button">
              Open Products
            </Button>
          </Link>
        </div>
        {!apiKey.trim() && (
          <p className="mt-2 text-xs text-ink-muted">Use “Use store” above or paste X-API-KEY in the top bar first.</p>
        )}
      </Card>
    </div>
  );
}
