"""FastAPI application entry point.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers.api import router as api_router

# ── Logging setup ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────────
app = FastAPI(
    title="AI Repository Analyzer",
    description=(
        "Analyze source code repositories (Python, JavaScript, TypeScript, "
        "Java, Kotlin, Go) and visualize architecture interactively. "
        "Features structured use-case extraction, code element explanation, "
        "and execution flow tracing powered by LLaMA 3."
    ),
    version="2.0.0",
)

# Allow all origins so the Android app can connect from any local IP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serve web frontend
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup():
    """Log startup info and pre-initialize tree-sitter if available."""
    logger.info("AI Repository Analyzer v2.0.0 starting up...")
    try:
        from services.generic_analyzer import _init_tree_sitter
        if _init_tree_sitter():
            logger.info("Multi-language analysis enabled (tree-sitter)")
        else:
            logger.warning("Multi-language analysis disabled (tree-sitter not installed)")
    except ImportError:
        logger.warning("Multi-language analysis disabled (tree-sitter not installed)")
    logger.info("Ready to accept requests")


@app.get("/")
async def root():
    """Serve the web frontend."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
