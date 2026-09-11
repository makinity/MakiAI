"""
MakiAI — KB Reader
Reads .md files from C:\\Knowledge-Base\\ for use in Gemini context
and skill execution with an in-memory warm RAM cache for near-instant access.

All paths are relative to KB_PATH from .env.
"""

import time
from pathlib import Path


class KBReader:
    """
    Reads Markdown files from the Knowledge Base.
    Uses an in-memory warm RAM cache with file timestamp validation
    to ensure 0ms retrieval with zero stale data.
    """

    def __init__(self, kb_path: str):
        """
        Args:
            kb_path: Absolute path to the Knowledge Base root.
        """
        self.kb_path = Path(kb_path)
        # Cache mapping: normalized_relative_path -> (mtime, content)
        self._cache: dict[str, tuple[float, str]] = {}
        # Cached list of files -> (timestamp, [paths])
        self._files_cache: dict[tuple[str, str], tuple[float, list[str]]] = {}
        self.warm_cache()

    # ─── Warm Cache ──────────────────────────────────────────────────────────

    def warm_cache(self) -> None:
        """Pre-load all Markdown files into memory for instant access."""
        if not self.kb_path.exists():
            return
        t0 = time.perf_counter()
        count = 0
        try:
            for file_path in self.list_files("", "*.md"):
                self.read(file_path)
                count += 1
            dt = (time.perf_counter() - t0) * 1000
            print(f"[KBReader] Warmed {count} files in RAM ({dt:.1f}ms).")
        except Exception as e:
            print(f"[KBReader] Warm cache warning: {e}")

    def invalidate_cache(self, relative_path: str = "") -> None:
        """Clear cache for a specific file or all files."""
        if relative_path:
            norm = relative_path.replace("\\", "/")
            self._cache.pop(norm, None)
            self._cache.pop(relative_path.replace("/", "\\"), None)
        else:
            self._cache.clear()
            self._files_cache.clear()

    # ─── Public API ──────────────────────────────────────────────────────────

    def read(self, relative_path: str) -> str:
        """
        Read a single KB file and return its content from RAM cache.
        Checks mtime so modifications on disk are automatically picked up.
        """
        norm_key = relative_path.replace("\\", "/")
        full_path = self.kb_path / relative_path

        try:
            if not full_path.exists():
                return ""

            mtime = full_path.stat().st_mtime
            cached = self._cache.get(norm_key)
            if cached and cached[0] == mtime:
                return cached[1]

            content = full_path.read_text(encoding="utf-8")
            self._cache[norm_key] = (mtime, content)
            return content
        except Exception as e:
            print(f"[KBReader] Error reading {relative_path}: {e}")
            return ""

    def read_many(self, relative_paths: list[str]) -> dict[str, str]:
        """Read multiple KB files at once from memory."""
        return {path: self.read(path) for path in relative_paths}

    def exists(self, relative_path: str) -> bool:
        """Check if a KB file exists."""
        return (self.kb_path / relative_path).exists()

    def list_files(self, relative_dir: str = "", pattern: str = "*.md") -> list[str]:
        """
        List matching files in a KB directory.
        Cached in RAM for 2 seconds to avoid repeated disk traversals.
        """
        SKIP_DIRS = {"node_modules", "dist", "build", ".next", "__pycache__", ".git", "out"}
        cache_key = (relative_dir, pattern)
        now = time.time()

        if cache_key in self._files_cache:
            ts, files = self._files_cache[cache_key]
            if now - ts < 3.0:
                return files

        target = self.kb_path / relative_dir if relative_dir else self.kb_path
        if not target.exists():
            return []

        results = []
        try:
            for p in target.rglob(pattern):
                if any(skip in p.parts for skip in SKIP_DIRS):
                    continue
                try:
                    results.append(str(p.relative_to(self.kb_path)))
                except Exception:
                    continue
            self._files_cache[cache_key] = (now, results)
        except Exception as e:
            print(f"[KBReader] list_files error in {relative_dir}: {e}")

        return results

    def resolve(self, relative_path: str) -> Path:
        """Get the absolute Path for a relative KB path."""
        return self.kb_path / relative_path

