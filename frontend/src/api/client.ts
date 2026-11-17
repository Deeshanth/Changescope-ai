import type {
  AIReport,
  AnalysisRunDetail,
  AnalysisRunSummary,
  CommitInfo,
  GraphView,
  NodeNeighborhood,
  RepoFile,
  RepoOverview,
  Repository,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`/api${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // ignore json parse error
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () =>
    request<{ status: string; app: string; ai_enabled: boolean }>("/health"),

  listRepositories: () => request<Repository[]>("/repositories"),

  registerRepository: (local_path: string, name?: string) =>
    request<Repository>("/repositories", {
      method: "POST",
      body: JSON.stringify({ local_path, name: name || undefined }),
    }),

  rescanRepository: (repoId: number) =>
    request<Repository>(`/repositories/${repoId}/scan`, { method: "POST" }),

  listFiles: (repoId: number) => request<RepoFile[]>(`/repositories/${repoId}/files`),

  listCommits: (repoId: number, limit = 50) =>
    request<CommitInfo[]>(`/repositories/${repoId}/commits?limit=${limit}`),

  getOverview: (repoId: number) =>
    request<RepoOverview>(`/repositories/${repoId}/overview`),

  getGraph: (
    repoId: number,
    params: {
      level?: "symbol" | "module";
      node_type?: string;
      focus_node_id?: number;
      depth?: number;
      include_tests?: boolean;
      limit?: number;
    }
  ) => {
    const qs = new URLSearchParams();
    if (params.level) qs.set("level", params.level);
    if (params.node_type) qs.set("node_type", params.node_type);
    if (params.focus_node_id !== undefined) qs.set("focus_node_id", String(params.focus_node_id));
    if (params.depth !== undefined) qs.set("depth", String(params.depth));
    if (params.include_tests !== undefined) qs.set("include_tests", String(params.include_tests));
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    return request<GraphView>(`/repositories/${repoId}/graph?${qs.toString()}`);
  },

  getNodeDetails: (repoId: number, nodeId: number) =>
    request<NodeNeighborhood>(`/repositories/${repoId}/nodes/${nodeId}`),

  runAnalysis: (repoId: number, base_commit: string, head_commit: string, max_depth = 5) =>
    request<AnalysisRunDetail>(`/repositories/${repoId}/analyses`, {
      method: "POST",
      body: JSON.stringify({ base_commit, head_commit, max_depth }),
    }),

  listAnalyses: (repoId: number) =>
    request<AnalysisRunSummary[]>(`/repositories/${repoId}/analyses`),

  getAnalysisDetail: (analysisId: number) =>
    request<AnalysisRunDetail>(`/analyses/${analysisId}`),

  getAIReport: (analysisId: number) =>
    request<AIReport>(`/analyses/${analysisId}/ai-report`),

  generateAIReport: (analysisId: number, regenerate = false) =>
    request<AIReport>(`/analyses/${analysisId}/ai-report`, {
      method: "POST",
      body: JSON.stringify({ regenerate }),
    }),
};
