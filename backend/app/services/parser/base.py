from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedNode:
    node_key: str
    node_type: str
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    complexity: int = 1
    is_test: bool = False
    parent_key: Optional[str] = None
    bases: List[str] = field(default_factory=list)


@dataclass
class ParsedImport:
    module_path: Optional[str]
    imported_name: str
    alias: str
    level: int = 0
    line_number: int = 1
    is_from_import: bool = False


@dataclass
class ParsedReference:
    source_node_key: str
    target_expr: str
    edge_type: str
    line_number: int


@dataclass
class FileParseResult:
    file_path: str
    module_name: str
    language: str
    file_hash: str
    loc: int
    is_test: bool
    parse_status: str
    parse_error: Optional[str] = None
    nodes: List[ParsedNode] = field(default_factory=list)
    imports: List[ParsedImport] = field(default_factory=list)
    references: List[ParsedReference] = field(default_factory=list)


class BaseLanguageParser(ABC):
    language: str = "unknown"

    @abstractmethod
    def parse_file(self, file_path: str, source: str) -> FileParseResult:
        """Parse source text into normalized nodes, imports, and references."""
