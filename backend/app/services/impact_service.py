from collections import deque
from typing import Dict, List, Set, Tuple
import networkx as nx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import RepositoryNotFoundError
from app.core.security import SecurityGuard
from app.db.models import (
    AnalysisRun,
    CodeNode,
    ImpactedComponent,
    RepoFile,
    Repository,
)
from app.services.git_service import FileDiff, GitService
from app.services.graph_service import GraphService
from app.services.risk_engine import ComponentRiskInput, RiskEngine


class ImpactService:
    def __init__(self) -> None:
        self.guard = SecurityGuard(
            allowed_roots=settings.allowed_repo_roots,
            max_file_bytes=settings.max_source_file_bytes,
        )
        self.git = GitService()
        self.graph_service = GraphService()
        self.risk_engine = RiskEngine()

    def run_analysis(
        self,
        db: Session,
        repo_id: int,
        base_commit: str,
        head_commit: str,
        max_depth: int = 5,
    ) -> AnalysisRun:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise RepositoryNotFoundError(f"Repository {repo_id} not found.")

        repo_path = self.guard.validate_repo_path(repo.local_path)
        file_diffs = self.git.get_diff_hunks(repo_path, base_commit, head_commit)

        repo_files = db.query(RepoFile).filter(RepoFile.repo_id == repo_id).all()
        path_to_file = {f.file_path: f for f in repo_files}
        nodes = db.query(CodeNode).filter(CodeNode.repo_id == repo_id).all()
        node_by_id = {n.id: n for n in nodes}

        nodes_by_file_id: Dict[int, List[CodeNode]] = {}
        for n in nodes:
            nodes_by_file_id.setdefault(n.file_id, []).append(n)

        direct_changed_lines: Dict[int, int] = {}
        unindexed_changed_files: List[str] = []
        changed_python_files: List[str] = []

        for diff in file_diffs:
            target_path = diff.new_path or diff.old_path or ""
            if not target_path.endswith(".py"):
                continue

            changed_python_files.append(target_path)
            repo_file = path_to_file.get(diff.new_path or "") or path_to_file.get(diff.old_path or "")
            if not repo_file:
                unindexed_changed_files.append(target_path)
                continue

            file_nodes = nodes_by_file_id.get(repo_file.id, [])
            matched_ids = self._match_diff_to_nodes(diff, file_nodes)
            total_file_churn = max(1, diff.added_lines + diff.removed_lines)
            for nid in matched_ids:
                direct_changed_lines[nid] = direct_changed_lines.get(nid, 0) + total_file_churn

        impact_graph = self.graph_service.build_impact_propagation_graph(db, repo_id)
        hop_map: Dict[int, int] = {}
        parents_map: Dict[int, List[int]] = {}
        queue: deque[int] = deque()

        for nid in direct_changed_lines:
            if nid in impact_graph:
                hop_map[nid] = 0
                parents_map[nid] = []
                queue.append(nid)

        safe_max_depth = max(1, min(max_depth, 8))
        while queue:
            current = queue.popleft()
            current_hop = hop_map[current]
            if current_hop >= safe_max_depth:
                continue

            for neighbor in impact_graph.successors(current):
                next_hop = current_hop + 1
                if neighbor not in hop_map:
                    hop_map[neighbor] = next_hop
                    parents_map[neighbor] = [current]
                    queue.append(neighbor)
                elif hop_map[neighbor] == next_hop:
                    parents_map[neighbor].append(current)

        max_repo_fan_in = max((n.fan_in for n in nodes), default=1)
        impacted_records: List[ImpactedComponent] = []
        score_inputs_for_overall: List[Tuple[bool, float]] = []

        for nid, hop in sorted(hop_map.items(), key=lambda kv: (kv[1], kv[0])):
            node = node_by_id[nid]
            paths, has_heuristic = self._reconstruct_paths(
                nid, hop_map, parents_map, impact_graph, node_by_id
            )
            loc = max(1, node.end_line - node.start_line + 1)
            changed_lines = direct_changed_lines.get(nid, 0)

            risk_res = self.risk_engine.calculate_component_risk(
                ComponentRiskInput(
                    node_id=node.id,
                    node_key=node.node_key,
                    node_type=node.node_type,
                    is_test=node.is_test,
                    hop_distance=hop,
                    fan_in=node.fan_in,
                    complexity=node.complexity,
                    loc=loc,
                    changed_lines=changed_lines,
                    has_heuristic_path=has_heuristic,
                    max_repo_fan_in=max_repo_fan_in,
                )
            )
            score_inputs_for_overall.append((node.is_test, risk_res.risk_score))

            impacted_records.append(
                ImpactedComponent(
                    node_id=node.id,
                    impact_type="direct" if hop == 0 else "transitive",
                    hop_distance=hop,
                    risk_score=risk_res.risk_score,
                    risk_level=risk_res.risk_level,
                    risk_factors_json=risk_res.factors,
                    dependency_paths_json=paths,
                )
            )

        overall_score, overall_level, overall_breakdown = self.risk_engine.calculate_overall_risk(
            score_inputs_for_overall
        )

        direct_count = sum(1 for r in impacted_records if r.impact_type == "direct")
        transitive_count = sum(1 for r in impacted_records if r.impact_type == "transitive")

        run = AnalysisRun(
            repo_id=repo_id,
            base_commit=base_commit,
            head_commit=head_commit,
            overall_risk_score=overall_score,
            risk_level=overall_level,
            status="completed",
            summary_json={
                "changed_files_total": len(file_diffs),
                "changed_python_files": changed_python_files,
                "unindexed_changed_files": unindexed_changed_files,
                "direct_impact_count": direct_count,
                "transitive_impact_count": transitive_count,
                "total_impacted_count": len(impacted_records),
                "max_depth": safe_max_depth,
                "overall_formula_breakdown": overall_breakdown,
            },
        )
        db.add(run)
        db.flush()

        for rec in impacted_records:
            rec.analysis_run_id = run.id
            db.add(rec)

        db.commit()
        db.refresh(run)
        return run

    def _match_diff_to_nodes(
        self, diff: FileDiff, file_nodes: List[CodeNode]
    ) -> Set[int]:
        if not file_nodes:
            return set()

        module_nodes = [n for n in file_nodes if n.node_type == "module"]
        symbol_nodes = [n for n in file_nodes if n.node_type != "module"]

        if diff.change_type == "deleted":
            return {n.id for n in file_nodes}

        matched: Set[int] = set()
        for hunk in diff.hunks:
            h_start, h_end = hunk.new_line_range
            overlapping_symbols = [
                n for n in symbol_nodes
                if n.start_line <= h_end and n.end_line >= h_start
            ]
            if overlapping_symbols:
                leaf_symbols = [
                    n for n in overlapping_symbols
                    if not any(
                        other.id != n.id
                        and other.start_line >= n.start_line
                        and other.end_line <= n.end_line
                        for other in overlapping_symbols
                    )
                ]
                for sym in leaf_symbols:
                    matched.add(sym.id)
            else:
                for mod in module_nodes:
                    matched.add(mod.id)

        if not matched and diff.change_type == "added":
            for mod in module_nodes:
                matched.add(mod.id)

        return matched

    def _reconstruct_paths(
        self,
        target_id: int,
        hop_map: Dict[int, int],
        parents_map: Dict[int, List[int]],
        impact_graph: nx.DiGraph,
        node_by_id: Dict[int, CodeNode],
        max_paths: int = 3,
    ) -> Tuple[List[List[str]], bool]:
        if hop_map[target_id] == 0:
            return ([[node_by_id[target_id].node_key]], False)

        collected: List[List[str]] = []
        has_heuristic = False

        def backtrack(curr: int, trail: List[str]) -> None:
            nonlocal has_heuristic
            if len(collected) >= max_paths:
                return
            if hop_map[curr] == 0:
                collected.append(list(reversed(trail)))
                return
            for p in parents_map.get(curr, []):
                edge_data = impact_graph.get_edge_data(p, curr) or {}
                if edge_data.get("confidence") == "heuristic":
                    has_heuristic = True
                backtrack(p, trail + [node_by_id[p].node_key])

        backtrack(target_id, [node_by_id[target_id].node_key])
        return (collected, has_heuristic)
