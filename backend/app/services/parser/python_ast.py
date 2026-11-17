import ast
import hashlib
from pathlib import PurePosixPath
from typing import List, Optional

from app.services.parser.base import (
    BaseLanguageParser,
    FileParseResult,
    ParsedImport,
    ParsedNode,
    ParsedReference,
)


def file_path_to_module_name(file_path: str) -> str:
    posix = PurePosixPath(file_path.replace("\\", "/"))
    parts = list(posix.parts)
    if not parts:
        return "root"

    last = parts[-1]
    if last == "__init__.py":
        pkg_parts = parts[:-1]
        return ".".join(pkg_parts) if pkg_parts else "__init__"

    if last.endswith(".py"):
        parts[-1] = last[:-3]
    return ".".join(parts)


def is_test_path(file_path: str) -> bool:
    posix = PurePosixPath(file_path.replace("\\", "/"))
    lower_parts = [p.lower() for p in posix.parts]
    filename = lower_parts[-1] if lower_parts else ""
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return True
    return any(part in {"tests", "test"} for part in lower_parts[:-1])


def _extract_expr_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _extract_expr_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _extract_expr_name(node.func)
    return None


def _compute_scope_complexity(root_node: ast.AST) -> int:
    """Computes cyclomatic complexity within the current node without double-counting nested defs."""
    complexity = 1
    stack = list(ast.iter_child_nodes(root_node))
    branch_types = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.ExceptHandler,
        ast.With,
        ast.AsyncWith,
        ast.IfExp,
        ast.comprehension,
    )

    while stack:
        current = stack.pop()
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(current, branch_types):
            complexity += 1
        elif isinstance(current, ast.BoolOp):
            complexity += max(0, len(current.values) - 1)
        stack.extend(ast.iter_child_nodes(current))

    return complexity


class _PythonASTVisitor(ast.NodeVisitor):
    def __init__(self, module_name: str, is_test: bool, total_lines: int) -> None:
        self.module_name = module_name
        self.is_test = is_test
        self.nodes: List[ParsedNode] = [
            ParsedNode(
                node_key=module_name,
                node_type="module",
                name=module_name.split(".")[-1],
                qualified_name=module_name,
                start_line=1,
                end_line=max(1, total_lines),
                complexity=1,
                is_test=is_test,
                parent_key=None,
            )
        ]
        self.imports: List[ParsedImport] = []
        self.references: List[ParsedReference] = []
        self._scope_stack: List[tuple[str, str]] = [("module", module_name)]

    @property
    def _current_scope_type(self) -> str:
        return self._scope_stack[-1][0]

    @property
    def _current_scope_key(self) -> str:
        return self._scope_stack[-1][1]

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            bound_name = alias.asname if alias.asname else alias.name.split(".")[0]
            self.imports.append(
                ParsedImport(
                    module_path=None,
                    imported_name=alias.name,
                    alias=bound_name,
                    level=0,
                    line_number=node.lineno,
                    is_from_import=False,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            bound_name = alias.asname if alias.asname else alias.name
            self.imports.append(
                ParsedImport(
                    module_path=node.module,
                    imported_name=alias.name,
                    alias=bound_name,
                    level=node.level,
                    line_number=node.lineno,
                    is_from_import=True,
                )
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        parent_key = self._current_scope_key
        class_key = f"{parent_key}.{node.name}"
        bases: List[str] = []

        for base in node.bases:
            base_name = _extract_expr_name(base)
            if base_name:
                bases.append(base_name)
                self.references.append(
                    ParsedReference(
                        source_node_key=class_key,
                        target_expr=base_name,
                        edge_type="inherits",
                        line_number=node.lineno,
                    )
                )

        self.nodes.append(
            ParsedNode(
                node_key=class_key,
                node_type="class",
                name=node.name,
                qualified_name=class_key,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                complexity=_compute_scope_complexity(node),
                is_test=self.is_test,
                parent_key=parent_key,
                bases=bases,
            )
        )

        self._scope_stack.append(("class", class_key))
        self.generic_visit(node)
        self._scope_stack.pop()

    def _visit_function_like(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        parent_type = self._current_scope_type
        parent_key = self._current_scope_key
        node_type = "method" if parent_type == "class" else "function"
        fn_key = f"{parent_key}.{node.name}"

        self.nodes.append(
            ParsedNode(
                node_key=fn_key,
                node_type=node_type,
                name=node.name,
                qualified_name=fn_key,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                complexity=_compute_scope_complexity(node),
                is_test=self.is_test or node.name.startswith("test_"),
                parent_key=parent_key,
            )
        )

        self._scope_stack.append((node_type, fn_key))
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_like(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_like(node)

    def visit_Call(self, node: ast.Call) -> None:
        target_expr = _extract_expr_name(node.func)
        if target_expr:
            self.references.append(
                ParsedReference(
                    source_node_key=self._current_scope_key,
                    target_expr=target_expr,
                    edge_type="calls",
                    line_number=node.lineno,
                )
            )
        self.generic_visit(node)


class PythonASTParser(BaseLanguageParser):
    language = "python"

    def parse_file(self, file_path: str, source: str) -> FileParseResult:
        normalized_path = file_path.replace("\\", "/")
        module_name = file_path_to_module_name(normalized_path)
        file_hash = hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()
        lines = source.splitlines()
        loc = len(lines)
        test_flag = is_test_path(normalized_path)

        try:
            tree = ast.parse(source, filename=normalized_path)
        except SyntaxError as exc:
            error_msg = f"Line {exc.lineno or '?'}: {exc.msg}"
            return FileParseResult(
                file_path=normalized_path,
                module_name=module_name,
                language=self.language,
                file_hash=file_hash,
                loc=loc,
                is_test=test_flag,
                parse_status="syntax_error",
                parse_error=error_msg,
                nodes=[
                    ParsedNode(
                        node_key=module_name,
                        node_type="module",
                        name=module_name.split(".")[-1],
                        qualified_name=module_name,
                        start_line=1,
                        end_line=max(1, loc),
                        complexity=1,
                        is_test=test_flag,
                    )
                ],
            )

        visitor = _PythonASTVisitor(
            module_name=module_name,
            is_test=test_flag,
            total_lines=loc,
        )
        visitor.visit(tree)

        return FileParseResult(
            file_path=normalized_path,
            module_name=module_name,
            language=self.language,
            file_hash=file_hash,
            loc=loc,
            is_test=test_flag,
            parse_status="ok",
            nodes=visitor.nodes,
            imports=visitor.imports,
            references=visitor.references,
        )
