"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api";

type ProductRow = {
  id: string;
  title: string;
  price: number;
  currency: string;
  tags: string[] | null;
  source_platform: string;
};

type SearchResponse = {
  items: ProductRow[];
  total: number;
  offset: number;
  limit: number;
};

export default function ProductsPage() {
  const [keyword, setKeyword] = useState("");
  const [rawJson, setRawJson] = useState(false);

  const query = useQuery({
    queryKey: ["products-search", keyword],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: "50", offset: "0" });
      if (keyword.trim()) params.set("keyword", keyword.trim());
      const r = await apiFetch<SearchResponse>({ path: `/products/search?${params.toString()}` });
      if (!r.ok) {
        toast.error("Product search failed");
        throw new Error("bad");
      }
      return r.data;
    },
    enabled: false,
  });

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <Card title="Catalog" description="GET /products/search — uses tenant API key.">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
          <input
            className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
            placeholder="Search keyword (optional)"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void query.refetch()}
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => void query.refetch()} disabled={query.isFetching}>
              {query.isFetching ? "Loading…" : "Fetch products"}
            </Button>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-ink-muted">
              <input type="checkbox" checked={rawJson} onChange={(e) => setRawJson(e.target.checked)} />
              Raw JSON
            </label>
          </div>
        </div>
        {query.error && <p className="mt-2 text-sm text-coral">Request failed — check API key and base URL.</p>}
        {rawJson && query.data ? (
          <pre className="mt-4 max-h-[480px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">
            {JSON.stringify(query.data, null, 2)}
          </pre>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50/80 text-xs uppercase text-ink-muted dark:border-slate-800 dark:bg-slate-900/50">
                <tr>
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium">Price</th>
                  <th className="px-4 py-3 font-medium">Tags</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {(query.data?.items ?? []).map((p, i) => (
                  <tr key={p.id} className={i % 2 ? "bg-slate-50/40 dark:bg-slate-900/30" : ""}>
                    <td className="px-4 py-2 font-medium text-ink dark:text-slate-100">{p.title}</td>
                    <td className="px-4 py-2 font-mono text-xs">
                      {p.currency} {p.price.toFixed(2)}
                    </td>
                    <td className="max-w-xs truncate px-4 py-2 text-ink-muted">
                      {(p.tags || []).join(", ") || "—"}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-ink-muted">{p.source_platform}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {query.data && (
              <div className="border-t border-slate-200 px-4 py-2 text-xs text-ink-muted dark:border-slate-800">
                Total: {query.data.total} · showing {query.data.items.length}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
