import { create } from "zustand";
import { persist } from "zustand/middleware";

export type LogEntry = {
  id: string;
  at: string;
  kind: "info" | "error" | "automation" | "api";
  title: string;
  detail?: string;
  meta?: unknown;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  products?: Record<string, unknown>[];
  at: string;
};

export type ChatDebugSnapshot = {
  rawResponse: unknown;
  intent?: string;
  memoryNote: string;
  agentSummary: string;
  activeChatAgent?: unknown;
};

type AppState = {
  apiBaseUrl: string;
  apiKey: string;
  provisionSecret: string;
  storeId: string;
  sessionId: string;
  memoryEnabled: boolean;
  chatMessages: ChatMessage[];
  lastChatDebug: ChatDebugSnapshot | null;
  automationLogs: LogEntry[];
  systemLogs: LogEntry[];
  testAgentLabel: string | null;
  connectionStatus: "idle" | "ok" | "error";
  setApiBaseUrl: (v: string) => void;
  setApiKey: (v: string) => void;
  setProvisionSecret: (v: string) => void;
  setStoreId: (v: string) => void;
  setSessionId: (v: string) => void;
  setMemoryEnabled: (v: boolean) => void;
  setChatMessages: (fn: (prev: ChatMessage[]) => ChatMessage[]) => void;
  clearChat: () => void;
  setLastChatDebug: (v: ChatDebugSnapshot | null) => void;
  pushAutomation: (title: string, detail?: string, meta?: unknown) => void;
  clearAutomationLogs: () => void;
  pushSystem: (kind: LogEntry["kind"], title: string, detail?: string, meta?: unknown) => void;
  clearSystemLogs: () => void;
  setTestAgentLabel: (v: string | null) => void;
  setConnectionStatus: (v: AppState["connectionStatus"]) => void;
};

const uid = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      apiBaseUrl:
        typeof window !== "undefined"
          ? process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"
          : "http://127.0.0.1:8000",
      apiKey: "",
      provisionSecret: "",
      storeId: "",
      sessionId: "",
      memoryEnabled: true,
      chatMessages: [],
      lastChatDebug: null,
      automationLogs: [],
      systemLogs: [],
      testAgentLabel: null,
      connectionStatus: "idle",
      setApiBaseUrl: (v) => set({ apiBaseUrl: v }),
      setApiKey: (v) => set({ apiKey: v }),
      setProvisionSecret: (v) => set({ provisionSecret: v }),
      setStoreId: (v) => set({ storeId: v }),
      setSessionId: (v) => set({ sessionId: v }),
      setMemoryEnabled: (v) => set({ memoryEnabled: v }),
      setChatMessages: (fn) => set({ chatMessages: fn(get().chatMessages) }),
      clearChat: () => set({ chatMessages: [], lastChatDebug: null }),
      setLastChatDebug: (v) => set({ lastChatDebug: v }),
      pushAutomation: (title, detail, meta) =>
        set({
          automationLogs: [
            {
              id: uid(),
              at: new Date().toISOString(),
              kind: "automation" as const,
              title,
              detail,
              meta,
            } satisfies LogEntry,
            ...get().automationLogs,
          ].slice(0, 200),
        }),
      clearAutomationLogs: () => set({ automationLogs: [] }),
      pushSystem: (kind, title, detail, meta) =>
        set({
          systemLogs: [
            { id: uid(), at: new Date().toISOString(), kind, title, detail, meta } satisfies LogEntry,
            ...get().systemLogs,
          ].slice(0, 300),
        }),
      clearSystemLogs: () => set({ systemLogs: [] }),
      setTestAgentLabel: (v) => set({ testAgentLabel: v }),
      setConnectionStatus: (v) => set({ connectionStatus: v }),
    }),
    {
      name: "comai-admin",
      partialize: (s) => ({
        apiBaseUrl: s.apiBaseUrl,
        apiKey: s.apiKey,
        provisionSecret: s.provisionSecret,
        storeId: s.storeId,
        sessionId: s.sessionId,
        memoryEnabled: s.memoryEnabled,
      }),
    }
  )
);
