"""
MakiAI — File Manager
Organize, move, rename, and search files by voice command.

Handles commands like:
  "organize my downloads folder"
  "search for resume"
  "find all PDF files"
  "move files in downloads"
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


# File type → folder name mapping for auto-organization
FILE_TYPE_MAP = {
    # Documents
    "pdf":   "Documents/PDFs",
    "doc":   "Documents/Word",
    "docx":  "Documents/Word",
    "xls":   "Documents/Excel",
    "xlsx":  "Documents/Excel",
    "ppt":   "Documents/PowerPoint",
    "pptx":  "Documents/PowerPoint",
    "txt":   "Documents/Text",
    "csv":   "Documents/CSV",
    "odt":   "Documents/Other",

    # Images
    "jpg":   "Images",
    "jpeg":  "Images",
    "png":   "Images",
    "gif":   "Images",
    "bmp":   "Images",
    "svg":   "Images",
    "webp":  "Images",
    "ico":   "Images",
    "heic":  "Images",

    # Videos
    "mp4":   "Videos",
    "mkv":   "Videos",
    "avi":   "Videos",
    "mov":   "Videos",
    "wmv":   "Videos",
    "flv":   "Videos",
    "webm":  "Videos",

    # Audio
    "mp3":   "Audio",
    "wav":   "Audio",
    "flac":  "Audio",
    "aac":   "Audio",
    "ogg":   "Audio",
    "m4a":   "Audio",

    # Archives
    "zip":   "Archives",
    "rar":   "Archives",
    "7z":    "Archives",
    "tar":   "Archives",
    "gz":    "Archives",

    # Code
    "py":    "Code/Python",
    "js":    "Code/JavaScript",
    "ts":    "Code/TypeScript",
    "html":  "Code/Web",
    "css":   "Code/Web",
    "java":  "Code/Java",
    "php":   "Code/PHP",
    "cs":    "Code/CSharp",
    "cpp":   "Code/CPP",
    "json":  "Code/Config",
    "xml":   "Code/Config",
    "yaml":  "Code/Config",
    "yml":   "Code/Config",

    # Executables / Installers
    "exe":   "Programs",
    "msi":   "Programs",
    "apk":   "Programs",

    # Shortcuts
    "lnk":   "Shortcuts",
}

# Common folder name aliases
FOLDER_ALIASES = {
    "downloads":    Path.home() / "Downloads",
    "desktop":      Path.home() / "Desktop",
    "documents":    Path.home() / "Documents",
    "pictures":     Path.home() / "Pictures",
    "videos":       Path.home() / "Videos",
    "music":        Path.home() / "Music",
}


class FileManager:
    """
    File organization and search service for MakiAI.

    Usage:
        fm = FileManager()
        result = fm.organize(folder_path)
        results = fm.search(query, search_dir)
        result = fm.move_file(src, dest)
    """

    def organize(self, folder_path: str) -> str:
        """
        Organize all files in a folder by type into subfolders.
        Creates subfolders automatically. Skips folders and hidden files.

        Args:
            folder_path: Path string or alias (e.g. "downloads").

        Returns:
            Summary of what was organized.
        """
        target = self._resolve_path(folder_path)

        if not target or not target.exists():
            return f"I couldn't find the folder '{folder_path}'."

        if not target.is_dir():
            return f"'{folder_path}' is not a folder."

        moved = 0
        skipped = 0
        errors = 0

        for item in target.iterdir():
            # Skip folders, hidden files, and system files
            if item.is_dir() or item.name.startswith("."):
                skipped += 1
                continue

            ext = item.suffix.lower().lstrip(".")
            subfolder_name = FILE_TYPE_MAP.get(ext, "Other")
            dest_dir = target / subfolder_name

            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / item.name

                # Avoid overwriting — append timestamp if name conflicts
                if dest_file.exists():
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest_file = dest_dir / f"{item.stem}_{ts}{item.suffix}"

                shutil.move(str(item), str(dest_file))
                moved += 1
            except Exception as e:
                print(f"[FileManager] Error moving {item.name}: {e}")
                errors += 1

        if moved == 0:
            return f"Nothing to organize in {target.name} — it's already clean."

        result = f"Organized {moved} file{'s' if moved > 1 else ''} in {target.name}."
        if errors:
            result += f" {errors} file{'s' if errors > 1 else ''} couldn't be moved."
        return result

    def search(self, query: str, search_dir: str = "~") -> str:
        """
        Search for files matching a query by name.

        Args:
            query:      Search term (filename or partial name).
            search_dir: Directory to search in. Defaults to home.

        Returns:
            Formatted list of matching file paths.
        """
        target = self._resolve_path(search_dir) or Path.home()
        query_lower = query.lower()
        matches = []
        max_results = 10

        try:
            for item in target.rglob("*"):
                if item.is_file() and query_lower in item.name.lower():
                    matches.append(str(item))
                    if len(matches) >= max_results:
                        break
        except PermissionError:
            pass
        except Exception as e:
            print(f"[FileManager] Search error: {e}")

        if not matches:
            return f"No files found matching '{query}'."

        result = f"Found {len(matches)} file{'s' if len(matches) > 1 else ''} matching '{query}':\n"
        result += "\n".join(f"  • {m}" for m in matches)
        if len(matches) == max_results:
            result += f"\n  (Showing first {max_results} results)"
        return result

    def move_file(self, source: str, destination: str) -> str:
        """
        Move or rename a file.

        Args:
            source:      Source file path.
            destination: Destination path or folder.

        Returns:
            Result message string.
        """
        src = Path(source)
        dest = Path(destination)

        if not src.exists():
            return f"Source file not found: {source}"

        try:
            if dest.is_dir():
                dest = dest / src.name
            shutil.move(str(src), str(dest))
            return f"Moved '{src.name}' to '{dest.parent}'."
        except Exception as e:
            print(f"[FileManager] Move error: {e}")
            return f"Couldn't move the file: {e}"

    def get_folder_summary(self, folder_path: str) -> str:
        """
        Get a quick summary of a folder's contents.

        Args:
            folder_path: Path string or alias.

        Returns:
            Summary string.
        """
        target = self._resolve_path(folder_path)
        if not target or not target.exists():
            return f"Folder '{folder_path}' not found."

        files = [f for f in target.iterdir() if f.is_file()]
        folders = [f for f in target.iterdir() if f.is_dir()]

        return (
            f"{target.name} contains {len(files)} file{'s' if len(files) != 1 else ''} "
            f"and {len(folders)} subfolder{'s' if len(folders) != 1 else ''}."
        )

    # ─── Internal ────────────────────────────────────────────────────────────

    def _resolve_path(self, path_str: str) -> Path | None:
        """Resolve a path string or alias to a Path object."""
        lower = path_str.strip().lower()

        # Check alias map first
        if lower in FOLDER_ALIASES:
            return FOLDER_ALIASES[lower]

        # Try as literal path
        p = Path(path_str).expanduser()
        if p.exists():
            return p

        # Try as home-relative
        home_relative = Path.home() / path_str
        if home_relative.exists():
            return home_relative

        return None
