"""AST-based Python source code analyzer.

Extracts classes, functions, methods, imports, inheritance, decorators,
and function-call relationships from Python files.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from utils.helpers import safe_read


# ── Extracted info containers ────────────────────────────────────

@dataclass
class ClassInfo:
    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    docstring: str | None = None
    line_start: int = 0
    line_end: int = 0
    decorators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "bases": self.bases,
            "methods": self.methods, "docstring": self.docstring,
            "line_start": self.line_start, "line_end": self.line_end,
            "decorators": self.decorators,
        }


@dataclass
class FunctionInfo:
    name: str
    args: list[str] = field(default_factory=list)
    returns: str | None = None
    docstring: str | None = None
    calls: list[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    decorators: list[str] = field(default_factory=list)
    is_method: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "args": self.args,
            "returns": self.returns, "docstring": self.docstring,
            "calls": self.calls, "line_start": self.line_start,
            "line_end": self.line_end, "decorators": self.decorators,
            "is_method": self.is_method,
        }


@dataclass
class FileAnalysisResult:
    path: str
    imports: list[str] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    line_count: int = 0
    module_docstring: str | None = None


# ── AST Visitor ──────────────────────────────────────────────────

class _CodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: list[str] = []
        self.classes: list[ClassInfo] = []
        self.functions: list[FunctionInfo] = []
        self._in_class: ClassInfo | None = None

    # Imports
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            self.imports.append(f"{mod}.{alias.name}" if mod else alias.name)
        self.generic_visit(node)

    # Classes
    def visit_ClassDef(self, node: ast.ClassDef):
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(ast.unparse(b))

        cls = ClassInfo(
            name=node.name, bases=bases,
            docstring=ast.get_docstring(node),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=[ast.unparse(d) for d in node.decorator_list],
        )

        prev = self._in_class
        self._in_class = cls
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cls.methods.append(item.name)
                self._process_func(item, is_method=True)
        self._in_class = prev
        self.classes.append(cls)

    # Top-level functions
    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self._in_class is None:
            self._process_func(node, is_method=False)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _process_func(self, node, is_method: bool):
        args = [a.arg for a in node.args.args if a.arg != "self"]
        returns = ast.unparse(node.returns) if node.returns else None

        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = self._call_name(child)
                if name:
                    calls.append(name)

        self.functions.append(FunctionInfo(
            name=node.name, args=args, returns=returns,
            docstring=ast.get_docstring(node),
            calls=calls,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            decorators=[ast.unparse(d) for d in node.decorator_list],
            is_method=is_method,
        ))

    @staticmethod
    def _call_name(node: ast.Call) -> str | None:
        f = node.func
        if isinstance(f, ast.Name):
            return f.id
        if isinstance(f, ast.Attribute):
            return ast.unparse(f)
        return None


# ── Public API ───────────────────────────────────────────────────

def analyze_file(file_path: Path, repo_root: Path) -> FileAnalysisResult | None:
    """Analyze a single Python file."""
    source = safe_read(file_path)
    if source is None:
        return None
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return None

    v = _CodeVisitor()
    v.visit(tree)

    return FileAnalysisResult(
        path=str(file_path.relative_to(repo_root)).replace("\\", "/"),
        imports=v.imports,
        classes=v.classes,
        functions=v.functions,
        line_count=source.count("\n") + 1,
        module_docstring=ast.get_docstring(tree),
    )


def analyze_repository(repo_path: Path) -> list[FileAnalysisResult]:
    """Analyze all supported source files in a repository.

    Python files use the built-in AST parser.
    JS/TS/Java/Kotlin/Go files use tree-sitter via generic_analyzer.
    """
    from config import SUPPORTED_EXTENSIONS

    # Lazy import to avoid circular dependency and allow graceful fallback
    try:
        from services.generic_analyzer import analyze_file_generic
        has_generic = True
    except ImportError:
        has_generic = False

    SKIP_DIRS = {"__pycache__", "node_modules", ".git", "venv", ".venv",
                 "env", ".env", "build", "dist", ".idea", ".gradle"}

    results = []
    for src_file in sorted(repo_path.rglob("*")):
        if not src_file.is_file():
            continue
        if src_file.suffix not in SUPPORTED_EXTENSIONS:
            continue

        parts = src_file.relative_to(repo_path).parts
        if any(p.startswith(".") or p in SKIP_DIRS for p in parts):
            continue

        # Dispatch: Python → AST, others → tree-sitter
        if src_file.suffix == ".py":
            r = analyze_file(src_file, repo_path)
        elif has_generic:
            r = analyze_file_generic(src_file, repo_path)
        else:
            continue

        if r:
            results.append(r)

    return results
