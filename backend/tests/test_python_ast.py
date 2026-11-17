from app.services.parser.python_ast import PythonASTParser
from app.services.parser.resolver import SymbolResolver


def test_ast_parser_extracts_symbols_and_complexity() -> None:
    parser = PythonASTParser()
    source = """
class Calculator:
    def compute(self, x: int) -> int:
        if x > 0:
            return x
        return 0
"""
    result = parser.parse_file("pkg/calc.py", source)
    assert result.parse_status == "ok"
    keys = {n.node_key: n for n in result.nodes}
    assert "pkg.calc" in keys
    assert "pkg.calc.Calculator" in keys
    assert "pkg.calc.Calculator.compute" in keys
    assert keys["pkg.calc.Calculator.compute"].complexity == 2


def test_ast_parser_handles_syntax_error_gracefully() -> None:
    parser = PythonASTParser()
    result = parser.parse_file("broken.py", "def bad(:\n    pass\n")
    assert result.parse_status == "syntax_error"
    assert result.parse_error is not None
    assert len(result.nodes) == 1


def test_symbol_resolver_cross_module_and_self_calls() -> None:
    parser = PythonASTParser()
    mod_a = parser.parse_file(
        "app/service.py",
        "from app.repo import save_user\n\nclass UserService:\n    def helper(self):\n        pass\n    def create(self):\n        self.helper()\n        save_user()\n",
    )
    mod_b = parser.parse_file(
        "app/repo.py",
        "def save_user():\n    return True\n",
    )

    output = SymbolResolver().resolve([mod_a, mod_b])
    triples = {(e.source_key, e.target_key, e.edge_type, e.confidence) for e in output.edges}

    assert ("app.service", "app.repo.save_user", "imports", "exact") in triples
    assert ("app.service.UserService.create", "app.service.UserService.helper", "calls", "exact") in triples
    assert ("app.service.UserService.create", "app.repo.save_user", "calls", "exact") in triples
