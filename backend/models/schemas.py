"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Any


# ── Requests ─────────────────────────────────────────────────────

class GitHubAnalyzeRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL")


# ── Responses ────────────────────────────────────────────────────

class NodeResponse(BaseModel):
    id: str
    type: str
    label: str
    metadata: dict[str, Any] = {}


class EdgeResponse(BaseModel):
    source: str
    target: str
    relationship: str
    metadata: dict[str, Any] = {}


class GraphResponse(BaseModel):
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]


class FileDetail(BaseModel):
    path: str
    language: str
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    imports: list[str] = []
    line_count: int = 0


class AnalysisSummaryResponse(BaseModel):
    id: str
    repo_name: str
    total_files: int
    total_classes: int
    total_functions: int
    status: str = "completed"


class FullAnalysisResponse(BaseModel):
    id: str
    repo_name: str
    total_files: int
    total_classes: int
    total_functions: int
    files: list[FileDetail]
    graph: GraphResponse
    explanations: dict[str, str]


class ExplanationResponse(BaseModel):
    path: str
    explanation: str


class ErrorResponse(BaseModel):
    detail: str


# ── Structured analysis responses ────────────────────────────────

class UseCaseResponse(BaseModel):
    actors: list[str] = []
    use_cases: list[str] = []
    relationships: list[str] = []
    raw_explanation: str = ""


class CodeElementRequest(BaseModel):
    name: str = Field(..., description="Name of the class or function to explain")
    file_path: str | None = Field(None, description="Optional file path to disambiguate")


class CodeElementResponse(BaseModel):
    name: str
    file_path: str
    element_type: str = ""  # class | function | method
    purpose: str = ""
    role: str = ""
    notes: str = ""
    category: str = ""  # Core Logic | Utility | API Layer | Data Handling | Configuration
    raw_explanation: str = ""


class ExecutionFlowRequest(BaseModel):
    start_function: str = Field(..., description="Name of the function to start tracing from")
    file_path: str | None = Field(None, description="Optional file path to disambiguate")


class ExecutionFlowResponse(BaseModel):
    start_point: str
    call_path: list[str] = []
    flow_explanation: str = ""
