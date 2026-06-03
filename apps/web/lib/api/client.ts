export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function createApiClient(getToken: () => Promise<string | null>) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

  async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const token = await getToken();
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options?.headers as Record<string, string>),
      },
    });

    if (!res.ok) {
      throw new ApiError(`API error: ${res.status} ${res.statusText}`, res.status);
    }

    return res.json() as Promise<T>;
  }

  return {
    // Organizations
    fetchMyOrgs: () => request<{ organizations: any[] }>("/orgs/me"),
    createOrg: (data: { slug: string; name: string }) =>
      request<any>("/orgs", { method: "POST", body: JSON.stringify(data) }),

    // Projects
    fetchProjects: (orgId: string) =>
      request<{ projects: any[] }>(`/orgs/${orgId}/projects`),
    createProject: (orgId: string, data: { slug: string; name: string; description?: string }) =>
      request<any>(`/orgs/${orgId}/projects`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // GitHub Integration
    getGitHubInstallUrl: (orgSlug?: string) =>
      request<{ install_url: string }>(`/integrations/github/install-url?${orgSlug ? `org_slug=${orgSlug}` : ""}`),
    listInstallations: (orgId?: string) =>
      request<Array<{ id: string; account_login: string; account_type: string; repos: Array<{ id: number; name: string; full_name: string; private: boolean; default_branch: string; language: string | null }> }>>(
        `/integrations/github/installations${orgId ? `?org_id=${orgId}` : ""}`
      ),

    // Search
    search: (data: { project_id: string; query: string; k?: number; mode?: string; filters?: Record<string, unknown> }) =>
      request<{ results: Array<{ chunk_id: string; score: number; source: Record<string, string>; snippet: string }>; mode: string; took_ms: number }>(
        "/search",
        { method: "POST", body: JSON.stringify(data) },
      ),
    searchPreview: (data: { project_id: string; query: string; max_chunks?: number; mode?: string }) =>
      request<{ items: Array<{ chunk_id: string; score: number; source: Record<string, string>; snippet: string; relevance: string }>; total_chunks: number; took_ms: number }>(
        "/search/preview",
        { method: "POST", body: JSON.stringify(data) },
      ),

    // Chats
    createConversation: (projectId: string) =>
      request<{ id: string; project_id: string; title: string | null; created_at: string; updated_at: string }>(
        "/chat/conversations",
        { method: "POST", body: JSON.stringify({ project_id: projectId }) },
      ),
    getConversation: (conversationId: string) =>
      request<{ id: string; project_id: string; title: string | null; messages: Array<{ id: string; conversation_id: string; role: string; content: string; model: string | null; tokens_in: number | null; tokens_out: number | null; citations: Array<{ chunk_id: string; score: number; source_type: string; path: string; snippet: string }>; created_at: string }>; created_at: string; updated_at: string }>(
        `/chat/conversations/${conversationId}`,
      ),
    sendMessage: (conversationId: string, content: string, model?: string) =>
      request<{ id: string; conversation_id: string; role: string; content: string; model: string | null; tokens_in: number | null; tokens_out: number | null; citations: Array<{ chunk_id: string; score: number; source_type: string; path: string; snippet: string }>; created_at: string }>(
        `/chat/conversations/${conversationId}/messages`,
        { method: "POST", body: JSON.stringify({ content, model }) },
      ),
    deleteConversation: (conversationId: string) =>
      request<{ status: string }>(`/chat/conversations/${conversationId}`, { method: "DELETE" }),

    // Memory
    listFacts: (projectId: string, scope?: string) =>
      request<{ facts: Array<{ id: string; project_id: string; scope: string; statement: string; source: string; confidence: number; created_at: string; expires_at: string | null }> }>(
        `/memory/facts?project_id=${projectId}${scope ? `&scope=${scope}` : ""}`,
      ),
    assertFact: (data: { project_id: string; statement: string; scope?: string; confidence?: number }) =>
      request<{ id: string; project_id: string; scope: string; statement: string; source: string; confidence: number; created_at: string }>(
        "/memory/facts",
        { method: "POST", body: JSON.stringify(data) },
      ),
    deleteFact: (factId: string) =>
      request<{ status: string }>(`/memory/facts/${factId}`, { method: "DELETE" }),

    // Agents
    runAgent: (data: { project_id: string; agent_type: string; input?: Record<string, string> }) =>
      request<{ session_id: string; status: string }>("/agents/run", { method: "POST", body: JSON.stringify(data) }),
    listAgentSessions: (projectId: string) =>
      request<{ sessions: Array<{ id: string; agent_type: string; status: string; output: Record<string, unknown> | null; started_at: string; ended_at: string | null }> }>(
        `/agents/sessions?project_id=${projectId}`,
      ),
    getAgentSession: (sessionId: string) =>
      request<{ id: string; agent_type: string; status: string; output: Record<string, unknown> | null; started_at: string; ended_at: string | null }>(
        `/agents/sessions/${sessionId}`,
      ),
    getAgentSessionEvents: (sessionId: string) =>
      request<{ events: Array<{ id: number; kind: string; payload: Record<string, unknown>; ts: string }> }>(
        `/agents/sessions/${sessionId}/events`,
      ),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
