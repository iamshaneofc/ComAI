"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { shopifyWebhookHmacBase64 } from "@/lib/hmac";
import { shopifyWebhookFetch } from "@/lib/api";
import { useAppStore } from "@/stores/app-store";

const DEFAULT_BODY = `{
  "id": 9876543210,
  "title": "Admin webhook test",
  "body_html": "Synthetic product for dev panel",
  "status": "active",
  "tags": "test, dev",
  "variants": [{ "price": "29.99" }],
  "images": [{ "src": "https://cdn.shopify.com/static/images/logos/shopify-bag.png", "alt": "bag" }],
  "options": []
}`;

export default function WebhooksPage() {
  const { apiBaseUrl, pushSystem } = useAppStore();
  const [shopDomain, setShopDomain] = useState("");
  const [secret, setSecret] = useState("");
  const [rawBody, setRawBody] = useState(DEFAULT_BODY);
  const [path, setPath] = useState("/webhooks/shopify/products/create");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<unknown>(null);

  const send = async () => {
    setBusy(true);
    setLast(null);
    try {
      const body = rawBody;
      const hmac = await shopifyWebhookHmacBase64(secret, body);
      const { ok, status, data } = await shopifyWebhookFetch(apiBaseUrl, path, {
        "X-Shopify-Shop-Domain": shopDomain.trim(),
        "X-Shopify-Hmac-Sha256": hmac,
      }, body);
      setLast({ status, ok, data });
      pushSystem(ok ? "api" : "error", `Webhook ${path}`, `${status}`, data);
      toast.message(ok ? `HTTP ${status}` : `HTTP ${status} — see System Logs`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      toast.error(msg);
      pushSystem("error", "Webhook client error", msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card
        title="Shopify webhook tester"
        description="POST /api/v1/webhooks/shopify/products/create|update — requires X-Shopify-Shop-Domain, valid HMAC, and webhook_secret in store credentials."
      >
        <div className="space-y-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Endpoint</span>
            <select
              className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
              value={path}
              onChange={(e) => setPath(e.target.value)}
            >
              <option value="/webhooks/shopify/products/create">/webhooks/shopify/products/create</option>
              <option value="/webhooks/shopify/products/update">/webhooks/shopify/products/update</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">X-Shopify-Shop-Domain</span>
            <input
              className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              value={shopDomain}
              onChange={(e) => setShopDomain(e.target.value)}
              placeholder="your-shop.myshopify.com"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Webhook secret (must match store credentials.shopify.webhook_secret)</span>
            <input
              type="password"
              className="rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm dark:border-slate-700 dark:bg-slate-950"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              autoComplete="off"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-ink-muted">Raw JSON body (must match HMAC input byte-for-byte)</span>
            <textarea
              className="min-h-[200px] rounded-lg border border-slate-200 px-3 py-2 font-mono text-xs dark:border-slate-700 dark:bg-slate-950"
              value={rawBody}
              onChange={(e) => setRawBody(e.target.value)}
            />
          </label>
          <Button onClick={() => void send()} disabled={busy || !shopDomain.trim() || !secret}>
            {busy ? "Sending…" : "Send webhook"}
          </Button>
        </div>
        {last != null && (
          <pre className="mt-4 max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">
            {JSON.stringify(last, null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}
