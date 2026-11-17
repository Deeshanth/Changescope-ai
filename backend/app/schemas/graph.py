from typing import Any, Dict, List
from pydantic import BaseModel


class GraphNodeDTO(BaseModel):
    id: int
    node_key: str
    node_type: str
    name: str
    file_path: str
    start_line: int
    end_line: int
    complexity: int
    fan_in: int
    fan_out: int
    is_test: bool


class GraphEdgeDTO(BaseModel):
    source: int
    target: int
    edge_type: str
    edge_types: List[str]
    confidence: str
    weight: int


class GraphViewResponse(BaseModel):
    level: str
    total_nodes_in_repo: int
    returned_nodes: int
    returned_edges: int
    nodes: List[GraphNodeDTO]
    edges: List[GraphEdgeDTO]


class RepoOverviewResponse(BaseModel):
    repository_id: int
    name: str
    last_indexed_commit: str | None
    total_files: int
    test_files: int
    total_loc: int
    total_nodes: int
    total_edges: int
    nodes_by_type: Dict[str, int]
    edges_by_type: Dict[str, int]
    parse_status_counts: Dict[str, int]
    top_fan_in_hotspots: List[Dict[str, Any]]
    top_complex_symbols: List[Dict[str, Any]]
