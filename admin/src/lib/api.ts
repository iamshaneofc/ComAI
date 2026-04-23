import { useAppStore } from "@/stores/app-store";

export type FetchOpts = {
  path: string;
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  /** Use tenant API key (default true for protected routes) */
  useApiKey?: boolean;
  /** X-Provision-Secret for bootstrap routes */
  provision?: boolean;
  headers?: Record<string, string>;
};

function normalizeBase(url: string) {
  return url.replace(/\/+$/, "");
}

export async function apiFetch<T = unknown>(opts: FetchOpts): Promise<{ ok: boolean; status: number; data: T }> {
  const {
    apiBaseUrl,
    apiKey,
    provisionSecret,
    pushSystem,
    setConnectionStatus,
  } = useAppStore.getState();

  const base = normalizeBase(apiBaseUrl || "http://127.0.0.1:8000");
  const url = `${base}/api/v1${opts.path.startsWith("/") ? opts.path : `/${opts.path}`}`;

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...opts.headers,
  };

  const useKey = opts.useApiKey !== false;
  if (useKey && apiKey) headers["X-API-KEY"] = apiKey;
  if (opts.provision && provisionSecret) headers["X-Provision-Secret"] = provisionSecret;

  let body: string | undefined;
  if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const started = performance.now();
  let status = 0;
  let parsed: unknown;

  try {
    const res = await fetch(url, { method: opts.method || "GET", headers, body });
    status = res.status;
    const text = await res.text();
    try {
      parsed = text ? JSON.parse(text) : null;
    } catch {
      parsed = text;
    }

    if (res.ok) {
      setConnectionStatus("ok");
    } else {
      setConnectionStatus("error");
    }

    const ms = Math.round(performance.now() - started);
    pushSystem(res.ok ? "api" : "error", `${opts.method || "GET"} ${opts.path}`, `${status} · ${ms}ms`, {
      url,
      response: parsed,
    });

    return { ok: res.ok, status, data: parsed as T };
  } catch (e) {
    setConnectionStatus("error");
    const msg = e instanceof Error ? e.message : "Network error";
    pushSystem("error", `${opts.method || "GET"} ${opts.path}`, msg, { url });
    throw e;
  }
}

export async function shopifyWebhookFetch(
  apiBaseUrl: string,
  path: string,
  headers: Record<string, string>,
  rawBody: string
): Promise<{ ok: boolean; status: number; data: unknown }> {
  const base = normalizeBase(apiBaseUrl || "http://127.0.0.1:8000");
  const url = `${base}/api/v1${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: rawBody,
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = text;
  }
  return { ok: res.ok, status: res.status, data: parsed };
}
