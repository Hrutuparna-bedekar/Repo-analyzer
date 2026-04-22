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


def _save_analysis(analysis_id: str, data: dict):
    """Persist analysis result to disk."""
    path = ANALYSIS_STORE / f"{analysis_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
    Uses caching to avoid redundant LLM calls.
    """
    data = _load_analysis(analysis_id)
    
    # Check cache first
    cache_key = f"__element__{req.file_path}__{req.name}"
    if cache_key in data.get("explanations", {}):
        raw = data["explanations"][cache_key]
        purpose, role, notes, category = _parse_code_element(raw)
        return CodeElementResponse(
            name=req.name,
            file_path=req.file_path,
            element_type="cached",
            purpose=purpose,
            role=role,
            notes=notes,
            category=category,
            raw_explanation=raw,
        )

    # Search for the element
    # Normalize requested path
    req_path = req.file_path.replace("\\", "/") if req.file_path else None
    
    # First pass: Search in the specified file (if provided)
    matches = []
    for f in data["files"]:
        f_path = f["path"].replace("\\", "/")
        
        # If file_path provided, check for match (exact or suffix)
        is_target_file = False
        if req_path:
            if f_path == req_path or f_path.endswith("/" + req_path) or req_path.endswith("/" + f_path):
                is_target_file = True
        
        # If no file_path provided or this is the target file, search it
        if not req_path or is_target_file:
            # Check classes (only if no type or type is class)
            if not req.element_type or req.element_type == "class":
                for cls in f.get("classes", []):
                    if cls["name"] == req.name:
                        matches.append(("class", cls, f["path"]))
            
            # Check functions/methods (only if no type or type is function/method)
            if not req.element_type or req.element_type in ["function", "method"]:
                for fn in f.get("functions", []):
                    if fn["name"] == req.name:
                        # If a specific type was requested, prioritize it
                        if req.element_type == "method" and fn.get("is_method"):
                            matches.insert(0, ("function", fn, f["path"]))
                        elif req.element_type == "function" and not fn.get("is_method"):
                            matches.insert(0, ("function", fn, f["path"]))
                        else:
                            matches.append(("function", fn, f["path"]))
        
        if is_target_file and matches:
            break

    # Second pass: If no match found in target file, search everywhere
    if not matches and req_path:
        for f in data["files"]:
            for cls in f.get("classes", []):
                if cls["name"] == req.name:
                    matches.append(("class", cls, f["path"]))
            for fn in f.get("functions", []):
                if fn["name"] == req.name:
                    matches.append(("function", fn, f["path"]))
            if matches:
                break

    if matches:
        etype, element, fpath = matches[0]
        if etype == "class":
            raw = explain_class(
                element["name"],
                element.get("bases", []),
                element.get("methods", []),
                element.get("docstring", ""),
                fpath,
            )
            purpose, role, notes, category = _parse_code_element(raw)
            
            # Save to cache
            if "explanations" not in data: data["explanations"] = {}
            data["explanations"][cache_key] = raw
            _save_analysis(analysis_id, data)

            return CodeElementResponse(
                name=element["name"],
                file_path=fpath,
                element_type="class",
                purpose=purpose,
                role=role,
                notes=notes,
                category=category,
                raw_explanation=raw,
            )
        else:
            raw = explain_function(
                element["name"],
                element.get("args", []),
                element.get("returns"),
                element.get("docstring"),
                element.get("calls", []),
                fpath,
            )
            purpose, role, notes, category = _parse_code_element(raw)

            # Save to cache
            if "explanations" not in data: data["explanations"] = {}
            data["explanations"][cache_key] = raw
            _save_analysis(analysis_id, data)

            return CodeElementResponse(
                name=element["name"],
                file_path=fpath,
                element_type="method" if element.get("is_method") else "function",
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
    """Parse the LLM's use-case output into actors, use_cases, relationships.
    Handles markdown headers, bolding, and various list styles.
    """
    actors = []
    use_cases = []
    relationships = []

    current_section = None
    lines = raw.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Clean line for section matching: remove ###, **, __
        clean_section = line.replace("#", "").replace("*", "").replace("_", "").strip().lower()
        
        if clean_section.startswith("actors") or "actors:" in clean_section:
            current_section = "actors"
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            if after: actors.append(after.lstrip("-*• "))
            continue
        elif clean_section.startswith("use cases") or "use cases:" in clean_section:
            current_section = "use_cases"
            continue
        elif clean_section.startswith("relationships") or "relationships:" in clean_section:
            current_section = "relationships"
            continue

        # Strip common list markers
        clean_content = line.lstrip("-•*#0123456789.) ").strip()
        if not clean_content:
            continue

        if current_section == "actors":
            actors.append(clean_content)
        elif current_section == "use_cases":
            use_cases.append(clean_content)
        elif current_section == "relationships":
            # Normalize arrows for relationships
            normalized_rel = clean_content.replace("->", "→").replace("=>", "→")
            relationships.append(normalized_rel)

    # Basic heuristic check: if nothing parsed but we have text, try one more time
    if not use_cases and len(lines) > 5:
        # Maybe it's just a raw list? 
        for line in lines:
            c = line.lstrip("-•*# ").strip()
            if c and len(c) > 10: use_cases.append(c)

    return actors, use_cases, relationships


def _parse_code_element(raw: str) -> tuple[str, str, str, str]:
    """Parse the LLM's code-element output into purpose, role, notes, category.
    Handles variations in formatting (bolding, case, etc.)
    """
    purpose = ""
    role = ""
    notes = ""
    category = "Core Logic"

    # If it's an error message, return it as purpose
    if raw.startswith("(AI explanation unavailable"):
        return raw, "N/A", "Please check your Groq API key or internet connection.", "Error"

    lines = raw.splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
        # Remove markdown bolding if present: **Purpose:** -> Purpose:
        clean_line = line.replace("**", "").replace("__", "").strip()
        lower = clean_line.lower()

        if lower.startswith("purpose:"):
            purpose = clean_line.split(":", 1)[1].strip()
        elif lower.startswith("role:"):
            role = clean_line.split(":", 1)[1].strip()
        elif lower.startswith("notes:"):
            notes = clean_line.split(":", 1)[1].strip()
        elif lower.startswith("category:"):
            category = clean_line.split(":", 1)[1].strip()
        
        # Fallback: if line is just "Purpose" and next line has content
        elif lower == "purpose" and i + 1 < len(lines):
            purpose = lines[i+1].strip().lstrip("-* ").strip()
        elif lower == "role" and i + 1 < len(lines):
            role = lines[i+1].strip().lstrip("-* ").strip()

    # Final fallback: if nothing parsed, use raw but stripped
    if not purpose and len(raw) > 10:
        purpose = raw.split("\n\n")[0].strip()

    return purpose, role, notes, category
