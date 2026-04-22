"""AI Explanation Engine powered by Groq (LLaMA 3).

Generates structured, natural-language explanations for repositories,
modules, files, classes, functions, and execution flows.

Output follows a strict structured format:
  A. Use-Case Extraction  → Actors / Use Cases / Relationships
  B. Code Element Explanation → Purpose / Role / Notes / Category
  C. Execution Flow → Step-by-step Flow Explanation
"""

from __future__ import annotations

import logging
import time
import json
import hashlib
from typing import Any
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, LLM_RETRY_COUNT
from services.ast_analyzer import FileAnalysisResult

logger = logging.getLogger(__name__)

# ── Caching setup ───────────────────────────────────────────────
from config import ANALYSIS_STORE
CACHE_DIR = ANALYSIS_STORE / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

def _get_cache_path(prompt: str) -> Path:
    """Generate a stable file path for a prompt's cache."""
    key = hashlib.md5(prompt.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.json"

# ── Groq client (lazy init) ─────────────────────────────────────
_client: Groq | None = None

SYSTEM_PROMPT = (
    "You are a senior software architect specialized in code analysis. "
    "You produce concise, structured explanations. Follow these constraints strictly:\n"
    "- Provide a very brief summary (max 6-7 lines total).\n"
    "- Do NOT repeat function signatures or raw input.\n"
    "- Do NOT hallucinate or invent missing logic.\n"
    "- If context is insufficient, state: 'Insufficient context'.\n"
    "- Use bullet points for clarity.\n"
    "- Prefer clarity over verbosity.\n"
    "- Output ONLY the requested format."
)


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY not set. Export it before starting the server.\n"
                "  Windows:  set GROQ_API_KEY=gsk_...\n"
                "  Linux:    export GROQ_API_KEY=gsk_..."
            )
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _ask(prompt: str, max_tokens: int = 1024) -> str:
    """Send a prompt to Groq with retry logic and return text response."""
    # 1. Check Cache
    cache_path = _get_cache_path(prompt)
    if cache_path.exists():
        try:
            logger.info("Cache hit for prompt (key=%s)", cache_path.stem)
            return json.loads(cache_path.read_text(encoding="utf-8"))["response"]
        except Exception as exc:
            logger.warning("Cache read failed: %s", exc)

    # 2. Call API with retries
    for attempt in range(LLM_RETRY_COUNT):
        try:
            resp = _get_client().chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            content = resp.choices[0].message.content.strip()
            
            # Save to Cache
            try:
                cache_path.write_text(json.dumps({"response": content}), encoding="utf-8")
                logger.info("Cache saved for prompt (key=%s)", cache_path.stem)
            except Exception as exc:
                logger.warning("Cache write failed: %s", exc)

            return content
        except Exception as exc:
            logger.warning("Groq API error (attempt %d/%d): %s", attempt + 1, LLM_RETRY_COUNT, exc)
            if attempt < LLM_RETRY_COUNT - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                return f"(AI explanation unavailable: {exc})"


# ═══════════════════════════════════════════════════════════════
# A. USE-CASE EXTRACTION
# ═══════════════════════════════════════════════════════════════

def explain_repository(
    repo_name: str,
    total_files: int,
    total_classes: int,
    total_functions: int,
    file_analyses: list[FileAnalysisResult],
) -> str:
    """Generate overall repo summary (backward-compatible free text)."""
    file_list = "\n".join(f"  - {fa.path} ({fa.line_count} lines)" for fa in file_analyses[:30])
    class_list = "\n".join(
        f"  - {cls.name} (in {fa.path})"
        for fa in file_analyses for cls in fa.classes
    )[:1500]

    # Detect languages present
    exts = {fa.path.rsplit(".", 1)[-1] for fa in file_analyses if "." in fa.path}
    languages = ", ".join(sorted(exts))

    prompt = f"""Analyze this repository and explain its purpose and architecture:

Repository: {repo_name}
Languages detected: {languages}
Files: {total_files} | Classes: {total_classes} | Functions: {total_functions}

File listing:
{file_list}

Classes found:
{class_list}

Provide a brief summary (max 7 lines):
1. What this project does (purpose)
2. High-level architecture overview
3. Key modules and their responsibilities
"""
    return _ask(prompt)


