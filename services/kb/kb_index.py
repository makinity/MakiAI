"""
MakiAI — Knowledge Base FTS5 Search Index
Ultra-fast offline full-text search powered by SQLite FTS5 with BM25 ranking.

Features:
  - Sub-millisecond keyword and phrase lookups across the entire Knowledge Base
  - Incremental sync based on file timestamps (0ms startup overhead when up-to-date)
  - Porter Stemmer and Unicode tokenization for accurate search matching
"""

import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEX_DB_PATH = PROJECT_ROOT / "data" / "kb_index.db"

STOPWORDS = {
    "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
    "have", "has", "had", "does", "is", "are", "was", "were", "my", "your", "the", "a",
    "an", "in", "on", "at", "to", "for", "of", "with", "about", "and", "or", "tell",
    "me", "show", "current", "you", "sir", "maki", "please", "know", "how", "i", "do",
}


class KBIndex:
    """
    High-performance SQLite FTS5 search index for MakiAI.
    """

    def __init__(self, kb_reader=None, db_path: Path = INDEX_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.kb_reader = kb_reader
        self._init_db()
        if self.kb_reader:
            self.sync()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a thread-safe connection to the SQLite database."""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database tables and FTS5 virtual table."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kb_meta (
                    filepath TEXT PRIMARY KEY,
                    mtime REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS kb_docs USING fts5 (
                    filepath,
                    title,
                    category,
                    content,
                    tokenize = 'porter unicode61'
                )
            """)
            conn.commit()

    def sync(self, force: bool = False) -> int:
        """
        Synchronize the index with the physical Knowledge Base.
        Only parses and inserts files that are new or modified since last sync.
        """
        if not self.kb_reader or not self.kb_reader.kb_path.exists():
            return 0

        t0 = time.perf_counter()
        updated_count = 0
        deleted_count = 0

        with self._get_connection() as conn:
            # 1. Fetch current meta map: filepath -> mtime
            cur = conn.execute("SELECT filepath, mtime FROM kb_meta")
            indexed_meta = {row["filepath"]: row["mtime"] for row in cur.fetchall()}

            # 2. Get all physical markdown files
            physical_files = self.kb_reader.list_files("", "*.md")
            current_physical_paths = set()

            for rel_path in physical_files:
                norm_p = rel_path.replace("\\", "/")
                current_physical_paths.add(norm_p)

                # Skip non-relevant folders
                if any(skip in norm_p for skip in ["node_modules", ".git", "voice.md"]):
                    continue

                full_path = self.kb_reader.resolve(rel_path)
                if not full_path.exists():
                    continue

                mtime = full_path.stat().st_mtime
                if not force and norm_p in indexed_meta and indexed_meta[norm_p] == mtime:
                    continue  # Already indexed and up to date

                content = self.kb_reader.read(rel_path)
                if not content or len(content.strip()) < 10:
                    continue

                parts = norm_p.split("/")
                category = parts[0] if len(parts) > 1 else "root"
                title = parts[-1].replace(".md", "").replace("-", " ").title()

                # Remove old doc entry if exists
                conn.execute("DELETE FROM kb_docs WHERE filepath = ?", (norm_p,))
                conn.execute(
                    "INSERT INTO kb_docs (filepath, title, category, content) VALUES (?, ?, ?, ?)",
                    (norm_p, title, category, content),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO kb_meta (filepath, mtime) VALUES (?, ?)",
                    (norm_p, mtime),
                )
                updated_count += 1

            # 3. Clean up deleted files
            for indexed_p in list(indexed_meta.keys()):
                if indexed_p not in current_physical_paths:
                    conn.execute("DELETE FROM kb_docs WHERE filepath = ?", (indexed_p,))
                    conn.execute("DELETE FROM kb_meta WHERE filepath = ?", (indexed_p,))
                    deleted_count += 1

            conn.commit()

        dt = (time.perf_counter() - t0) * 1000
        if updated_count > 0 or deleted_count > 0:
            print(f"[KBIndex] Sync complete: {updated_count} updated, {deleted_count} removed ({dt:.1f}ms).")
        return updated_count

    def index_file(self, rel_path: str, content: str) -> None:
        """Directly index or update a single file in memory and DB."""
        norm_p = rel_path.replace("\\", "/")
        parts = norm_p.split("/")
        category = parts[0] if len(parts) > 1 else "root"
        title = parts[-1].replace(".md", "").replace("-", " ").title()
        mtime = time.time()

        with self._get_connection() as conn:
            conn.execute("DELETE FROM kb_docs WHERE filepath = ?", (norm_p,))
            conn.execute(
                "INSERT INTO kb_docs (filepath, title, category, content) VALUES (?, ?, ?, ?)",
                (norm_p, title, category, content),
            )
            conn.execute(
                "INSERT OR REPLACE INTO kb_meta (filepath, mtime) VALUES (?, ?)",
                (norm_p, mtime),
            )
            conn.commit()

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """
        Execute BM25 ranked full-text search against the index.

        Args:
            query: User search query or question text.
            limit: Maximum number of relevant documents to return.

        Returns:
            List of dicts: [{"filepath": str, "title": str, "category": str, "content": str, "score": float}]
        """
        if not query or not query.strip():
            return []

        # Tokenize and remove stopwords
        words = [re.sub(r"[^a-zA-Z0-9_-]", "", w.lower()) for w in query.split()]
        keywords = [w for w in words if len(w) > 2 and w not in STOPWORDS]

        if not keywords:
            return []

        # Build FTS5 match query with prefixes
        # e.g. "capstone* OR project* OR title*"
        match_query = " OR ".join([f"{kw}*" for kw in keywords])

        results = []
        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    SELECT filepath, title, category, content, bm25(kb_docs, 5.0, 3.0, 2.0, 1.0) AS score
                    FROM kb_docs
                    WHERE kb_docs MATCH ?
                    ORDER BY score
                    LIMIT ?
                    """,
                    (match_query, limit),
                )
                for row in cur.fetchall():
                    results.append({
                        "filepath": row["filepath"],
                        "title": row["title"],
                        "category": row["category"],
                        "content": row["content"],
                        "score": float(row["score"]),
                    })
        except Exception as e:
            print(f"[KBIndex] Search error: {e}")

        return results
