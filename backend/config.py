"""Application configuration — reads GROQ_API_KEY from environment."""

import os
from pathlib import Path

# ── Directories ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
CLONE_DIR = BASE_DIR / "cloned_repos"
ANALYSIS_STORE = BASE_DIR / "analyses"

for _d in (UPLOAD_DIR, CLONE_DIR, ANALYSIS_STORE):
    _d.mkdir(exist_ok=True)

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# ── Groq ─────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Analysis limits ──────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".py",                          # Python
    ".js", ".jsx", ".ts", ".tsx",   # JavaScript / TypeScript
    ".java",                        # Java
    ".kt",                          # Kotlin
    ".go",                          # Go
}
MAX_FILE_SIZE = 5 * 1024 * 1024       # 5 MB per file
MAX_UPLOAD_SIZE = 50 * 1024 * 1024    # 50 MB ZIP

# ── Execution flow ───────────────────────────────────────────────
MAX_TRACE_DEPTH = 10

# ── LLM settings ────────────────────────────────────────────────
LLM_RETRY_COUNT = 3
LLM_TIMEOUT = 30  # seconds
