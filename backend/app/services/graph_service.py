from collections import Counter
from typing import Any, Dict, Optional, Set
import networkx as nx
from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryNotFoundError
from app.db.models import CodeNode, DependencyEdge, RepoFile, Repository


class GraphService:
    """Builds and queries NetworkX directed graphs from indexed CodeNodes and DependencyEdges."""

    def _ensure_repo(self, db: Session, repo_id: int) -> Repository:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found.")
        return repo

    def build_dependency_graph(
        self,
        db: Session,
        repo_id: int,
        include_contains: bool = False,
    ) -> nx.DiGraph:
        self._ensure_repo(db, repo_id)

        nodes = db.query(CodeNode).filter(CodeNode.repo_id == repo_id).all()
        files = {
            f.id: f.file_path
            for f in db.query(RepoFile).filter(RepoFile.repo_id == repo_id).all()
        }

        graph = nx.DiGraph()
        for node in nodes:
            graph.add_node(
                node.id,
                node_key=node.node_key,
                node_type=node.node_type,
                name=node.name,
                qualified_name=node.qualified_name,
                file_path=files.get(node.file_id, ""),
                start_line=node.start_line,
                end_line=node.end_line,
                complexity=node.complexity,
                fan_in=node.fan_in,
                fan_out=node.fan_out,
                is_test=node.is_test,
            )

        edges = db.query(DependencyEdge).filter(DependencyEdge.repo_id == repo_id).all()
        for edge in edges:
            if not include_contains and edge.edge_type == "contains":
                continue
            if edge.source_node_id in graph and edge.target_node_id in graph:
                if graph.has_edge(edge.source_node_id, edge.target_node_id):
                    existing = graph[edge.source_node_id][edge.target_node_id]
                    existing["edge_types"].add(edge.edge_type)
                    existing["weight"] += 1
                    if edge.confidence == "exact":
                        existing["confidence"] = "exact"
                else:
                    graph.add_edge(
                        edge.source_node_id,
                        edge.target_node_id,
                        edge_types={edge.edge_type},
                        edge_type=edge.edge_type,
                        confidence=edge.confidence,
                        weight=1,
                    )

        return graph

    def build_impact_propagation_graph(self, db: Session, repo_id: int) -> nx.DiGraph:
        self._ensure_repo(db, repo_id)
        nodes = db.query(CodeNode).filter(CodeNode.repo_id == repo_id).all()
        edges = db.query(DependencyEdge).filter(DependencyEdge.repo_id == repo_id).all()

        impact_graph = nx.DiGraph()
        for node in nodes:
            impact_graph.add_node(node.id, node_key=node.node_key, is_test=node.is_test)

        for edge in edges:
            if edge.source_node_id not in impact_graph or edge.target_node_id not in impact_graph:
                continue

            if edge.edge_type == "contains":
                src, tgt = edge.target_node_id, edge.source_node_id
                propagation_kind = "contained_in"
            else:
                src, tgt = edge.target_node_id, edge.source_node_id
                propagation_kind = edge.edge_type

            if impact_graph.has_edge(src, tgt):
                existing = impact_graph[src][tgt]
                existing["edge_types"].add(propagation_kind)
                if edge.confidence == "exact":
                    existing["confidence"] = "exact"
            else:
                impact_graph.add_edge(
                    src,
                    tgt,
                    edge_types={propagation_kind},
                    confidence=edge.confidence,
                )

        return impact_graph

    def get_overview_metrics(self, db: Session, repo_id: int) -> Dict[str, Any]:
        repo = self._ensure_repo(db, repo_id)
        files = db.query(RepoFile).filter(RepoFile.repo_id == repo_id).all()
        nodes = db.query(CodeNode).filter(CodeNode.repo_id == repo_id).all()
        edges = db.query(DependencyEdge).filter(DependencyEdge.repo_id == repo_id).all()

        type_counts = Counter(n.node_type for n in nodes)
        edge_type_counts = Counter(e.edge_type for e in edges)
        parse_status_counts = Counter(f.parse_status for f in files)
        total_loc = sum(f.loc for f in files)
        test_files = sum(1 for f in files if f.is_test)

        file_map = {f.id: f.file_path for f in files}
        hotspots = sorted(
            (n for n in nodes if not n.is_test and n.fan_in > 0),
            key=lambda n: (n.fan_in, n.complexity),
            reverse=True,
        )[:10]

        most_complex = sorted(
            (n for n in nodes if n.node_type in {"function", "method"} and not n.is_test),
            key=lambda n: n.complexity,
            reverse=True,
        )[:10]

        return {
            "repository_id": repo.id,
            "name": repo.name,
            "last_indexed_commit": repo.last_indexed_commit,
            "total_files": len(files),
            "test_files": test_files,
            "total_loc": total_loc,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "nodes_by_type": dict(type_counts),
            "edges_by_type": dict(edge_type_counts),
            "parse_status_counts": dict(parse_status_counts),
            "top_fan_in_hotspots": [
                {
                    "id": n.id,
                    "node_key": n.node_key,
                    "node_type": n.node_type,
                    "file_path": file_map.get(n.file_id, ""),
                    "fan_in": n.fan_in,
                    "fan_out": n.fan_out,
                    "complexity": n.complexity,
                }
                for n in hotspots
            ],
            "top_complex_symbols": [
                {
                    "id": n.id,
                    "node_key": n.node_key,
                    "node_type": n.node_type,
                    "file_path": file_map.get(n.file_id, ""),
                    "complexity": n.complexity,
                    "fan_in": n.fan_in,
                }
                for n in most_complex
            ],
        }

    def get_graph_view(
        self,
        db: Session,
        repo_id: int,
        level: str = "symbol",
        node_type: Optional[str] = None,
        focus_node_id: Optional[int] = None,
        depth: int = 2,
        include_tests: bool = True,
        limit: int = 250,
    ) -> Dict[str, Any]:
        full_graph = self.build_dependency_graph(db, repo_id, include_contains=False)

        if level == "module":
            return self._build_module_graph_view(db, repo_id, full_graph, include_tests, limit)

        selected_ids: Set[int] = set()
        if focus_node_id is not None and focus_node_id in full_graph:
            undirected = full_graph.to_undirected(as_view=True)
            ego = nx.ego_graph(undirected, focus_node_id, radius=max(1, min(depth, 4)))
            selected_ids = set(ego.nodes())
        else:
            for nid, attrs in full_graph.nodes(data=True):
                if not include_tests and attrs.get("is_test"):
                    continue
                if node_type and attrs.get("node_type") != node_type:
                    continue
                selected_ids.add(nid)

        if len(selected_ids) > limit:
            ranked = sorted(
                selected_ids,
                key=lambda nid: (
                    full_graph.nodes[nid].get("fan_in", 0)
                    + full_graph.nodes[nid].get("fan_out", 0)
                ),
                reverse=True,
            )
            selected_ids = set(ranked[:limit])

        subgraph = full_graph.subgraph(selected_ids)
        nodes_out = [
            {
                "id": nid,
                "node_key": attrs["node_key"],
                "node_type": attrs["node_type"],
                "name": attrs["name"],
                "file_path": attrs["file_path"],
                "start_line": attrs["start_line"],
                "end_line": attrs["end_line"],
                "complexity": attrs["complexity"],
                "fan_in": attrs["fan_in"],
                "fan_out": attrs["fan_out"],
                "is_test": attrs["is_test"],
            }
            for nid, attrs in subgraph.nodes(data=True)
        ]

        edges_out = [
            {
                "source": u,
                "target": v,
                "edge_type": attrs["edge_type"],
                "edge_types": sorted(attrs["edge_types"]),
                "confidence": attrs["confidence"],
                "weight": attrs["weight"],
            }
            for u, v, attrs in subgraph.edges(data=True)
        ]

        return {
            "level": "symbol",
            "total_nodes_in_repo": full_graph.number_of_nodes(),
            "returned_nodes": len(nodes_out),
            "returned_edges": len(edges_out),
            "nodes": nodes_out,
            "edges": edges_out,
        }

    def _build_module_graph_view(
        self,
        db: Session,
        repo_id: int,
        symbol_graph: nx.DiGraph,
        include_tests: bool,
        limit: int,
    ) -> Dict[str, Any]:
        files = {
            f.id: f
            for f in db.query(RepoFile).filter(RepoFile.repo_id == repo_id).all()
        }
        nodes = db.query(CodeNode).filter(CodeNode.repo_id == repo_id).all()

        module_by_file: Dict[int, CodeNode] = {}
        node_to_module_id: Dict[int, int] = {}

        for n in nodes:
            if n.node_type == "module":
                module_by_file[n.file_id] = n

        for n in nodes:
            mod_node = module_by_file.get(n.file_id)
            if mod_node:
                node_to_module_id[n.id] = mod_node.id

        mod_graph = nx.DiGraph()
        for mod_node in module_by_file.values():
            if not include_tests and mod_node.is_test:
                continue
            f = files.get(mod_node.file_id)
            mod_graph.add_node(
                mod_node.id,
                node_key=mod_node.node_key,
                node_type="module",
                name=mod_node.name,
                file_path=f.file_path if f else "",
                start_line=1,
                end_line=f.loc if f else 1,
                complexity=mod_node.complexity,
                fan_in=0,
                fan_out=0,
                is_test=mod_node.is_test,
            )

        for u, v, attrs in symbol_graph.edges(data=True):
            mod_u = node_to_module_id.get(u)
            mod_v = node_to_module_id.get(v)
            if not mod_u or not mod_v or mod_u == mod_v:
                continue
            if mod_u not in mod_graph or mod_v not in mod_graph:
                continue
            if mod_graph.has_edge(mod_u, mod_v):
                mod_graph[mod_u][mod_v]["weight"] += attrs["weight"]
                mod_graph[mod_u][mod_v]["edge_types"].update(attrs["edge_types"])
            else:
                mod_graph.add_edge(
                    mod_u,
                    mod_v,
                    edge_type="depends_on",
                    edge_types=set(attrs["edge_types"]),
                    confidence=attrs["confidence"],
                    weight=attrs["weight"],
                )

        for nid in mod_graph.nodes():
            mod_graph.nodes[nid]["fan_in"] = mod_graph.in_degree(nid)
            mod_graph.nodes[nid]["fan_out"] = mod_graph.out_degree(nid)

        selected = list(mod_graph.nodes())[:limit]
        sub = mod_graph.subgraph(selected)

        return {
            "level": "module",
            "total_nodes_in_repo": len(module_by_file),
            "returned_nodes": sub.number_of_nodes(),
            "returned_edges": sub.number_of_edges(),
            "nodes": [{"id": nid, **attrs} for nid, attrs in sub.nodes(data=True)],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "edge_type": attrs["edge_type"],
                    "edge_types": sorted(attrs["edge_types"]),
                    "confidence": attrs["confidence"],
                    "weight": attrs["weight"],
                }
                for u, v, attrs in sub.edges(data=True)
            ],
        }

    def get_node_neighborhood(
        self, db: Session, repo_id: int, node_id: int
    ) -> Optional[Dict[str, Any]]:
        graph = self.build_dependency_graph(db, repo_id, include_contains=False)
        if node_id not in graph:
            return None

        node_attrs = graph.nodes[node_id]
        dependencies = [
            {
                "id": tgt,
                "node_key": graph.nodes[tgt]["node_key"],
                "node_type": graph.nodes[tgt]["node_type"],
                "file_path": graph.nodes[tgt]["file_path"],
                "edge_types": sorted(graph[node_id][tgt]["edge_types"]),
                "confidence": graph[node_id][tgt]["confidence"],
            }
            for tgt in graph.successors(node_id)
        ]
        dependents = [
            {
                "id": src,
                "node_key": graph.nodes[src]["node_key"],
                "node_type": graph.nodes[src]["node_type"],
                "file_path": graph.nodes[src]["file_path"],
                "edge_types": sorted(graph[src][node_id]["edge_types"]),
                "confidence": graph[src][node_id]["confidence"],
            }
            for src in graph.predecessors(node_id)
        ]

        return {
            "node": {"id": node_id, **node_attrs},
            "dependencies": dependencies,
            "dependents": dependents,
        }
