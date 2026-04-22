"""NetworkX-based multi-level architecture graph builder.

Builds a directed graph with node types: repository, folder, file, class, function.
Edge types: contains, imports, inherits, calls, defines.
"""

from __future__ import annotations
from pathlib import Path

import networkx as nx

from models.graph_models import GraphNode, GraphEdge, NodeType, EdgeType
from services.ast_analyzer import FileAnalysisResult


def build_graph(
    repo_name: str,
    repo_path: Path,
    file_analyses: list[FileAnalysisResult],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Build a complete architecture graph from analysis results.

    Returns (nodes, edges) lists ready for serialization.
    """
    G = nx.DiGraph()
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    # ── 1. Repository root node ──────────────────────────────────
    repo_id = f"repo::{repo_name}"
    nodes[repo_id] = GraphNode(repo_id, NodeType.REPOSITORY, repo_name)
    G.add_node(repo_id)

    # ── 2. Folder + File nodes ───────────────────────────────────
    seen_folders: set[str] = set()

    for fa in file_analyses:
        parts = fa.path.split("/")

        # Create folder chain
        for i in range(len(parts) - 1):
            folder_path = "/".join(parts[: i + 1])
            folder_id = f"folder::{folder_path}"
            if folder_id not in seen_folders:
                seen_folders.add(folder_id)
                nodes[folder_id] = GraphNode(
                    folder_id, NodeType.FOLDER, parts[i]
                )
                G.add_node(folder_id)

                # Edge: parent → folder
                if i == 0:
                    parent_id = repo_id
                else:
                    parent_id = f"folder::{'/'.join(parts[:i])}"
                edge = GraphEdge(parent_id, folder_id, EdgeType.CONTAINS)
                edges.append(edge)
                G.add_edge(parent_id, folder_id)

        # File node
        file_id = f"file::{fa.path}"
        ext = fa.path.rsplit(".", 1)[-1] if "." in fa.path else "unknown"
        nodes[file_id] = GraphNode(
            file_id, NodeType.FILE, parts[-1],
            metadata={"line_count": fa.line_count, "path": fa.path, "language": ext},
        )
        G.add_node(file_id)

        # Edge: parent folder (or repo) → file
        if len(parts) > 1:
            parent_id = f"folder::{'/'.join(parts[:-1])}"
        else:
            parent_id = repo_id
        edges.append(GraphEdge(parent_id, file_id, EdgeType.CONTAINS))
        G.add_edge(parent_id, file_id)

        # ── 3. Class nodes ───────────────────────────────────────
        class_method_map = {}  # To keep track of which method belongs to which class
        for cls in fa.classes:
            cls_id = f"class::{fa.path}::{cls.name}"
            nodes[cls_id] = GraphNode(
                cls_id, NodeType.CLASS, cls.name,
                metadata={
                    "bases": cls.bases,
                    "methods": cls.methods,
                    "docstring": cls.docstring or "",
                    "lines": f"{cls.line_start}-{cls.line_end}",
                },
            )
            G.add_node(cls_id)
            
            for m_name in cls.methods:
                class_method_map[m_name] = cls_id

            # file → defines → class
            edges.append(GraphEdge(file_id, cls_id, EdgeType.DEFINES))
            G.add_edge(file_id, cls_id)

            # Inheritance edges
            for base in cls.bases:
                base_id = _find_class_id(base, file_analyses, fa.path)
                if base_id:
                    edges.append(GraphEdge(cls_id, base_id, EdgeType.INHERITS))
                    G.add_edge(cls_id, base_id)

        # ── 4. Function nodes ────────────────────────────────────
        for func in fa.functions:
            if func.is_method:
                parent_cls_id = class_method_map.get(func.name)
                # Make ID unique per class
                if parent_cls_id:
                    cls_name = parent_cls_id.split("::")[-1]
                    func_id = f"method::{fa.path}::{cls_name}::{func.name}"
                else:
                    func_id = f"method::{fa.path}::{func.name}"
                ntype = NodeType.METHOD
            else:
                func_id = f"function::{fa.path}::{func.name}"
                ntype = NodeType.FUNCTION

            nodes[func_id] = GraphNode(
                func_id, ntype, func.name,
                metadata={
                    "args": func.args,
                    "returns": func.returns or "",
                    "docstring": func.docstring or "",
                    "lines": f"{func.line_start}-{func.line_end}",
                    "calls": func.calls,
                },
            )
            G.add_node(func_id)

            # Define relationship
            if func.is_method and parent_cls_id:
                # class → defines → method
                edges.append(GraphEdge(parent_cls_id, func_id, EdgeType.DEFINES))
                G.add_edge(parent_cls_id, func_id)
            else:
                # file → defines → function
                edges.append(GraphEdge(file_id, func_id, EdgeType.DEFINES))
                G.add_edge(file_id, func_id)

    # ── 5. Import edges between files ────────────────────────────
    path_set = {fa.path for fa in file_analyses}
    for fa in file_analyses:
        file_id = f"file::{fa.path}"
        for imp in fa.imports:
            target = _resolve_import(imp, path_set)
            if target:
                target_id = f"file::{target}"
                edges.append(GraphEdge(file_id, target_id, EdgeType.IMPORTS))
                G.add_edge(file_id, target_id)

    # ── 6. Detect circular dependencies ──────────────────────────
    cycles = list(nx.simple_cycles(G))
    cycle_metadata = [c for c in cycles if len(c) > 1]

    return list(nodes.values()), edges


def _find_class_id(
    class_name: str,
    analyses: list[FileAnalysisResult],
    current_path: str,
) -> str | None:
    """Find the graph ID of a class by name across all files."""
    for fa in analyses:
        for cls in fa.classes:
            if cls.name == class_name and fa.path != current_path:
                return f"class::{fa.path}::{cls.name}"
    return None


def _resolve_import(import_name: str, file_paths: set[str]) -> str | None:
    """Try to match an import string to a file path in the repo."""
    # Convert dotted import to path: foo.bar.baz → foo/bar/baz.py
    candidate = import_name.replace(".", "/")
    if f"{candidate}.py" in file_paths:
        return f"{candidate}.py"
    if f"{candidate}/__init__.py" in file_paths:
        return f"{candidate}/__init__.py"
    # Try partial match (from foo.bar import thing → foo/bar.py)
    parts = candidate.rsplit("/", 1)
    if len(parts) == 2 and f"{parts[0]}.py" in file_paths:
        return f"{parts[0]}.py"
    return None


def graph_to_json(
    nodes: list[GraphNode], edges: list[GraphEdge]
) -> dict:
    """Serialize graph to JSON-ready dict."""
    return {
        "nodes": [n.to_dict() for n in nodes],
        "edges": [e.to_dict() for e in edges],
    }
