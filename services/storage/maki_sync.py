"""
MakiSync Storage — Folder Structure Manager
Central storage system for all MakiAI files.

Every leaf folder uses date-based subfolders (YYYY-MM-DD).
Files are always saved to today's dated folder inside their category.

Structure:
  C:\\MakiSync Storage\\
  ├── School\\
  │   ├── Activities\\     2026-09-11\\ ...
  │   ├── Notes\\          2026-09-11\\ ...
  │   ├── Projects\\       2026-09-11\\ ...
  │   ├── Assignments\\    2026-09-11\\ ...
  │   ├── Exams\\          2026-09-11\\ ...
  │   └── Others\\         2026-09-11\\ ...
  ├── Work\\
  │   ├── Docs\\           2026-09-11\\ ...
  │   ├── Projects\\       2026-09-11\\ ...
  │   ├── Reports\\        2026-09-11\\ ...
  │   └── Others\\         2026-09-11\\ ...
  ├── Personal\\
  │   ├── Images\\         2026-09-11\\ ...
  │   ├── Videos\\         2026-09-11\\ ...
  │   ├── Music\\          2026-09-11\\ ...
  │   └── Others\\         2026-09-11\\ ...
  ├── Freelance\\
  │   ├── Clients\\        2026-09-11\\ ...
  │   ├── Projects\\       2026-09-11\\ ...
  │   ├── Invoices\\       2026-09-11\\ ...
  │   └── Others\\         2026-09-11\\ ...
  └── MakiAI\\
      ├── Screenshots\\    2026-09-11\\ ...
      ├── Photos\\         2026-09-11\\ ...
      └── Recordings\\     2026-09-11\\ ...
"""

from pathlib import Path
from datetime import datetime


MAKI_SYNC_ROOT = Path(r"C:\MakiSync Storage")

# Full folder tree — all leaf folders get date subfolders at runtime
FOLDER_STRUCTURE = {
    "School": [
        "Activities",
        "Notes",
        "Projects",
        "Assignments",
        "Exams",
        "Temp-Guide",
        "Others",
    ],
    "Work": [
        "Docs",
        "Projects",
        "Reports",
        "Others",
    ],
    "Personal": [
        "Images",
        "Videos",
        "Music",
        "Others",
    ],
    "Freelance": [
        "Clients",
        "Projects",
        "Invoices",
        "Others",
    ],
    "MakiAI": [
        "Screenshots",
        "Photos",
        "Recordings",
    ],
}

# File extension → (top_folder, sub_folder) mapping for auto-save routing
FILE_ROUTING = {
    # Documents
    "docx":  ("School", "Activities"),
    "doc":   ("School", "Activities"),
    "xlsx":  ("Work", "Docs"),
    "xls":   ("Work", "Docs"),
    "pptx":  ("School", "Activities"),
    "ppt":   ("School", "Activities"),
    "pdf":   ("School", "Activities"),
    "txt":   ("School", "Notes"),
    "md":    ("School", "Notes"),
    "csv":   ("Work", "Docs"),
    # Images
    "jpg":   ("Personal", "Images"),
    "jpeg":  ("Personal", "Images"),
    "png":   ("Personal", "Images"),
    "gif":   ("Personal", "Images"),
    "webp":  ("Personal", "Images"),
    "heic":  ("Personal", "Images"),
    "bmp":   ("Personal", "Images"),
    # Videos
    "mp4":   ("Personal", "Videos"),
    "mkv":   ("Personal", "Videos"),
    "avi":   ("Personal", "Videos"),
    "mov":   ("Personal", "Videos"),
    "wmv":   ("Personal", "Videos"),
    # Audio
    "mp3":   ("Personal", "Music"),
    "wav":   ("Personal", "Music"),
    "flac":  ("Personal", "Music"),
    "aac":   ("Personal", "Music"),
    # Code / others stay in their project folders
}


