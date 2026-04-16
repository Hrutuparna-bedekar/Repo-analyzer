"""Filesystem and misc utility functions."""

from pathlib import Path
from config import SUPPORTED_EXTENSIONS


def walk_directory(root: Path) -> list[dict]:
    """Walk a directory tree and return metadata for each entry."""
    entries = []
    for item in sorted(root.rglob("*")):
        parts = item.relative_to(root).parts
        if any(p.startswith(".") or p == "__pycache__" or p == "node_modules" for p in parts):
            continue

        rel = str(item.relative_to(root)).replace("\\", "/")
        entry = {"path": rel, "name": item.name, "is_dir": item.is_dir()}
        if item.is_file():
            entry["size"] = item.stat().st_size
            entry["extension"] = item.suffix
        entries.append(entry)
    return entries


def is_supported(path: Path) -> bool:
    return path.suffix in SUPPORTED_EXTENSIONS


def detect_language(path: Path) -> str:
    return {
        ".py": "python",
        ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".java": "java",
        ".kt": "kotlin",
        ".go": "go",
    }.get(path.suffix, "unknown")


def safe_read(path: Path, max_bytes: int = 5 * 1024 * 1024) -> str | None:
    """Read file text; returns None if too large or binary."""
    if not path.is_file() or path.stat().st_size > max_bytes:
        return None
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
