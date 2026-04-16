"""Repository ingestion — GitHub clone and ZIP extraction."""

import shutil
import uuid
import zipfile
from pathlib import Path

import git

from config import CLONE_DIR, UPLOAD_DIR


def clone_github_repo(url: str) -> tuple[str, Path]:
    """Clone a public GitHub repo (shallow) and return (analysis_id, path)."""
    analysis_id = uuid.uuid4().hex[:12]
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    dest = CLONE_DIR / f"{analysis_id}_{repo_name}"

    try:
        git.Repo.clone_from(url, str(dest), depth=1)
    except git.exc.GitCommandError as exc:
        raise RuntimeError(f"Clone failed: {exc}") from exc

    return analysis_id, dest


def extract_zip(zip_path: Path) -> tuple[str, Path]:
    """Extract an uploaded ZIP and return (analysis_id, path)."""
    analysis_id = uuid.uuid4().hex[:12]
    dest = UPLOAD_DIR / analysis_id

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"Bad ZIP: {exc}") from exc

    # If single top-level dir, use it as root
    children = list(dest.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return analysis_id, children[0]
    return analysis_id, dest


def cleanup(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
