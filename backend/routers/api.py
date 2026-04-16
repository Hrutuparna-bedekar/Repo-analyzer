"""FastAPI REST API router — all endpoints for the Android app.

Provides analysis, graph visualization, AI explanations,
structured use-case extraction, code element explanation,
and execution flow tracing.
"""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from config import ANALYSIS_STORE
from models.schemas import (
    GitHubAnalyzeRequest,
    FullAnalysisResponse,
    GraphResponse,
    NodeResponse,
    EdgeResponse,
    FileDetail,
    ExplanationResponse,
    AnalysisSummaryResponse,
    UseCaseResponse,
    CodeElementRequest,
    CodeElementResponse,
    ExecutionFlowRequest,
    ExecutionFlowResponse,
)
from services.repo_ingester import clone_github_repo, extract_zip, cleanup
from services.ast_analyzer import analyze_repository
from services.graph_builder import build_graph, graph_to_json
from services.ai_explainer import (
    generate_all_explanations, explain_file, explain_class,
    explain_function, explain_execution_flow,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


# ── Helpers ──────────────────────────────────────────────────────

def _run_analysis(analysis_id: str, repo_name: str, repo_path: Path) -> dict:
    """Run the full analysis pipeline and persist results."""
    # 1. AST analysis (multi-language)
    logger.info("Analyzing repository '%s' (id=%s)...", repo_name, analysis_id)
    file_analyses = analyze_repository(repo_path)
    logger.info("Found %d files across all languages", len(file_analyses))

    # Detect languages present
    exts = {fa.path.rsplit(".", 1)[-1] for fa in file_analyses if "." in fa.path}
    languages = sorted(exts)

    # 2. Build graph
    logger.info("Building architecture graph...")
    nodes, edges = build_graph(repo_name, repo_path, file_analyses)

    # 3. AI explanations (includes use-case extraction)
    try:
        logger.info("Generating AI explanations...")
        explanations = generate_all_explanations(repo_name, file_analyses)
    except Exception as exc:
        logger.error("AI explanation failed: %s", exc)
        explanations = {"__repo__": "(AI explanations unavailable — check GROQ_API_KEY)"}

    # 4. Assemble result
    result = {
        "id": analysis_id,
        "repo_name": repo_name,
        "languages": languages,
        "total_files": len(file_analyses),
        "total_classes": sum(len(fa.classes) for fa in file_analyses),
        "total_functions": sum(len(fa.functions) for fa in file_analyses),
        "files": [
            {
                "path": fa.path,
                "language": fa.path.rsplit(".", 1)[-1] if "." in fa.path else "unknown",
                "classes": [c.to_dict() for c in fa.classes],
                "functions": [f.to_dict() for f in fa.functions],
                "imports": fa.imports,
                "line_count": fa.line_count,
            }
            for fa in file_analyses
        ],
        "graph": graph_to_json(nodes, edges),
        "explanations": explanations,
    }

    # Persist to disk
    store_path = ANALYSIS_STORE / f"{analysis_id}.json"
    store_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info("Analysis saved: %s", store_path)

    return result


def _load_analysis(analysis_id: str) -> dict:
    """Load a persisted analysis result."""
    path = ANALYSIS_STORE / f"{analysis_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Analysis '{analysis_id}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS (backward-compatible)
# ═══════════════════════════════════════════════════════════════

@router.post("/analyze/github", response_model=AnalysisSummaryResponse)
async def analyze_github(req: GitHubAnalyzeRequest):
    """Clone a GitHub repository and analyze it."""
    try:
        analysis_id, repo_path = clone_github_repo(req.url)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))

    repo_name = req.url.rstrip("/").split("/")[-1].replace(".git", "")

    try:
        result = _run_analysis(analysis_id, repo_name, repo_path)
    finally:
        cleanup(repo_path)

    return AnalysisSummaryResponse(
        id=result["id"],
        repo_name=result["repo_name"],
        total_files=result["total_files"],
        total_classes=result["total_classes"],
        total_functions=result["total_functions"],
    )


