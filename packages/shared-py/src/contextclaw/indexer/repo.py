from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterator

from git import Repo as GitRepo


def clone_repo(clone_url: str, ref: str = "HEAD") -> str:
    """Clone a git repository to a temp dir and checkout *ref*.

    Returns the path to the cloned repo.
    """
    tmp = tempfile.mkdtemp(prefix="contextclaw_")
    git_repo = GitRepo.clone_from(clone_url, tmp, depth=1, branch=ref)
    git_repo.close()
    return tmp


def walk_files(repo_path: str) -> Iterator[str]:
    """Yield relative file paths from *repo_path* suitable for indexing."""
    _exclude = frozenset({
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        ".next", "dist", "build", ".turbo", "target",
        ".DS_Store", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    })
    _extensions = frozenset({
        ".py", ".ts", ".tsx", ".js", ".jsx",
        ".go", ".java", ".rs", ".rb", ".php",
        ".c", ".h", ".cpp", ".hpp", ".cs",
        ".swift", ".kt", ".scala", ".elixir", ".ex",
        ".md", ".mdx", ".rst", ".txt",
        ".yaml", ".yml", ".toml", ".json", ".tf",
        ".css", ".scss", ".html",
        ".sql",
    })

    for root, dirs, files in os.walk(repo_path):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in _exclude]

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in _extensions:
                continue
            rel = os.path.relpath(os.path.join(root, f), repo_path)
            yield rel


def read_file(repo_path: str, rel_path: str) -> str | None:
    """Read a file from the cloned repo, returning None on error."""
    full = os.path.join(repo_path, rel_path)
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return None


def cleanup(repo_path: str) -> None:
    """Remove a cloned repo from disk."""
    import shutil
    shutil.rmtree(repo_path, ignore_errors=True)