def extract_use_cases(
    repo_name: str,
    total_files: int,
    total_classes: int,
    total_functions: int,
    file_analyses: list[FileAnalysisResult],
) -> str:
    """Extract structured use cases from the repository.

    Returns structured text with Actors, Use Cases, and Relationships.
    """
    file_list = "\n".join(f"  - {fa.path} ({fa.line_count} lines)" for fa in file_analyses[:30])
    class_list = "\n".join(
        f"  - {cls.name} (in {fa.path})"
        for fa in file_analyses for cls in fa.classes
    )[:1500]

    func_list = "\n".join(
        f"  - {func.name} (in {fa.path})"
        for fa in file_analyses for func in fa.functions if not func.is_method
    )[:1500]

    # Detect languages
    exts = {fa.path.rsplit(".", 1)[-1] for fa in file_analyses if "." in fa.path}
    languages = ", ".join(sorted(exts))

    prompt = f"""Analyze this repository and extract structured use cases:

Repository: {repo_name}
Languages: {languages}
Files: {total_files} | Classes: {total_classes} | Functions: {total_functions}

File listing:
{file_list}

Classes:
{class_list}

Key functions:
{func_list}

Follow this EXACT output format:

Actors:
- [actor1]: [description]
- [actor2]: [description]

Use Cases:
1. [use case title]: [brief description]
2. [use case title]: [brief description]
... (identify 5-12 use cases)

Relationships:
- [actor] → [use case]
- [actor] → [use case]

Rules:
- Identify main actors (user, admin, external systems, APIs, etc.)
- Extract 5–12 high-level use cases
- Group related functionalities logically
- Define clear relationships between actors and use cases
"""
    return _ask(prompt, max_tokens=1200)


# ═══════════════════════════════════════════════════════════════
# B. CODE ELEMENT EXPLANATION
# ═══════════════════════════════════════════════════════════════

def explain_file(file_analysis: FileAnalysisResult) -> str:
    """Explain a single file with structured Code Element format."""
    classes = ", ".join(c.name for c in file_analysis.classes) or "none"
    functions = ", ".join(
        f.name for f in file_analysis.functions if not f.is_method
    ) or "none"
    imports = ", ".join(file_analysis.imports[:20]) or "none"

    # Detect language from path
    ext = file_analysis.path.rsplit(".", 1)[-1] if "." in file_analysis.path else "unknown"

    prompt = f"""Explain this source file using the structured format below:

Path: {file_analysis.path}
Language: {ext}
Lines: {file_analysis.line_count}
Module docstring: {file_analysis.module_docstring or 'none'}
Classes: {classes}
Top-level functions: {functions}
Imports: {imports}

Output EXACTLY in this format:
Purpose: [2-3 sentences on what this file does]
Role: [its role in the larger system]
Notes: [key dependencies, side effects, or important details]
Category: [exactly one of: Core Logic | Utility | API Layer | Data Handling | Configuration]
"""
    return _ask(prompt)


def explain_class(
    class_name: str,
    bases: list[str],
    methods: list[str],
    docstring: str,
    file_path: str,
) -> str:
    """Explain a class with structured Code Element format."""
    # Detect language
    ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "unknown"

    prompt = f"""Explain this class using the structured format below:

Class: {class_name}
File: {file_path}
Language: {ext}
Bases: {', '.join(bases) or 'none'}
Methods: {', '.join(methods) or 'none'}
Docstring: {docstring or 'none'}

Output EXACTLY in this format:
Purpose: [2-3 sentences on what this class represents]
Role: [its responsibility in the system]
Notes: [key dependencies, inheritance details, or side effects]
Category: [exactly one of: Core Logic | Utility | API Layer | Data Handling | Configuration]
"""
    return _ask(prompt, max_tokens=512)


