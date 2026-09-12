"""
MakiAI — Memory Skill
Store and recall long-term memories across sessions.
Memories are saved in data/memory.json.

Triggered by:
  - "remember that [info]"
  - "what do you remember about [topic]"
  - "forget about [topic]"
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from skills.base_skill import BaseSkill


MEMORY_FILE = Path(__file__).resolve().parents[1] / "data" / "memory.json"


class MemorySkill(BaseSkill):

    SKILL_ID = "memory"
    REQUIRED_FILES = []   # Uses local memory.json, not KB files

    def execute(self, text: str) -> str:
        """Route to remember, recall, or forget subcommand."""
        lowered = text.lower()

        if any(kw in lowered for kw in ["what do you remember", "recall", "do you know"]):
            return self._recall(text)
        elif any(kw in lowered for kw in ["forget", "delete", "remove", "clear"]):
            return self._forget(text)
        else:
            return self._remember(text)

    # ─── Subcommands ─────────────────────────────────────────────────────────

    def _remember(self, text: str) -> str:
        """
        Extract key-value memory from natural language and store it.
        Uses Gemini to parse what to remember.
        """
        prompt = f"""
The user said: "{text}"

Extract the memory to store and return ONLY a JSON object:
{{
  "key": "short topic label",
  "value": "full detail to remember"
}}

Return only the JSON — no explanation, no markdown fences.
""".strip()

        try:
            raw = self.gemini.send(prompt, "")
            raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
            parsed = json.loads(raw)
            key = parsed.get("key", "note").strip()
            value = parsed.get("value", text).strip()

            memories = self._load()
            # Check if key already exists — update instead of duplicate
            updated = False
            for mem in memories:
                if mem.get("key", "").lower() == key.lower():
                    mem["value"] = value
                    mem["updated_at"] = datetime.now().isoformat()
                    updated = True
                    break

            if not updated:
                memories.append({
                    "id": str(uuid.uuid4()),
                    "key": key,
                    "value": value,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                })

            self._save(memories)
            return f"Got it. I'll remember: {key} — {value}."

        except Exception as e:
            print(f"[MemorySkill] Remember error: {e}")
            return "I had trouble storing that memory. Could you rephrase it?"

    def _recall(self, text: str) -> str:
        """Search stored memories and return matching ones."""
        memories = self._load()

        if not memories:
            return "I don't have any memories stored yet. You can say 'remember that' to add some."

        # Build memory summary for Gemini to search
        memory_text = "\n".join([
            f"- {m['key']}: {m['value']}" for m in memories
        ])

        prompt = f"""
The user asked: "{text}"

Here are all stored memories:
{memory_text}

Find and return the most relevant memory or memories.
Keep the answer short — 1 to 3 sentences. Spoken aloud.
If nothing is relevant, say "I don't have anything stored about that."
""".strip()

        return self.gemini.send(prompt, "")

    def _forget(self, text: str) -> str:
        """Remove a memory matching the topic mentioned."""
        memories = self._load()
        lowered = text.lower()

        # Let Gemini identify which memory to remove
        memory_text = "\n".join([
            f"- {m['key']}: {m['value']}" for m in memories
        ])

        prompt = f"""
The user said: "{text}"

Stored memories:
{memory_text}

Which memory key should be deleted? Return ONLY the key string — nothing else.
If nothing matches, return "none".
""".strip()

        key_to_delete = self.gemini.send(prompt, "").strip().strip('"').strip("'")

        if key_to_delete.lower() == "none":
            return "I couldn't find a matching memory to forget."

        before = len(memories)
        memories = [m for m in memories if m.get("key", "").lower() != key_to_delete.lower()]

        if len(memories) < before:
            self._save(memories)
            return f"Done. I've forgotten: {key_to_delete}."
        return "I couldn't find that memory."

    # ─── Storage ─────────────────────────────────────────────────────────────

    def _load(self) -> list[dict]:
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8")).get("memories", [])
        except Exception:
            return []

    def _save(self, memories: list[dict]) -> None:
        try:
            MEMORY_FILE.write_text(
                json.dumps({"memories": memories}, indent=2, default=str),
                encoding="utf-8",
            )
            if self.context_builder:
                self.context_builder.invalidate_cache()
        except Exception as e:
            print(f"[MemorySkill] Save error: {e}")
