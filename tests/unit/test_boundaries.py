import ast
from pathlib import Path


def test_dependency_direction():
    package = Path(__file__).resolve().parents[2] / "src" / "china_masters"
    for layer in ("domain", "application"):
        for file in (package / layer).rglob("*.py"):
            tree = ast.parse(file.read_text(encoding="utf-8"))
            modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules.append(node.module)
            forbidden = [
                "sqlalchemy",
                "fastapi",
                "pydantic",
                "pathlib",
                "os",
                "openai",
                "china_masters.infrastructure",
                "china_masters.interfaces",
                "china_masters.bootstrap",
                "china_masters.adapters",
            ]
            if layer == "domain":
                forbidden.append("china_masters.application")
            for module in modules:
                assert not any(
                    module == bad or module.startswith(bad + ".") for bad in forbidden
                ), (file, module)
