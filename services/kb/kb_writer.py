"""
MakiAI — KB Writer
Writes and updates .md files in C:\\Knowledge-Base\\.

Used by skills to update deadlines, carryover, progress, and memory.
All writes are logged for traceability.
"""

from pathlib import Path
from datetime import datetime


class KBWriter:
    """
    Writes and appends to Markdown files in the Knowledge Base.

    Usage:
        writer = KBWriter(kb_path="C:\\Knowledge-Base")
        writer.write("workflows/carryover.md", new_content)
        writer.append("workflows/deadlines.md", "- [ ] New deadline by Friday")
        writer.replace_section("workflows/deadlines.md", "## Pending", new_section)
    """

    def __init__(self, kb_path: str):
        """
        Args:
            kb_path: Absolute path to the Knowledge Base root.
        """
        self.kb_path = Path(kb_path)

    # ─── Public API ──────────────────────────────────────────────────────────

    def write(self, relative_path: str, content: str) -> bool:
        """
        Overwrite a KB file with new content.
        Creates the file if it doesn't exist.

        Args:
            relative_path: Path relative to KB root.
            content:       Full new content to write.

        Returns:
            True on success, False on failure.
        """
        full_path = self.kb_path / relative_path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            self._log(f"WRITE: {relative_path}")
            return True
        except Exception as e:
            print(f"[KBWriter] Write failed [{relative_path}]: {e}")
            return False

    def append(self, relative_path: str, content: str) -> bool:
        """
        Append content to the end of a KB file.
        Creates the file if it doesn't exist.

        Args:
            relative_path: Path relative to KB root.
            content:       Content to append (newline added automatically).

        Returns:
            True on success, False on failure.
        """
        full_path = self.kb_path / relative_path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(f"\n{content}")
            self._log(f"APPEND: {relative_path}")
            return True
        except Exception as e:
            print(f"[KBWriter] Append failed [{relative_path}]: {e}")
            return False

    def replace_section(
        self,
        relative_path: str,
        section_header: str,
        new_section_content: str,
    ) -> bool:
        """
        Replace a specific section in a Markdown file.
        Finds the line matching section_header and replaces everything
        from that line to the next ## heading (or end of file).

        Args:
            relative_path:       Path relative to KB root.
            section_header:      The ## heading line to find.
                                 e.g. "## Pending Tasks"
            new_section_content: The full replacement section including
                                 the heading line.

        Returns:
            True on success, False if section not found or write fails.
        """
        full_path = self.kb_path / relative_path
        if not full_path.exists():
            print(f"[KBWriter] File not found for section replace: {relative_path}")
            return False

        try:
            lines = full_path.read_text(encoding="utf-8").splitlines()
            start_idx = None
            end_idx = len(lines)

            # Find section start
            for i, line in enumerate(lines):
                if line.strip() == section_header.strip():
                    start_idx = i
                    break

            if start_idx is None:
                print(f"[KBWriter] Section not found: '{section_header}' in {relative_path}")
                return False

            # Find next ## heading after start
            for i in range(start_idx + 1, len(lines)):
                if lines[i].startswith("## ") or lines[i].startswith("# "):
                    end_idx = i
                    break

            # Rebuild file with section replaced
            before = lines[:start_idx]
            after = lines[end_idx:]
            new_lines = before + new_section_content.splitlines() + [""] + after

            full_path.write_text("\n".join(new_lines), encoding="utf-8")
            self._log(f"REPLACE_SECTION: {relative_path} [{section_header}]")
            return True

        except Exception as e:
            print(f"[KBWriter] Section replace failed [{relative_path}]: {e}")
            return False

    def update_last_updated(self, relative_path: str) -> bool:
        """
        Update the 'Last Updated:' date in a KB file to today.

        Args:
            relative_path: Path relative to KB root.

        Returns:
            True on success, False on failure.
        """
        full_path = self.kb_path / relative_path
        if not full_path.exists():
            return False

        try:
            content = full_path.read_text(encoding="utf-8")
            today = datetime.now().strftime("%Y-%m-%d")

            # Replace existing date line
            import re
            updated = re.sub(
                r"(Last Updated:?\s*)[\d\-]+",
                f"\\g<1>{today}",
                content,
            )

            if updated != content:
                full_path.write_text(updated, encoding="utf-8")
                self._log(f"UPDATE_DATE: {relative_path}")
            return True
        except Exception as e:
            print(f"[KBWriter] Date update failed [{relative_path}]: {e}")
            return False

    # ─── Internal ────────────────────────────────────────────────────────────

    def _log(self, action: str) -> None:
        """Log a write action to console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[KBWriter] [{timestamp}] {action}")
