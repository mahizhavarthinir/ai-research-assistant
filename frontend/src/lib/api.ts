/* ── API Client ───────────────────────────────────────── */

import type {
  TokenResponse,
  UserProfile,
  RegisterPayload,
  LoginPayload,
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationDetail,
  Document,
  DocumentListResponse,
  DocumentChunk,
  Integration,
  IntegrationsHealthResponse,
  DocumentCompareRequest,
  DocumentCompareResponse,
  ResearchReportRequest,
  ResearchReportResponse,
} from "@/types";

const API_BASE = (() => {
  const customUrl = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL;
  // If custom URL is set and not pointing to localhost in production, use it
  if (customUrl && !(process.env.NODE_ENV === "production" && customUrl.includes("localhost"))) {
    return customUrl.replace(/\/+$/, "");
  }
  // In the browser, always default to the unified same-origin reverse proxy
  if (typeof window !== "undefined") {
    return "/api/v1";
  }
  // In server-side rendering or node environment, fall back to backend URL
  return (
    process.env.BACKEND_INTERNAL_URL ||
    (process.env.NODE_ENV === "production"
      ? "https://ai-research-assistant-backend-j2sj.onrender.com/api/v1"
      : "http://localhost:8000/api/v1")
  );
})();

/* ── Token Management ────────────────────────────────── */

let accessToken: string | null = null;

export function setToken(token: string) {
  accessToken = token;
  if (typeof window !== "undefined") {
    localStorage.setItem("access_token", token);
  }
}

export function getToken(): string | null {
  if (accessToken) return accessToken;
  if (typeof window !== "undefined") {
    accessToken = localStorage.getItem("access_token");
  }
  return accessToken;
}

export function clearToken() {
  accessToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }
}

/* ── Fetch Wrapper ───────────────────────────────────── */

let isRefreshing = false;

async function tryRefreshToken(): Promise<boolean> {
  if (typeof window === "undefined") return false;
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken || isRefreshing) return false;

  isRefreshing = true;
  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (response.ok) {
      const data = await response.json();
      if (data.access_token) {
        setToken(data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        return true;
      }
    }
  } catch {
    // Refresh failed — fall through to logout
  } finally {
    isRefreshing = false;
  }
  return false;
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Only set Content-Type for non-FormData
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 || (response.status === 403 && !getToken())) {
    // Try refreshing the token before giving up
    if (response.status === 401) {
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        // Retry the original request with the new token
        const newHeaders = { ...headers, Authorization: `Bearer ${getToken()}` };
        const retryResponse = await fetch(`${API_BASE}${path}`, {
          ...options,
          headers: newHeaders,
        });
        if (retryResponse.ok) {
          if (retryResponse.status === 204) return undefined as T;
          return retryResponse.json();
        }
      }
    }
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

/* ── Auth API ────────────────────────────────────────── */

export const authApi = {
  async register(data: RegisterPayload): Promise<TokenResponse> {
    const result = await apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    setToken(result.access_token);
    if (typeof window !== "undefined") {
      localStorage.setItem("refresh_token", result.refresh_token);
    }
    return result;
  },

  async login(data: LoginPayload): Promise<TokenResponse> {
    const result = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
    setToken(result.access_token);
    if (typeof window !== "undefined") {
      localStorage.setItem("refresh_token", result.refresh_token);
    }
    return result;
  },

  async logout(): Promise<void> {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      clearToken();
    }
  },

  async getProfile(): Promise<UserProfile> {
    return apiFetch<UserProfile>("/auth/me");
  },
};

/* ── Chat API ────────────────────────────────────────── */

export type ExportFormat = "markdown" | "json" | "pdf" | "docx";

export const chatApi = {
  async sendMessage(data: ChatRequest): Promise<ChatResponse> {
    return apiFetch<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async regenerate(
    conversationId: string,
    documentId?: string
  ): Promise<ChatResponse> {
    return apiFetch<ChatResponse>(
      `/chat/conversations/${conversationId}/regenerate`,
      {
        method: "POST",
        body: JSON.stringify({ document_id: documentId || null }),
      }
    );
  },

  async exportConversation(
    conversationId: string,
    format: ExportFormat
  ): Promise<Blob> {
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const response = await fetch(
      `${API_BASE}/chat/conversations/${conversationId}/export?format=${format}`,
      { headers }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Export failed");
    }
    return response.blob();
  },

  async listConversations(
    page = 1,
    perPage = 50,
    query?: string
  ): Promise<Conversation[]> {
    const searchParams = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    });
    if (query && query.trim()) {
      searchParams.set("query", query.trim());
    }
    return apiFetch<Conversation[]>(
      `/chat/conversations?${searchParams.toString()}`
    );
  },

  async getConversation(id: string): Promise<ConversationDetail> {
    return apiFetch<ConversationDetail>(`/chat/conversations/${id}`);
  },

  async updateConversation(id: string, title: string): Promise<Conversation> {
    return apiFetch<Conversation>(`/chat/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
  },

  async deleteConversation(id: string): Promise<void> {
    return apiFetch(`/chat/conversations/${id}`, { method: "DELETE" });
  },
};

/* ── Documents API ───────────────────────────────────── */

export const documentsApi = {
  async upload(file: File): Promise<Document> {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<Document>("/documents/upload", {
      method: "POST",
      body: formData,
    });
  },

  async ingestUrl(url: string): Promise<Document> {
    return apiFetch<Document>("/documents/ingest-url", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
  },

  async list(params?: {
    query?: string;
    file_type?: string;
    status?: string;
  }): Promise<DocumentListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.query) searchParams.set("query", params.query);
    if (params?.file_type) searchParams.set("file_type", params.file_type);
    if (params?.status) searchParams.set("status", params.status);
    const qs = searchParams.toString();
    return apiFetch<DocumentListResponse>(`/documents${qs ? `?${qs}` : ""}`);
  },

  async retry(id: string): Promise<Document> {
    return apiFetch<Document>(`/documents/${id}/retry`, {
      method: "POST",
    });
  },

  async getChunks(id: string): Promise<DocumentChunk[]> {
    return apiFetch<DocumentChunk[]>(`/documents/${id}/chunks`);
  },

  async get(id: string): Promise<Document> {
    return apiFetch<Document>(`/documents/${id}`);
  },

  async delete(id: string): Promise<void> {
    return apiFetch(`/documents/${id}`, { method: "DELETE" });
  },
};

/* ── Integrations API ────────────────────────────────── */

export const integrationsApi = {
  async list(): Promise<Integration[]> {
    return apiFetch<Integration[]>("/integrations");
  },

  async health(): Promise<IntegrationsHealthResponse> {
    return apiFetch<IntegrationsHealthResponse>("/integrations/health");
  },

  async execute(id: string): Promise<Record<string, unknown>> {
    return apiFetch(`/integrations/${id}/execute`, { method: "POST" });
  },
};

/* ── Research API (Phase 4) ──────────────────────────── */

export const researchApi = {
  async compareDocuments(
    payload: DocumentCompareRequest
  ): Promise<DocumentCompareResponse> {
    return apiFetch<DocumentCompareResponse>("/research/compare", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async generateReport(
    payload: ResearchReportRequest
  ): Promise<ResearchReportResponse> {
    return apiFetch<ResearchReportResponse>("/research/report", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async exportContent(
    payload: Record<string, unknown>,
    format: ExportFormat
  ): Promise<Blob> {
    const token = getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const response = await fetch(
      `${API_BASE}/research/export?format=${format}`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Export failed");
    }
    return response.blob();
  },
};
