"""Repository-level checks for documentation, typing, and function logging."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_PATHS = [
    *sorted((PROJECT_ROOT / "src" / "supergene").glob("*.py")),
    *sorted((PROJECT_ROOT / "scripts").glob("*.py")),
]
LOGGER_EXEMPTIONS = {
    (Path("scripts/upload_chapters_to_vector.py"), "log_to_err_console"),
}


def test_python_modules_have_google_docstrings_type_hints_and_function_logging() -> None:
    """Require production Python modules to document, type, and trace functions."""
    failures: list[str] = []
    for path in PYTHON_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(PROJECT_ROOT)
        if not ast.get_docstring(tree):
            failures.append(f"{relative_path}: missing module docstring")

        imports_logger = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "loguru"
            and any(alias.name == "logger" for alias in node.names)
            for node in tree.body
        )
        if not imports_logger:
            failures.append(f"{relative_path}: missing 'from loguru import logger'")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and not ast.get_docstring(node):
                failures.append(f"{relative_path}:{node.lineno}: class {node.name} missing docstring")
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name == "update" and path.name == "__main__.py":
                    continue
                if not ast.get_docstring(node):
                    failures.append(f"{relative_path}:{node.lineno}: function {node.name} missing docstring")
                if not _has_complete_annotations(node):
                    failures.append(f"{relative_path}:{node.lineno}: function {node.name} missing type hints")
                if (relative_path, node.name) not in LOGGER_EXEMPTIONS and not _contains_logger_call(node):
                    failures.append(f"{relative_path}:{node.lineno}: function {node.name} missing logger call")

    assert failures == []


def _has_complete_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether all function parameters and the return value are annotated."""
    positional_arguments = [
        *node.args.posonlyargs,
        *node.args.args,
    ]
    if positional_arguments and positional_arguments[0].arg in {"self", "cls"}:
        positional_arguments = positional_arguments[1:]
    arguments = [
        *positional_arguments,
        *node.args.kwonlyargs,
    ]
    if node.args.vararg:
        arguments.append(node.args.vararg)
    if node.args.kwarg:
        arguments.append(node.args.kwarg)
    return all(argument.annotation is not None for argument in arguments) and node.returns is not None


def _contains_logger_call(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a function body calls the shared Loguru logger."""
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and isinstance(child.func.value, ast.Name)
        and child.func.value.id == "logger"
        for child in ast.walk(node)
    )
