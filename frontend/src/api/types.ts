export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface RepositoryStats {
  file_count: number;
  node_count: number;
  edge_count: number;
  parse_error_count: number;
}

export interface Repository {
  id: number;
  name: string;
  local_path: string;
  default_branch: string | null;
  last_indexed_commit: string | null;
  last_indexed_at: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
  stats: RepositoryStats | null;
}

export interface RepoFile {
  id: number;
  file_path: string;
  language: string;
  loc: number;
  is_test: boolean;
  parse_status: string;
  parse_error: string | null;
}

export interface CommitInfo {
  commit_hash: string;
  short_hash: string;
  author_name: string;
  committed_at: string;
  subject: string;
}

export interface RepoOverview {
  repository_id: number;
  name: string;
  last_indexed_commit: string | null;
  total_files: number;
  test_files: number;
  total_loc: number;
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
  parse_status_counts: Record<string, number>;
  top_fan_in_hotspots: Array<{
    id: number;
    node_key: string;
    node_type: string;
    file_path: string;
    fan_in: number;
    fan_out: number;
    complexity: number;
  }>;
  top_complex_symbols: Array<{
    id: number;
    node_key: string;
    node_type: string;
    file_path: string;
    complexity: number;
    fan_in: number;
  }>;
}

export interface GraphNode {
  id: number;
  node_key: string;
  node_type: string;
  name: string;
  file_path: string;
  start_line: number;
  end_line: number;
  complexity: number;
  fan_in: number;
  fan_out: number;
  is_test: boolean;
}

export interface GraphEdge {
  source: number;
  target: number;
  edge_type: string;
  edge_types: string[];
  confidence: string;
  weight: number;
}

export interface GraphView {
  level: "symbol" | "module";
  total_nodes_in_repo: number;
  returned_nodes: number;
  returned_edges: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NodeNeighborhood {
  node: GraphNode;
  dependencies: Array<{
    id: number;
    node_key: string;
    node_type: string;
    file_path: string;
    edge_types: string[];
    confidence: string;
  }>;
  dependents: Array<{
    id: number;
    node_key: string;
    node_type: string;
    file_path: string;
    edge_types: string[];
    confidence: string;
  }>;
}

export interface ImpactedComponent {
  id: number;
  node_id: number;
  node_key: string;
  node_type: string;
  name: string;
  file_path: string;
  start_line: number;
  end_line: number;
  is_test: boolean;
  impact_type: "direct" | "transitive";
  hop_distance: number;
  risk_score: number;
  risk_level: RiskLevel;
  risk_factors: {
    proximity_score: number;
    proximity_max: number;
    centrality_score: number;
    centrality_max: number;
    churn_score: number;
    churn_max: number;
    complexity_score: number;
    complexity_max: number;
    uncertainty_penalty: number;
    uncertainty_max: number;
    raw_score: number;
    test_dampening_factor: number;
    inputs: {
      hop_distance: number;
      fan_in: number;
      complexity: number;
      changed_lines: number;
      symbol_loc: number;
      is_test: boolean;
      has_heuristic_path: boolean;
    };
  };
  dependency_paths: string[][];
}

export interface AnalysisRunSummary {
  id: number;
  repo_id: number;
  base_commit: string;
  head_commit: string;
  overall_risk_score: number;
  risk_level: RiskLevel;
  summary_json: Record<string, any>;
  status: string;
  created_at: string;
}

export interface AnalysisRunDetail extends AnalysisRunSummary {
  impacted_components: ImpactedComponent[];
  has_ai_report: boolean;
}

export interface RecommendedTest {
  target_component: string;
  test_type: string;
  priority: string;
  rationale: string;
  suggested_scenario: string;
}

export interface AIReport {
  id: number;
  analysis_run_id: number;
  model_name: string;
  explanation_markdown: string;
  recommended_tests: RecommendedTest[];
  prompt_tokens: number;
  completion_tokens: number;
  created_at: string;
}
