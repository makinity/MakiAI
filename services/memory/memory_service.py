"""
MakiAI — Memory Service
Stores and retrieves long-term memories across sessions.
Memories are saved in data/memory.json as key-value pairs.

Used by MemorySkill and injected into Gemini context.
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path


MEMORY_FILE = Path(__file__).resolve().parents[2] / "data" / "memory.json"


class MemoryService:
    """
    Long-term memory store for MakiAI.
    Unified with FactStore (SQLite FTS5) for fast retrieval and persistence.
    """

    def __init__(self):
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            from services.memory.fact_store import FactStore
            self.fact_store = FactStore()
        except Exception:
            self.fact_store = None

    # ─── Public API ──────────────────────────────────────────────────────────

    def remember(self, key: str, value: str) -> bool:
        """
        Store or update a memory.
        """
        memories = self._load()
        now = datetime.now().isoformat()

        # Sync to SQLite FactStore
        if self.fact_store:
            cat = "contact" if any(w in (key + " " + value).lower() for w in ["sister", "dog", "brother", "friend", "family", "pet"]) else "preference" if any(w in (key + " " + value).lower() for w in ["favorite", "preferred", "ide", "drink", "language"]) else "personal"
            fact_text = f"{key}: {value}" if key and value and not value.lower().startswith(key.lower()) else value or key
            self.fact_store.save_fact(fact_text, category=cat, confidence=1.0, source="explicit_remember")

        # Update existing key if found
        for mem in memories:
            if mem.get("key", "").lower() == key.lower():
                mem["value"] = value
                mem["updated_at"] = now
                self._save(memories)
                print(f"[MemoryService] Updated: {key}")
                return True

        # Add new memory
        memories.append({
            "id": str(uuid.uuid4()),
            "key": key,
            "value": value,
            "created_at": now,
            "updated_at": now,
        })
        self._save(memories)
        print(f"[MemoryService] Remembered: {key} = {value}")
        return True

    def recall(self, query: str) -> list[dict]:
        """
        Find memories matching a query string using both JSON and SQLite FTS5 search.
        """
        memories = self._load()
        query_lower = query.lower()
        matched = [
            m for m in memories
            if query_lower in m.get("key", "").lower()
            or query_lower in m.get("value", "").lower()
        ]

        # Augment with SQLite FactStore results
        if self.fact_store and not matched:
            fts_matches = self.fact_store.search_facts(query, limit=5)
            for f in fts_matches:
                matched.append({
                    "id": str(f.get("id", uuid.uuid4())),
                    "key": f.get("category", "fact"),
                    "value": f.get("fact", ""),
                    "created_at": f.get("created_at", ""),
                    "updated_at": f.get("updated_at", ""),
                })

        return matched

    def forget(self, key: str) -> bool:
        """
        Delete a memory by key.
        """
        memories = self._load()
        original_len = len(memories)
        memories = [m for m in memories if m.get("key", "").lower() != key.lower()]

        if self.fact_store:
            self.fact_store.delete_fact(keyword=key)

        if len(memories) < original_len:
            self._save(memories)
            print(f"[MemoryService] Forgot: {key}")
            return True
        return False

    def forget_all(self) -> None:
        """Clear all memories."""
        self._save([])
        print("[MemoryService] All memories cleared.")

    def get_all(self) -> list[dict]:
        """Return all stored memories."""
        return self._load()

    def as_context_string(self) -> str:
        """
        Format all memories as a string for Gemini system prompt injection.

        Returns:
            Multi-line string of all memories, or empty string if none.
        """
        memories = self._load()
        if not memories:
            return ""

        user_name = os.getenv("USER_NAME", "User")
        lines = [f"## {user_name}'s Memories (things they asked me to remember):"]
        for mem in memories:
            lines.append(f"- {mem['key']}: {mem['value']}")
        return "\n".join(lines)

    def count(self) -> int:
        """Return the number of stored memories."""
        return len(self._load())

    # ─── Storage ─────────────────────────────────────────────────────────────

    def _load(self) -> list[dict]:
        """Load memories from disk."""
        try:
            if not MEMORY_FILE.exists():
                return []
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8")).get("memories", [])
        except Exception as e:
            print(f"[MemoryService] Load error: {e}")
            return []

    def _save(self, memories: list[dict]) -> None:
        """Save memories to disk."""
        try:
            MEMORY_FILE.write_text(
                json.dumps({"memories": memories}, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[MemoryService] Save error: {e}")