def explain_function(
    func_name: str,
    args: list[str],
    returns: str | None,
    docstring: str | None,
    calls: list[str],
    file_path: str,
) -> str:
    """Explain a function with structured Code Element format."""
    ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "unknown"

    prompt = f"""Explain this function using the structured format below:

Function: {func_name}
File: {file_path}
Language: {ext}
Arguments: {', '.join(args) or 'none'}
Returns: {returns or 'unknown'}
Docstring: {docstring or 'none'}
Calls: {', '.join(calls[:15]) or 'none'}

Output EXACTLY in this format:
Purpose: [2-3 sentences on what this function does]
Role: [its role in the codebase]
Notes: [key dependencies, side effects, or edge cases]
Category: [exactly one of: Core Logic | Utility | API Layer | Data Handling | Configuration]
"""
    return _ask(prompt, max_tokens=512)


# ═══════════════════════════════════════════════════════════════
# C. EXECUTION FLOW EXPLANATION
# ═══════════════════════════════════════════════════════════════

def explain_execution_flow(
    start_function: str,
    call_path: list[str],
    file_path: str | None = None,
) -> str:
    """Generate a step-by-step execution flow explanation.

    Args:
        start_function: Name of the entry function.
        call_path: Ordered list of "func_name (file)" strings.
        file_path: Optional source file for context.
    """
    path_str = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(call_path))

    prompt = f"""Explain this execution flow step by step:

Start Point: {start_function}
{f'File: {file_path}' if file_path else ''}

Call Path:
{path_str}

Output EXACTLY in this format:
Flow Explanation:
1. [Step 1 description — what happens at this point and why]
2. [Step 2 description — transition to next component]
... (continue for each step)

Rules:
- Describe each step clearly
- Explain transitions between components
- Keep total explanation under 6-7 lines
"""
    return _ask(prompt, max_tokens=800)


# ═══════════════════════════════════════════════════════════════
# BATCH GENERATION (backward-compatible)
# ═══════════════════════════════════════════════════════════════

def generate_all_explanations(
    repo_name: str,
    file_analyses: list[FileAnalysisResult],
) -> dict[str, str]:
    """Generate explanations for the repo and every file in parallel."""
    explanations: dict[str, str] = {}

    total_files = len(file_analyses)
    total_classes = sum(len(fa.classes) for fa in file_analyses)
    total_functions = sum(len(fa.functions) for fa in file_analyses)

    # 1. High-priority repo-level and use-case summaries
    logger.info("Generating top-level summaries for '%s'...", repo_name)
    
    # We run these two sequentially at first to establish baseline context, 
    # but could parallelize them too if needed.
    explanations["__repo__"] = explain_repository(
        repo_name, total_files, total_classes, total_functions, file_analyses
    )
    explanations["__use_cases__"] = extract_use_cases(
        repo_name, total_files, total_classes, total_functions, file_analyses
    )

    # 2. File-level explanations in parallel (limit to 20 files)
    target_files = file_analyses[:20]
    num_parallel = min(len(target_files), 5)  # Cap at 5 concurrent requests for rate safety
    
    logger.info("Explaining %d files in parallel (workers=%d)...", len(target_files), num_parallel)
    
    with ThreadPoolExecutor(max_workers=num_parallel) as executor:
        # Map file paths to their analysis results
        future_to_path = {
            executor.submit(explain_file, fa): fa.path 
            for fa in target_files
        }
        
        for future in future_to_path:
            path = future_to_path[future]
            try:
                explanations[path] = future.result()
            except Exception as exc:
                logger.error("Failed to explain file '%s': %s", path, exc)
                explanations[path] = f"(Explanation failed: {exc})"

    return explanations