@router.post("/analyze/upload", response_model=AnalysisSummaryResponse)
async def analyze_upload(file: UploadFile = File(...)):
    """Upload a ZIP file and analyze it."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(400, "Please upload a .zip file")

    tmp = Path(tempfile.mktemp(suffix=".zip"))
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(file.file, f)
        analysis_id, repo_path = extract_zip(tmp)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))
    finally:
        tmp.unlink(missing_ok=True)

    repo_name = file.filename.replace(".zip", "")

    try:
        result = _run_analysis(analysis_id, repo_name, repo_path)
    finally:
        cleanup(repo_path)

    return AnalysisSummaryResponse(
        id=result["id"],
        repo_name=result["repo_name"],
        total_files=result["total_files"],
        total_classes=result["total_classes"],
        total_functions=result["total_functions"],
    )


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Return full analysis results."""
    return _load_analysis(analysis_id)


@router.get("/analysis/{analysis_id}/graph")
async def get_graph(analysis_id: str):
    """Return only the architecture graph."""
    data = _load_analysis(analysis_id)
    return data["graph"]


@router.get("/analysis/{analysis_id}/files")
async def get_files(analysis_id: str):
    """Return the file listing."""
    data = _load_analysis(analysis_id)
    return data["files"]


@router.get("/analysis/{analysis_id}/file/{file_path:path}")
async def get_file_detail(analysis_id: str, file_path: str):
    """Return details for a specific file."""
    data = _load_analysis(analysis_id)
    for f in data["files"]:
        if f["path"] == file_path:
            return f
    raise HTTPException(404, f"File '{file_path}' not found in analysis")


@router.get("/analysis/{analysis_id}/explain/{path:path}")
async def get_explanation(analysis_id: str, path: str):
    """Return AI explanation for a file or module."""
    data = _load_analysis(analysis_id)
    explanation = data.get("explanations", {}).get(path)
    if explanation:
        return ExplanationResponse(path=path, explanation=explanation)

    # Generate on-demand if missing
    for f in data["files"]:
        if f["path"] == path:
            from services.ast_analyzer import FileAnalysisResult, ClassInfo, FunctionInfo

            classes = [ClassInfo(**c) for c in f.get("classes", [])]
            functions = [FunctionInfo(**fn) for fn in f.get("functions", [])]
            fa = FileAnalysisResult(
                path=f["path"],
                imports=f.get("imports", []),
                classes=classes,
                functions=functions,
                line_count=f.get("line_count", 0),
            )
            expl = explain_file(fa)
            return ExplanationResponse(path=path, explanation=expl)

    raise HTTPException(404, f"Path '{path}' not found")


@router.get("/analysis/{analysis_id}/explain-repo")
async def get_repo_explanation(analysis_id: str):
    """Return the repo-level AI explanation."""
    data = _load_analysis(analysis_id)
    expl = data.get("explanations", {}).get("__repo__", "No explanation available.")
    return ExplanationResponse(path="__repo__", explanation=expl)


# ═══════════════════════════════════════════════════════════════
# NEW ENDPOINTS — Structured Analysis
# ═══════════════════════════════════════════════════════════════

@router.get("/analysis/{analysis_id}/use-cases", response_model=UseCaseResponse)
async def get_use_cases(analysis_id: str):
    """Return structured use-case extraction (actors, use cases, relationships).

    Parses the pre-generated __use_cases__ explanation into structured fields.
    """
    data = _load_analysis(analysis_id)
    raw = data.get("explanations", {}).get("__use_cases__", "")

    if not raw:
        raise HTTPException(404, "Use-case analysis not available for this repository")

    # Parse the structured text into lists
    actors, use_cases, relationships = _parse_use_cases(raw)

    return UseCaseResponse(
        actors=actors,
        use_cases=use_cases,
        relationships=relationships,
        raw_explanation=raw,
    )


