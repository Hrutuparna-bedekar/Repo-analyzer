"""Graph data models — nodes, edges, and analysis results."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    REPOSITORY = "repository"
    FOLDER = "folder"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class EdgeType(str, Enum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    INHERITS = "inherits"
    CALLS = "calls"
    DEFINES = "defines"


@dataclass
class GraphNode:
    id: str
    type: NodeType
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type.value,
                "label": self.label, "metadata": self.metadata}


@dataclass
class GraphEdge:
    source: str
    target: str
    relationship: EdgeType
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target,
                "relationship": self.relationship.value,
                "metadata": self.metadata}


@dataclass
class FileAnalysis:
    path: str
    language: str = "python"
    classes: list[dict[str, Any]] = field(default_factory=list)
    functions: list[dict[str, Any]] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    line_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AnalysisResult:
    id: str
    repo_name: str
    total_files: int = 0
    total_classes: int = 0
    total_functions: int = 0
    files: list[FileAnalysis] = field(default_factory=list)
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    explanations: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo_name": self.repo_name,
            "total_files": self.total_files,
            "total_classes": self.total_classes,
            "total_functions": self.total_functions,
            "files": [f.to_dict() for f in self.files],
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "explanations": self.explanations,
        }
