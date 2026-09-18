"""
MakiAI — Durable Fact Store (SQLite)
Stores automatically extracted user facts, preferences, contacts, projects,
routines, hardware setups, and personal context.

Used for context injection into LLM system prompts and autonomous personalization.
"""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Generator

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "memory_facts.db"
_LOCK = threading.Lock()


class FactStore:
    """
    Thread-safe SQLite store for durable user facts and preferences.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that opens and cleanly closes a database connection."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        with _LOCK, self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL DEFAULT 'general',
                    confidence REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'conversation',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_recalled_at TEXT,
                    recall_count INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON user_facts(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_updated ON user_facts(updated_at DESC)")
            conn.commit()

    def save_fact(
        self,
        fact: str,
        category: str = "general",
        confidence: float = 1.0,
        source: str = "conversation"
    ) -> int:
        """
        Save or update a durable fact.
        Deduplicates against exact or highly similar existing facts.
        """
        fact_clean = fact.strip().rstrip(". ")
        if not fact_clean or len(fact_clean) < 4:
            return 0

        now = datetime.now().isoformat()
        category_clean = category.lower().strip() if category else "general"

        with _LOCK, self._connection() as conn:
            cursor = conn.cursor()

            # 1. Exact match check
            cursor.execute("SELECT id, recall_count FROM user_facts WHERE lower(fact) = lower(?)", (fact_clean,))
            row = cursor.fetchone()
            if row:
                fact_id = row["id"]
                new_recall = row["recall_count"] + 1
                cursor.execute("""
                    UPDATE user_facts
                    SET category = ?, confidence = max(confidence, ?), updated_at = ?, recall_count = ?
                    WHERE id = ?
                """, (category_clean, confidence, now, new_recall, fact_id))
                conn.commit()
                return fact_id

            # 2. Key-overlap check (e.g. "User's preferred editor is VS Code" vs "User prefers VS Code editor")
            cursor.execute("SELECT id, fact FROM user_facts WHERE category = ?", (category_clean,))
            rows = cursor.fetchall()
            STOPWORDS = {"that", "this", "with", "from", "have", "been", "will", "about", "your", "user", "mark"}
            new_tokens = set(w.lower() for w in fact_clean.split() if len(w) > 2 and w.lower() not in STOPWORDS)

            for r in rows:
                existing_tokens = set(w.lower() for w in r["fact"].split() if len(w) > 2 and w.lower() not in STOPWORDS)
                if new_tokens and existing_tokens:
                    intersection = new_tokens & existing_tokens
                    union = new_tokens | existing_tokens
                    jaccard = len(intersection) / len(union) if union else 0
                    min_ratio = len(intersection) / min(len(new_tokens), len(existing_tokens)) if min(len(new_tokens), len(existing_tokens)) else 0

                    if jaccard >= 0.5 or min_ratio >= 0.65:
                        cursor.execute("""
                            UPDATE user_facts
                            SET fact = ?, confidence = max(confidence, ?), updated_at = ?
                            WHERE id = ?
                        """, (fact_clean, confidence, now, r["id"]))
                        conn.commit()
                        return r["id"]

            # 3. Insert new fact
            cursor.execute("""
                INSERT INTO user_facts (fact, category, confidence, source, created_at, updated_at, recall_count)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (fact_clean, category_clean, confidence, source, now, now))
            conn.commit()
            return cursor.lastrowid

    def get_all_facts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all stored facts, optionally filtered by category."""
        with _LOCK, self._connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT * FROM user_facts WHERE category = ? ORDER BY updated_at DESC",
                    (category.lower().strip(),)
                )
            else:
                cursor.execute("SELECT * FROM user_facts ORDER BY category, updated_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def search_facts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search facts by query tokens."""
        tokens = [t.lower() for t in query.split() if len(t) >= 3]
        if not tokens:
            return []

        with _LOCK, self._connection() as conn:
            cursor = conn.cursor()
            # Construct LIKE conditions for each token
            clauses = ["lower(fact) LIKE ?" for _ in tokens]
            params = [f"%{t}%" for t in tokens]
            sql = f"SELECT * FROM user_facts WHERE {' OR '.join(clauses)} ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(sql, params)
            return [dict(r) for r in cursor.fetchall()]

    def delete_fact(self, fact_id: Optional[int] = None, keyword: Optional[str] = None) -> bool:
        """Delete a fact by ID or matching keyword."""
        with _LOCK, self._connection() as conn:
            cursor = conn.cursor()
            if fact_id is not None:
                cursor.execute("DELETE FROM user_facts WHERE id = ?", (fact_id,))
            elif keyword:
                cursor.execute("DELETE FROM user_facts WHERE lower(fact) LIKE ?", (f"%{keyword.lower().strip()}%",))
            else:
                return False
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_facts(self) -> None:
        """Wipe all facts from the store."""
        with _LOCK, self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_facts")
            conn.commit()

    def count(self) -> int:
        """Return total number of saved facts."""
        with _LOCK, self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_facts")
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_context_summary(self, limit: int = 20) -> str:
        """
        Generate a clean, categorized markdown summary of learned facts for LLM context injection.
        """
        facts = self.get_all_facts()
        if not facts:
            return ""

        # Limit to top N most recent / relevant facts
        facts = facts[:limit]

        # Group by category
        grouped: Dict[str, List[str]] = {}
        category_titles = {
            "preference": "User Preferences & Habits",
            "contact": "Important Contacts & People",
            "project": "Current Projects & Workflows",
            "hardware": "Hardware & Environment Setup",
            "routine": "Daily Routine & Schedules",
            "personal": "Personal Background & Bio",
            "general": "General Facts",
        }

        for f in facts:
            cat = f.get("category", "general").lower()
            cat_title = category_titles.get(cat, cat.capitalize())
            if cat_title not in grouped:
                grouped[cat_title] = []
            grouped[cat_title].append(f["fact"])

        lines = ["## Learned Facts & Personal Context (Auto-Memory)"]
        for title, items in grouped.items():
            lines.append(f"### {title}:")
            for item in items:
                lines.append(f"- {item}")

        return "\n".join(lines)
