"""
MakiAI — KB Reader
Reads .md files from C:\\Knowledge-Base\\ for use in Gemini context
and skill execution.

All paths are relative to KB_PATH from .env.
"""

from pathlib import Path


class KBReader:
    """
    Reads Markdown files from the Knowledge Base.

    Usage:
        reader = KBReader(kb_path="C:\\Knowledge-Base")
        content = reader.read("workflows/deadlines.md")
        files = reader.read_many(["workflows/time-management.md", "workflows/carryover.md"])
    """

    def __init__(self, kb_path: str):
        """
        Args:
            kb_path: Absolute path to the Knowledge Base root.
                     From settings_service.get_kb_path()
        """
        self.kb_path = Path(kb_path)

    # ─── Public API ──────────────────────────────────────────────────────────

    def read(self, relative_path: str) -> str:
        """
        Read a single KB file and return its content.

        Args:
            relative_path: Path relative to KB root.
                           e.g. "workflows/deadlines.md"

        Returns:
            File content as string, or empty string if not found.
        """
        full_path = self.kb_path / relative_path
        try:
            if not full_path.exists():
                print(f"[KBReader] File not found: {full_path}")
                return ""
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[KBReader] Error reading {relative_path}: {e}")
            return ""

    def read_many(self, relative_paths: list[str]) -> dict[str, str]:
        """
        Read multiple KB files at once.

        Args:
            relative_paths: List of relative paths to read.

        Returns:
            Dict of {relative_path: content}.
            Missing files have empty string values.
        """
        return {path: self.read(path) for path in relative_paths}

    def exists(self, relative_path: str) -> bool:
        """
        Check if a KB file exists.

        Args:
            relative_path: Path relative to KB root.

        Returns:
            True if the file exists.
        """
        return (self.kb_path / relative_path).exists()

    def list_files(self, relative_dir: str = "", pattern: str = "*.md") -> list[str]:
        """
        List all matching files in a KB directory.

        Args:
            relative_dir: Directory relative to KB root. Empty = root.
            pattern:      Glob pattern. Default: "*.md"

        Returns:
            List of relative file paths (as strings).
        """
        target = self.kb_path / relative_dir if relative_dir else self.kb_path
        if not target.exists():
            return []
        return [
            str(p.relative_to(self.kb_path))
            for p in target.rglob(pattern)
        ]

    def resolve(self, relative_path: str) -> Path:
        """
        Get the absolute Path for a relative KB path.

        Args:
            relative_path: Path relative to KB root.

        Returns:
            Absolute Path object.
        """
        return self.kb_path / relative_path