def initialize_storage() -> None:
    """
    Create the full MakiSync Storage folder tree.
    Also creates today's dated subfolder inside every leaf folder.
    Safe to call multiple times — only creates missing folders.
    """
    today = _today()
    created = 0

    for top_folder, sub_folders in FOLDER_STRUCTURE.items():
        top_path = MAKI_SYNC_ROOT / top_folder
        top_path.mkdir(parents=True, exist_ok=True)

        for sub in sub_folders:
            sub_path = top_path / sub
            sub_path.mkdir(exist_ok=True)

            # Create today's date folder inside every leaf
            dated = sub_path / today
            dated.mkdir(exist_ok=True)
            created += 1

    print(f"[MakiSync] Storage initialized at {MAKI_SYNC_ROOT} ({created} folders ready)")


def get_dated_folder(category: str, top: str = "MakiAI") -> Path:
    """
    Get or create today's dated subfolder inside a category.

    Args:
        category: Leaf folder name e.g. "Screenshots", "Photos", "Activities"
        top:      Top-level folder e.g. "MakiAI", "School", "Work"

    Returns:
        Path to today's dated folder, created if needed.
        e.g. C:\\MakiSync Storage\\MakiAI\\Screenshots\\2026-09-11\\
    """
    today = _today()
    folder = MAKI_SYNC_ROOT / top / category / today
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_maki_path(category: str) -> Path:
    """
    Get the MakiAI root subfolder (without date).
    Use get_dated_folder() when saving files.

    Args:
        category: "Screenshots", "Photos", or "Recordings"

    Returns:
        Path to C:\\MakiSync Storage\\MakiAI\\<category>\\
    """
    path = MAKI_SYNC_ROOT / "MakiAI" / category
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_folder(top: str, sub: str) -> Path:
    """
    Get a specific category folder root (without date).

    Args:
        top: Top-level folder e.g. "School"
        sub: Sub folder e.g. "Activities"

    Returns:
        Path to C:\\MakiSync Storage\\<top>\\<sub>\\
    """
    path = MAKI_SYNC_ROOT / top / sub
    path.mkdir(parents=True, exist_ok=True)
    return path


def route_file(extension: str) -> tuple[str, str] | None:
    """
    Determine the correct top + sub folder for a file by extension.

    Args:
        extension: File extension without dot e.g. "pdf", "jpg"

    Returns:
        (top_folder, sub_folder) tuple or None if no routing defined.
    """
    return FILE_ROUTING.get(extension.lower())


def list_dated_folders(category: str, top: str = "MakiAI") -> list[str]:
    """
    List all date folders inside a category, newest first.

    Args:
        category: Leaf folder name e.g. "Screenshots"
        top:      Top-level folder e.g. "MakiAI"

    Returns:
        Sorted list of date strings YYYY-MM-DD, newest first.
    """
    root = MAKI_SYNC_ROOT / top / category
    if not root.exists():
        return []
    folders = [f.name for f in root.iterdir() if f.is_dir() and _is_date(f.name)]
    return sorted(folders, reverse=True)


def find_files_by_date(category: str, date: str, top: str = "MakiAI") -> list[Path]:
    """
    Find all files in a category's date folder, newest first.

    Args:
        category: Leaf folder name
        date:     Date string YYYY-MM-DD
        top:      Top-level folder

    Returns:
        List of file Paths, newest first.
    """
    folder = MAKI_SYNC_ROOT / top / category / date
    if not folder.exists():
        return []
    return sorted(
        [f for f in folder.iterdir() if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )


def find_latest_file(category: str, top: str = "MakiAI") -> Path | None:
    """
    Find the most recently created file across all date folders in a category.

    Args:
        category: Leaf folder name
        top:      Top-level folder

    Returns:
        Path to the latest file, or None if none exist.
    """
    root = MAKI_SYNC_ROOT / top / category
    if not root.exists():
        return None
    all_files = sorted(
        [f for f in root.rglob("*") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return all_files[0] if all_files else None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _is_date(name: str) -> bool:
    """Check if a folder name looks like YYYY-MM-DD."""
    try:
        datetime.strptime(name, "%Y-%m-%d")
        return True
    except ValueError:
        return False
