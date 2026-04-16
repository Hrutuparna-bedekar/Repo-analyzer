"""Execution flow tracer — builds call-path chains from AST data.

Walks the function-call graph extracted by AST analysis to produce
execution flow paths from a given start point, with cycle detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from services.ast_analyzer import FileAnalysisResult, FunctionInfo

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────
MAX_TRACE_DEPTH = 10


@dataclass
class FlowStep:
    """A single step in an execution flow."""
    function_name: str
    file_path: str
    args: list[str] = field(default_factory=list)
    returns: str | None = None
    docstring: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "function_name": self.function_name,
            "file_path": self.file_path,
            "args": self.args,
            "returns": self.returns,
            "docstring": self.docstring,
        }


def _build_call_index(
    file_analyses: list[FileAnalysisResult],
) -> dict[str, tuple[FunctionInfo, str]]:
    """Build a lookup: function_name → (FunctionInfo, file_path).

    If there are duplicate names across files, the first occurrence wins.
    """
    index: dict[str, tuple[FunctionInfo, str]] = {}
    for fa in file_analyses:
        for func in fa.functions:
            key = func.name
            if key not in index:
                index[key] = (func, fa.path)
            # Also index as file::function for disambiguation
            qualified = f"{fa.path}::{func.name}"
            index[qualified] = (func, fa.path)
    return index


def trace_execution_flow(
    start_function: str,
    file_analyses: list[FileAnalysisResult],
    max_depth: int = MAX_TRACE_DEPTH,
    file_path: str | None = None,
) -> list[FlowStep]:
    """Trace the execution flow starting from a given function.

    Args:
        start_function: Name of the function to start tracing from.
        file_analyses: All file analysis results.
        max_depth: Maximum recursion depth.
        file_path: Optional file path to disambiguate the start function.

    Returns:
        Ordered list of FlowStep objects representing the call chain.
    """
    index = _build_call_index(file_analyses)

    # Resolve start point
    if file_path:
        key = f"{file_path}::{start_function}"
        if key in index:
            start_info, start_file = index[key]
        elif start_function in index:
            start_info, start_file = index[start_function]
        else:
            logger.warning("Start function '%s' not found in analysis", start_function)
            return []
    else:
        if start_function not in index:
            logger.warning("Start function '%s' not found in analysis", start_function)
            return []
        start_info, start_file = index[start_function]

    # Walk the call chain
    flow: list[FlowStep] = []
    visited: set[str] = set()

    def _trace(func_name: str, depth: int):
        if depth > max_depth:
            return
        if func_name in visited:
            return  # Cycle detected

        # Resolve function
        if func_name in index:
            func_info, fpath = index[func_name]
        else:
            # Try to find by simple name (strip module prefix)
            simple = func_name.split(".")[-1] if "." in func_name else func_name
            if simple in index:
                func_info, fpath = index[simple]
            else:
                return  # External call — not in our codebase

        visited.add(func_name)
        flow.append(FlowStep(
            function_name=func_info.name,
            file_path=fpath,
            args=func_info.args,
            returns=func_info.returns,
            docstring=func_info.docstring,
        ))

        # Follow calls
        for callee in func_info.calls:
            _trace(callee, depth + 1)

        visited.discard(func_name)  # Allow revisiting in different branches

    _trace(start_function, 0)
    return flow


def format_call_path(steps: list[FlowStep]) -> list[str]:
    """Format flow steps into human-readable call path strings.

    Returns list like: ["main (app.py)", "→ create_app (factory.py)", ...]
    """
    if not steps:
        return ["(no call path found)"]

    result = []
    for i, step in enumerate(steps):
        prefix = "→ " if i > 0 else ""
        args_str = f"({', '.join(step.args)})" if step.args else "()"
        result.append(f"{prefix}{step.function_name}{args_str}  [{step.file_path}]")
    return result
