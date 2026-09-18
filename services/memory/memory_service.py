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

    Memories are simple key-value pairs — Mark tells Maki to remember
    something and Maki can recall it in any future session.

    Usage:
        mem = MemoryService()
        mem.remember("exam date", "Monday September 14")
        mem.recall("exam")          → "exam date: Monday September 14"
        mem.forget("exam date")
        mem.get_all()               → list of all memory dicts
        mem.as_context_string()     → formatted string for Gemini prompt
    """

    def __init__(self):
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    # ─── Public API ──────────────────────────────────────────────────────────

    def remember(self, key: str, value: str) -> bool:
        """
        Store or update a memory.

        Args:
            key:   Short topic label (e.g. "exam date").
            value: Full detail to remember.

        Returns:
            True on success.
        """
        memories = self._load()
        now = datetime.now().isoformat()

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
        Find memories matching a query string.

        Args:
            query: Search term to match against key or value.

        Returns:
            List of matching memory dicts.
        """
        memories = self._load()
        query_lower = query.lower()
        return [
            m for m in memories
            if query_lower in m.get("key", "").lower()
            or query_lower in m.get("value", "").lower()
        ]

    def forget(self, key: str) -> bool:
        """
        Delete a memory by key.

        Args:
            key: The memory key to delete.

        Returns:
            True if found and deleted, False otherwise.
        """
        memories = self._load()
        original_len = len(memories)
        memories = [m for m in memories if m.get("key", "").lower() != key.lower()]

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

        user_name = os.getenv("USER_NAME", "Mark")
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