@router.post("/analysis/{analysis_id}/explain-element", response_model=CodeElementResponse)
async def explain_code_element(analysis_id: str, req: CodeElementRequest):
    """Explain a specific code element (class or function) with structured output.

    Searches for the element by name across all files and generates
    a structured explanation with Purpose, Role, Notes, and Category.
    """
    data = _load_analysis(analysis_id)

    # Search for the element
    for f in data["files"]:
        if req.file_path and f["path"] != req.file_path:
            continue

        # Check classes
        for cls in f.get("classes", []):
            if cls["name"] == req.name:
                raw = explain_class(
                    cls["name"],
                    cls.get("bases", []),
                    cls.get("methods", []),
                    cls.get("docstring", ""),
                    f["path"],
                )
                purpose, role, notes, category = _parse_code_element(raw)
                return CodeElementResponse(
                    name=cls["name"],
                    file_path=f["path"],
                    element_type="class",
                    purpose=purpose,
                    role=role,
                    notes=notes,
                    category=category,
                    raw_explanation=raw,
                )

        # Check functions
        for fn in f.get("functions", []):
            if fn["name"] == req.name:
                raw = explain_function(
                    fn["name"],
                    fn.get("args", []),
                    fn.get("returns"),
                    fn.get("docstring"),
                    fn.get("calls", []),
                    f["path"],
                )
                purpose, role, notes, category = _parse_code_element(raw)
                return CodeElementResponse(
                    name=fn["name"],
                    file_path=f["path"],
                    element_type="method" if fn.get("is_method") else "function",
                    purpose=purpose,
                    role=role,
                    notes=notes,
                    category=category,
                    raw_explanation=raw,
                )

    raise HTTPException(404, f"Element '{req.name}' not found in analysis")


@router.post("/analysis/{analysis_id}/execution-flow", response_model=ExecutionFlowResponse)
async def get_execution_flow(analysis_id: str, req: ExecutionFlowRequest):
    """Trace and explain the execution flow from a given start function.

    Uses the call graph from AST analysis to build the call path,
    then generates a step-by-step AI explanation.
    """
    data = _load_analysis(analysis_id)

    # Rebuild FileAnalysisResult objects for flow tracing
    from services.ast_analyzer import FileAnalysisResult, ClassInfo, FunctionInfo
    from services.flow_tracer import trace_execution_flow, format_call_path

    file_analyses = []
    for f in data["files"]:
        classes = [ClassInfo(**c) for c in f.get("classes", [])]
        functions = [FunctionInfo(**fn) for fn in f.get("functions", [])]
        fa = FileAnalysisResult(
            path=f["path"],
            imports=f.get("imports", []),
            classes=classes,
            functions=functions,
            line_count=f.get("line_count", 0),
        )
        file_analyses.append(fa)

    # Trace the flow
    steps = trace_execution_flow(
        req.start_function, file_analyses, file_path=req.file_path
    )

    if not steps:
        raise HTTPException(
            404,
            f"Function '{req.start_function}' not found or has no traceable calls"
        )

    call_path = format_call_path(steps)

    # Generate AI explanation
    flow_explanation = explain_execution_flow(
        req.start_function, call_path, req.file_path
    )

    return ExecutionFlowResponse(
        start_point=req.start_function,
        call_path=call_path,
        flow_explanation=flow_explanation,
    )


# ═══════════════════════════════════════════════════════════════
# Parsing helpers for structured LLM output
# ═══════════════════════════════════════════════════════════════

def _parse_use_cases(raw: str) -> tuple[list[str], list[str], list[str]]:
    """Parse the LLM's use-case output into actors, use_cases, relationships."""
    actors = []
    use_cases = []
    relationships = []

    current_section = None

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        lower = line.lower()
        if lower.startswith("actors:") or lower.startswith("actors"):
            current_section = "actors"
            # Check for inline content after the colon
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            if after and after != "":
                actors.append(after)
            continue
        elif lower.startswith("use cases:") or lower.startswith("use cases"):
            current_section = "use_cases"
            continue
        elif lower.startswith("relationships:") or lower.startswith("relationships"):
            current_section = "relationships"
            continue

        # Strip list markers
        clean = line.lstrip("-•*0123456789.) ").strip()
        if not clean:
            continue

        if current_section == "actors":
            actors.append(clean)
        elif current_section == "use_cases":
            use_cases.append(clean)
        elif current_section == "relationships":
            relationships.append(clean)

    return actors, use_cases, relationships


def _parse_code_element(raw: str) -> tuple[str, str, str, str]:
    """Parse the LLM's code-element output into purpose, role, notes, category."""
    purpose = ""
    role = ""
    notes = ""
    category = ""

    for line in raw.splitlines():
        line = line.strip()
        lower = line.lower()

        if lower.startswith("purpose:"):
            purpose = line.split(":", 1)[1].strip()
        elif lower.startswith("role:"):
            role = line.split(":", 1)[1].strip()
        elif lower.startswith("notes:"):
            notes = line.split(":", 1)[1].strip()
        elif lower.startswith("category:"):
            category = line.split(":", 1)[1].strip()

    return purpose, role, notes, category
