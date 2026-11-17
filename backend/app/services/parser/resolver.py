import builtins
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from app.services.parser.base import FileParseResult, ParsedImport, ParsedNode

_PYTHON_BUILTINS: Set[str] = set(dir(builtins))


@dataclass(frozen=True)
class ResolvedEdge:
    source_key: str
    target_key: str
    edge_type: str
    confidence: str
    line_number: Optional[int] = None


@dataclass
class ResolutionOutput:
    edges: List[ResolvedEdge] = field(default_factory=list)
    unresolved_references: List[tuple[str, str, int]] = field(default_factory=list)


class SymbolResolver:
    """Resolves AST imports, containment, inheritance, and call sites into graph edges."""

    def resolve(self, file_results: List[FileParseResult]) -> ResolutionOutput:
        node_map: Dict[str, ParsedNode] = {}
        name_index: Dict[str, List[ParsedNode]] = {}

        for result in file_results:
            for node in result.nodes:
                node_map[node.node_key] = node
                if node.node_type != "module":
                    name_index.setdefault(node.name, []).append(node)

        edges: List[ResolvedEdge] = []
        seen_edges: Set[tuple[str, str, str, Optional[int]]] = set()
        unresolved: List[tuple[str, str, int]] = []

        def add_edge(
            src: str,
            tgt: str,
            edge_type: str,
            confidence: str,
            line_number: Optional[int],
        ) -> None:
            if src == tgt:
                return
            key = (src, tgt, edge_type, line_number)
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append(
                    ResolvedEdge(
                        source_key=src,
                        target_key=tgt,
                        edge_type=edge_type,
                        confidence=confidence,
                        line_number=line_number,
                    )
                )

        for result in file_results:
            for node in result.nodes:
                if node.parent_key and node.parent_key in node_map:
                    add_edge(node.parent_key, node.node_key, "contains", "exact", node.start_line)

            alias_map: Dict[str, str] = {}
            for imp in result.imports:
                target_fqn = self._resolve_import_target(result, imp, node_map)
                if target_fqn:
                    alias_map[imp.alias] = target_fqn
                    if target_fqn in node_map:
                        add_edge(result.module_name, target_fqn, "imports", "exact", imp.line_number)
                elif not imp.is_from_import and "." in imp.imported_name:
                    if imp.imported_name in node_map:
                        alias_map[imp.imported_name] = imp.imported_name
                        add_edge(result.module_name, imp.imported_name, "imports", "exact", imp.line_number)

            for ref in result.references:
                resolved_target, confidence = self._resolve_reference(
                    source_key=ref.source_node_key,
                    expr=ref.target_expr,
                    module_name=result.module_name,
                    alias_map=alias_map,
                    node_map=node_map,
                    name_index=name_index,
                )
                if resolved_target:
                    add_edge(
                        ref.source_node_key,
                        resolved_target,
                        ref.edge_type,
                        confidence,
                        ref.line_number,
                    )
                else:
                    unresolved.append((ref.source_node_key, ref.target_expr, ref.line_number))

        return ResolutionOutput(edges=edges, unresolved_references=unresolved)

    def _resolve_import_target(
        self,
        file_result: FileParseResult,
        imp: ParsedImport,
        node_map: Dict[str, ParsedNode],
    ) -> Optional[str]:
        if not imp.is_from_import:
            if imp.imported_name in node_map:
                return imp.imported_name
            return None

        if imp.level > 0:
            is_pkg_init = file_result.file_path.endswith("__init__.py")
            mod_parts = file_result.module_name.split(".")
            if not is_pkg_init:
                mod_parts = mod_parts[:-1]
            climb = imp.level - 1
            if climb > len(mod_parts):
                return None
            base_parts = mod_parts[: len(mod_parts) - climb] if climb > 0 else mod_parts
            if imp.module_path:
                base_mod = ".".join([*base_parts, imp.module_path]) if base_parts else imp.module_path
            else:
                base_mod = ".".join(base_parts)
        else:
            base_mod = imp.module_path or ""

        if base_mod:
            candidate_symbol = f"{base_mod}.{imp.imported_name}"
            if candidate_symbol in node_map:
                return candidate_symbol
            if base_mod in node_map:
                return base_mod
        elif imp.imported_name in node_map:
            return imp.imported_name

        return None

    def _resolve_reference(
        self,
        source_key: str,
        expr: str,
        module_name: str,
        alias_map: Dict[str, str],
        node_map: Dict[str, ParsedNode],
        name_index: Dict[str, List[ParsedNode]],
    ) -> tuple[Optional[str], str]:
        if expr in _PYTHON_BUILTINS:
            return (None, "exact")

        if expr.startswith("self.") or expr.startswith("cls."):
            attr_path = expr.split(".", 1)[1]
            source_node = node_map.get(source_key)
            class_key = None
            if source_node and source_node.node_type == "method":
                class_key = source_node.parent_key
            elif source_node and source_node.node_type == "class":
                class_key = source_node.node_key

            if class_key:
                candidate = f"{class_key}.{attr_path}"
                if candidate in node_map:
                    return (candidate, "exact")

        local_candidate = f"{module_name}.{expr}"
        if local_candidate in node_map:
            return (local_candidate, "exact")

        if expr in alias_map and alias_map[expr] in node_map:
            return (alias_map[expr], "exact")

        parts = expr.split(".")
        for split_idx in range(len(parts), 0, -1):
            prefix = ".".join(parts[:split_idx])
            remainder = ".".join(parts[split_idx:])
            if prefix in alias_map:
                base_target = alias_map[prefix]
                candidate = f"{base_target}.{remainder}" if remainder else base_target
                if candidate in node_map:
                    return (candidate, "exact")

        leaf_name = parts[-1]
        if leaf_name in _PYTHON_BUILTINS:
            return (None, "exact")

        matches = name_index.get(leaf_name, [])
        if len(matches) == 1:
            return (matches[0].node_key, "heuristic")

        return (None, "exact")
