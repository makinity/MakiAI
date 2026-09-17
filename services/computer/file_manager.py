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
import re
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
    File organization, creation, writing, and search service for MakiAI.

    Usage:
        fm = FileManager()
        result = fm.create_file("notes.txt", "content")
        result = fm.write_to_file(path, "more content")
    """

    def __init__(self):
        self.last_created_file: Path | None = None
        self.last_accessed_file: Path | None = None
        self._cached_index: list[Path] = []
        self._index_time: float = 0.0

    def _scan_directory_fast(self, root: Path, max_depth: int = 4) -> list[Path]:
        """Fast non-recursive directory scanner using os.scandir with directory pruning."""
        if not root or not root.exists():
            return []

        IGNORED_NAMES = {
            "node_modules", ".git", ".next", "__pycache__", "venv", ".venv",
            "dist", "build", ".idea", ".vscode", "appdata", "$recycle.bin",
            "system volume information", "site-packages", ".cache", ".gemini",
            "windows", "program files", "program files (x86)"
        }

        results = []
        stack = [(str(root), 0)]

        while stack:
            curr_dir, depth = stack.pop()
            if depth > max_depth:
                continue
            try:
                with os.scandir(curr_dir) as it:
                    for entry in it:
                        try:
                            name_lower = entry.name.lower()
                            if name_lower.startswith(".") or name_lower in IGNORED_NAMES:
                                continue
                            if entry.is_file(follow_symlinks=False):
                                results.append(Path(entry.path))
                            elif entry.is_dir(follow_symlinks=False):
                                if depth < max_depth:
                                    stack.append((entry.path, depth + 1))
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                continue

        return results

    def get_indexed_files(self, force_refresh: bool = False) -> list[Path]:
        """Return cached indexed files across all priority system roots with 4-second TTL."""
        import time
        now = time.time()
        if not force_refresh and self._cached_index and (now - self._index_time < 4.0):
            return self._cached_index

        from services.storage.maki_sync import MAKI_SYNC_ROOT
        from services.settings.settings_service import SettingsService

        kb_path = Path(SettingsService().get_kb_path())
        roots = [
            (Path.home() / "Downloads", 2),
            (MAKI_SYNC_ROOT, 5),
            (kb_path, 4),
            (Path.home() / "Documents", 3),
            (Path.home() / "Desktop", 2),
            (Path.home() / "Pictures", 3),
            (Path.home() / "Videos", 2),
            (Path(r"c:\development"), 3),
        ]

        all_files = []
        seen = set()
        for root_p, depth in roots:
            if root_p and root_p.exists():
                for f in self._scan_directory_fast(root_p, max_depth=depth):
                    f_str = str(f).lower()
                    if f_str not in seen:
                        seen.add(f_str)
                        all_files.append(f)

        self._cached_index = all_files
        self._index_time = now
        return all_files

    def find_latest_file(self, target_type: str = "any", source: str = "any") -> Path | None:
        """
        Find the newest file matching target_type and source filter across indexed system roots.
        """
        files = self.get_indexed_files()
        if not files:
            return None

        # 1. Resolve Target Extensions
        TYPE_MAP = {
            "docx": {".docx", ".doc"},
            "word": {".docx", ".doc"},
            "doc": {".docx", ".doc"},
            "pdf": {".pdf"},
            "image": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".ico", ".heic"},
            "picture": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".ico", ".heic"},
            "photo": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".heic"},
            "screenshot": {".png", ".jpg", ".jpeg", ".webp"},
            "video": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".flv"},
            "recording": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
            "excel": {".xlsx", ".xls", ".csv"},
            "spreadsheet": {".xlsx", ".xls", ".csv"},
            "xlsx": {".xlsx", ".xls"},
            "csv": {".csv"},
            "powerpoint": {".pptx", ".ppt"},
            "presentation": {".pptx", ".ppt"},
            "pptx": {".pptx", ".ppt"},
            "code": {".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml", ".env"},
            "python": {".py"},
            "script": {".py", ".js", ".ts"},
            "text": {".txt", ".md"},
            "note": {".txt", ".md"},
            "notes": {".txt", ".md"},
            "markdown": {".md"},
            "document": {".docx", ".doc", ".pdf", ".txt", ".md", ".xlsx", ".pptx"},
            "archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
            "zip": {".zip", ".rar", ".7z"},
        }

        target_clean = target_type.lower().strip().lstrip(".")
        if target_type.startswith("."):
            valid_exts = {target_type.lower().strip()}
        else:
            valid_exts = TYPE_MAP.get(target_clean, None)

        filtered = files
        if valid_exts:
            filtered = [f for f in filtered if f.suffix.lower() in valid_exts]

        # 2. Resolve Source Filters
        src_lower = source.lower().strip()
        if src_lower in ("download", "downloads", "downloaded"):
            downloads_dir = str(Path.home() / "Downloads").lower()
            filtered = [f for f in filtered if str(f).lower().startswith(downloads_dir)]
        elif src_lower in ("screenshot", "screenshots"):
            filtered = [f for f in filtered if "screenshot" in str(f).lower() or "capture" in str(f).lower()]
        elif src_lower in ("photo", "photos", "camera"):
            filtered = [f for f in filtered if "photo" in str(f).lower() or "camera" in str(f).lower()]
        elif src_lower in ("recording", "recordings", "video", "videos"):
            filtered = [f for f in filtered if "recording" in str(f).lower() or "video" in str(f).lower()]
        elif src_lower in ("makisync", "storage"):
            from services.storage.maki_sync import MAKI_SYNC_ROOT
            maki_dir = str(MAKI_SYNC_ROOT).lower()
            filtered = [f for f in filtered if str(f).lower().startswith(maki_dir)]
        elif src_lower in ("knowledge_base", "kb", "knowledge"):
            from services.settings.settings_service import SettingsService
            kb_dir = str(SettingsService().get_kb_path()).lower()
            filtered = [f for f in filtered if str(f).lower().startswith(kb_dir)]

        if not filtered:
            return None

        # Sort by mtime descending
        try:
            filtered.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            return filtered[0]
        except Exception:
            return filtered[0] if filtered else None

    def open_latest_file(self, target_type: str = "any", source: str = "any", action: str = "open") -> str:
        """
        Find and either launch the latest file or reveal its folder in File Explorer.
        
        Args:
            target_type: File extension (e.g. 'docx', 'pdf', 'png') or category ('image', 'document', etc.)
            source: Source filter ('download', 'screenshot', 'storage', 'any')
            action: 'open' (launch file) or 'reveal' (open folder with file highlighted)
        """
        latest = self.find_latest_file(target_type=target_type, source=source)
        if not latest:
            type_label = target_type.upper() if target_type.startswith(".") else target_type.capitalize()
            src_label = f" in {source}" if source != "any" else ""
            return f"I couldn't find any recent {type_label} files{src_label} on your PC, sir."

        self.last_accessed_file = latest

        # Nice descriptive name
        friendly_types = {
            "docx": "Word document", "word": "Word document", "doc": "Word document",
            "pdf": "PDF document", "image": "image", "picture": "image", "photo": "photo",
            "screenshot": "screenshot", "video": "video recording", "recording": "recording",
            "excel": "spreadsheet", "spreadsheet": "spreadsheet", "code": "code file", "python": "Python script"
        }
        kind = friendly_types.get(target_type.lower().lstrip("."), f"{target_type.upper()} file")
        src_desc = "downloaded " if source in ("download", "downloads") else ("captured " if source in ("screenshot", "photo") else "")

        if action in ("reveal", "folder", "folder_path", "directory", "show_folder"):
            self._open_in_explorer(latest)
            return f"Opening the folder for your latest {src_desc}{kind}, '{latest.name}', in File Explorer, sir."
        else:
            self._open_file(latest)
            return f"Opening your latest {src_desc}{kind}, '{latest.name}', for you, sir."

    def open_specific_file(self, query: str, action: str = "open") -> str:
        """
        Find a specific file by keyword and open or reveal it.
        """
        found = self.find_file(query)
        if not found:
            return f"I couldn't find any file matching '{query}' across your storage or Knowledge Base, sir."

        self.last_accessed_file = found
        if action in ("reveal", "folder", "folder_path", "directory", "show_folder"):
            self._open_in_explorer(found)
            return f"Opening the folder for '{found.name}' in File Explorer, sir."
        else:
            self._open_file(found)
            return f"Opening '{found.name}' from {found.parent.name} for you, sir."

    def reveal_in_explorer(self, filepath: Path | str) -> str:
        """Reveal a specific file or path in Windows File Explorer."""
        p = Path(filepath) if isinstance(filepath, str) else filepath
        if p.exists():
            if p.is_file():
                self._open_in_explorer(p)
                return f"Opening the folder containing '{p.name}' in File Explorer, sir."
            else:
                self._open_folder_in_explorer(p)
                return f"Opening '{p.name}' folder in File Explorer, sir."
        return f"I couldn't find the path '{filepath}', sir."

    def get_last_file(self) -> Path | None:
        """Return the most recently created or accessed text/document file."""
        DOC_EXTENSIONS = {".txt", ".md", ".docx", ".doc", ".py", ".js", ".html", ".css", ".json", ".csv", ".yaml", ".yml"}
        if self.last_created_file and self.last_created_file.exists() and self.last_created_file.suffix.lower() in DOC_EXTENSIONS:
            return self.last_created_file
        if self.last_accessed_file and self.last_accessed_file.exists() and self.last_accessed_file.suffix.lower() in DOC_EXTENSIONS:
            return self.last_accessed_file

        return self.find_latest_file("document")

    def create_file(self, filename: str, content: str = "", folder_path: str = "") -> str:
        """
        Create a new file with optional content.
        Handles .txt, .md, .docx, .py, .js, .html, .csv, .json properly.
        """
        from services.storage.maki_sync import MAKI_SYNC_ROOT

        # Resolve destination folder
        if folder_path:
            dest = self._resolve_path(folder_path)
            if not dest:
                dest = Path(folder_path)
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest = MAKI_SYNC_ROOT
            dest.mkdir(parents=True, exist_ok=True)

        filepath = dest / filename
        ext = filepath.suffix.lower()

        try:
            if ext == ".docx":
                self._create_docx(filepath, content)
            elif ext in (".txt", ".md", ".py", ".js", ".html", ".css",
                         ".csv", ".json", ".yaml", ".yml", ".env"):
                filepath.write_text(content, encoding="utf-8")
            else:
                # Generic — write as text
                filepath.write_text(content, encoding="utf-8")

            self.last_created_file = filepath
            self.last_accessed_file = filepath

            print(f"[FileManager] Created: {filepath}")
            self._open_file(filepath)
            return f"Done, sir. I've created {filename} in {dest.name} and opened it for you."

        except Exception as e:
            print(f"[FileManager] Create file error: {e}")
            return f"I couldn't create that file, sir: {e}"

    def write_to_file(self, filepath: Path | str, content: str, mode: str = "append") -> str:
        """
        Write or append text content to a file in MakiSync Storage.
        """
        path = Path(filepath) if isinstance(filepath, str) else filepath
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

        ext = path.suffix.lower()
        try:
            if ext == ".docx":
                try:
                    from docx import Document
                    if path.exists() and path.stat().st_size > 0:
                        doc = Document(str(path))
                    else:
                        doc = Document()
                    if content:
                        doc.add_paragraph(content)
                    doc.save(str(path))
                except ImportError:
                    with open(path, "a" if mode == "append" else "w", encoding="utf-8") as f:
                        prefix = "\n\n" if mode == "append" and path.stat().st_size > 0 else ""
                        f.write(prefix + content)
            else:
                existing = ""
                if path.exists() and mode == "append":
                    try:
                        existing = path.read_text(encoding="utf-8")
                    except Exception:
                        existing = ""

                if mode == "append" and existing.strip():
                    new_content = existing.rstrip() + "\n\n" + content.strip()
                else:
                    new_content = content.strip()

                path.write_text(new_content, encoding="utf-8")

            self.last_accessed_file = path
            print(f"[FileManager] Successfully wrote {len(content)} chars to {path}")
            return f"Done, sir. I've written your content into {path.name}."

        except Exception as e:
            print(f"[FileManager] Write error on {path}: {e}")
            return f"I couldn't write to {path.name}, sir: {e}"

    def _create_docx(self, filepath: Path, content: str = "") -> None:
        """Create a proper .docx file using python-docx if available."""
        try:
            from docx import Document
            doc = Document()
            if content:
                doc.add_paragraph(content)
            doc.save(str(filepath))
        except ImportError:
            # python-docx not installed — create as plain text with .docx extension
            print("[FileManager] python-docx not installed — creating plain file.")
            filepath.write_bytes(b"")  # Empty file

    def find_file(self, query: str) -> Path | None:
        """
        Intelligently find any file by path, exact name, or keywords
        across Knowledge Base, MakiSync Storage, and system folders.
        """
        from services.storage.maki_sync import MAKI_SYNC_ROOT
        from services.settings.settings_service import SettingsService

        kb_path = Path(SettingsService().get_kb_path())
        query_clean = query.strip().strip('"\'')

        def _prefer_pdf(path: Path) -> Path:
            """If a PDF version exists alongside a docx/doc/md file, prefer the PDF."""
            if path.suffix.lower() in (".docx", ".doc", ".md", ".txt"):
                pdf_sibling = path.with_suffix(".pdf")
                if pdf_sibling.exists() and pdf_sibling.is_file():
                    return pdf_sibling
            return path

        # 1. Direct path check (e.g. C:\Knowledge-Base\docs\Weekly_Time_Management_Plan_UPDATED)
        direct_p = Path(query_clean)
        if direct_p.exists() and direct_p.is_file():
            return _prefer_pdf(direct_p)
        if direct_p.parent.exists() and direct_p.parent.is_dir():
            for ext in [".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".pptx", ".py", ".png", ".jpg"]:
                cand = direct_p.with_suffix(ext)
                if cand.exists() and cand.is_file():
                    return _prefer_pdf(cand)

        # 2. Search indexed files (Exact filename/stem match first)
        indexed = self.get_indexed_files()
        query_lower = query_clean.lower()

        # Exact match check
        for p in indexed:
            if p.name.lower() == query_lower or p.stem.lower() == query_lower:
                return _prefer_pdf(p)

        # Exact match with common extension check
        for ext in [".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".pptx", ".py", ".png", ".jpg"]:
            cand_name = f"{query_lower}{ext}"
            for p in indexed:
                if p.name.lower() == cand_name:
                    return _prefer_pdf(p)

        # 3. Clean query tokens (remove filler words)
        tokens_raw = re.sub(
            r"\b(open|show|find|get|the|file|document|where|i|store|my|inside|in|knowledge|base|space|storage|please|can|you|for|me|called|named|folder|path|location|directory)\b",
            "",
            query_clean,
            flags=re.IGNORECASE
        ).strip()
        keywords = [t.lower() for t in re.split(r"[\s_\-]+", tokens_raw) if len(t) >= 3]

        if not keywords:
            return None

        # 4. Keyword score search across all indexed files
        best_file = None
        best_score = 0.0

        for p in indexed:
            fname_lower = p.name.lower()
            # Count how many keywords appear in the filename
            matches = sum(1 for kw in keywords if kw in fname_lower)
            if matches > 0:
                # Score formula: matched tokens / total keywords + bonus for exact prefix + bonus for PDF
                score = matches / len(keywords)
                if fname_lower.startswith(keywords[0]):
                    score += 0.2
                if p.suffix.lower() == ".pdf":
                    score += 0.1
                # Prefer more recent files slightly on ties
                if score > best_score:
                    best_score = score
                    best_file = p

        if best_score >= 0.5 and best_file:
            return _prefer_pdf(best_file)

        return None

    def find_folder(self, folder_name: str) -> Path | None:
        """
        Search for a folder by name inside MakiSync Storage.
        """
        from services.storage.maki_sync import MAKI_SYNC_ROOT

        for match in MAKI_SYNC_ROOT.rglob(folder_name):
            if match.is_dir():
                return match

        common = [
            Path.home() / "Desktop" / folder_name,
            Path.home() / "Documents" / folder_name,
            Path.home() / "Downloads" / folder_name,
            MAKI_SYNC_ROOT / folder_name,
        ]
        for p in common:
            if p.exists() and p.is_dir():
                return p

        return None

    def search_file_path(self, filename: str) -> Path | None:
        """Search for a specific file by name in Knowledge Base and MakiSync Storage."""
        return self.find_file(filename)

    def organize(self, folder_path: str = "downloads") -> str:
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
            return f"No files found matching '{query}', sir."

        # Open File Explorer to the folder of the first match and open the file
        first_match = Path(matches[0])
        self._open_in_explorer(first_match)
        self._open_file(first_match)

        result = f"Found {len(matches)} file{'s' if len(matches) > 1 else ''} matching '{query}', sir.\n"
        result += "\n".join(f"  • {m}" for m in matches[:5])
        if len(matches) > 5:
            result += f"\n  (and {len(matches) - 5} more...)"
        result += f"\n\nOpened the first match and its folder for you."
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


    # ─── Smart MakiSync Search ────────────────────────────────────────────────

    def find_latest(self, category: str, top: str = "MakiAI") -> str:
        """Find the most recent file and open File Explorer to its folder."""
        from services.storage.maki_sync import find_latest_file, get_maki_path

        # Try new maki_sync function first
        latest = find_latest_file(category, top)

        if not latest:
            # Fallback to old method
            root = get_maki_path(category)
            all_files = sorted(
                [f for f in root.rglob("*") if f.is_file()],
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            if not all_files:
                return f"I couldn't find any {category.lower()} in MakiSync Storage yet, sir."
            latest = all_files[0]

        # Open explorer with file selected + open the file
        self._open_in_explorer(latest)
        self._open_file(latest)
        return (
            f"Found it, sir. The latest {category[:-1].lower()} is {latest.name} "
            f"from {latest.parent.name}. I've opened it and highlighted it in the folder."
        )

    def find_by_date(self, category: str, date_str: str, top: str = "MakiAI") -> str:
        """Find files by date, open File Explorer to that date folder."""
        from services.storage.maki_sync import get_maki_path, MAKI_SYNC_ROOT
        from datetime import datetime, timedelta

        today = datetime.now()
        date_lower = date_str.lower().strip()

        DATE_MAP = {
            "today": 0, "just now": 0, "right now": 0, "just": 0,
            "yesterday": 1,
            "monday":    (today.weekday() - 0) % 7,
            "tuesday":   (today.weekday() - 1) % 7,
            "wednesday": (today.weekday() - 2) % 7,
            "thursday":  (today.weekday() - 3) % 7,
            "friday":    (today.weekday() - 4) % 7,
            "saturday":  (today.weekday() - 5) % 7,
            "sunday":    (today.weekday() - 6) % 7,
        }

        target_date = None
        if date_lower in DATE_MAP:
            target_date = today - timedelta(days=DATE_MAP[date_lower])
        else:
            try:
                target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except ValueError:
                pass

        if not target_date:
            return f"I couldn't understand the date '{date_str}', sir. Try 'today', 'yesterday', or a date like 2026-09-11."

        date_folder_name = target_date.strftime("%Y-%m-%d")
        root = get_maki_path(category)
        date_folder = root / date_folder_name

        if not date_folder.exists() or not any(date_folder.iterdir()):
            return f"I didn't find any {category.lower()} from {date_folder_name}, sir."

        files = sorted(
            [f for f in date_folder.iterdir() if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        if not files:
            return f"I didn't find any {category.lower()} from {date_folder_name}, sir."

        # Open File Explorer to the date folder and open the latest file
        self._open_folder_in_explorer(date_folder)
        self._open_file(files[0])

        count = len(files)
        if count == 1:
            return (
                f"Found one {category[:-1].lower()} from {date_folder_name}, sir — "
                f"{files[0].name}. I've opened it and shown you the folder."
            )
        return (
            f"Found {count} {category.lower()} from {date_folder_name}, sir. "
            f"I've opened the folder and the latest one: {files[0].name}."
        )

        return f"I couldn't understand the date '{date_str}'. Try 'today', 'yesterday', or a date like 2026-09-11."

    def open_maki_folder(self, category: str) -> str:
        """Open a MakiSync Storage folder in File Explorer."""
        from services.storage.maki_sync import MAKI_SYNC_ROOT, get_maki_path

        cat_lower = category.lower()
        if cat_lower in ("screenshots", "screenshot"):
            folder = get_maki_path("Screenshots")
        elif cat_lower in ("photos", "photo", "pictures", "camera"):
            folder = get_maki_path("Photos")
        elif cat_lower in ("recordings", "recording", "videos", "video"):
            folder = get_maki_path("Recordings")
        else:
            folder = MAKI_SYNC_ROOT

        self._open_folder_in_explorer(folder)
        return f"Opening your {folder.name} folder, sir."

    def _open_file(self, path: Path) -> None:
        """Open a file with its default Windows application."""
        import os
        try:
            os.startfile(str(path))
        except Exception as e:
            print(f"[FileManager] Could not open file: {e}")

    def _open_in_explorer(self, filepath: Path) -> None:
        """Open File Explorer with the specific file selected/highlighted."""
        import subprocess
        try:
            subprocess.Popen(f'explorer /select,"{filepath}"')
        except Exception as e:
            print(f"[FileManager] Explorer select error: {e}")
            self._open_folder_in_explorer(filepath.parent)

    def _open_folder_in_explorer(self, folder: Path) -> None:
        """Open File Explorer to a specific folder."""
        import subprocess
        try:
            subprocess.Popen(f'explorer "{folder}"')
        except Exception as e:
            print(f"[FileManager] Explorer folder error: {e}")
        except Exception as e:
            print(f"[FileManager] Could not open file: {e}")
