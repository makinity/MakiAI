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

        if any(kw in lowered for kw in ["what do you remember", "recall", "do you know", "what is my", "what's my", "ano ang"]):
            return self._recall(text)
        elif any(kw in lowered for kw in ["forget", "delete", "remove", "clear"]):
            return self._forget(text)
        else:
            return self._remember(text)

    # ─── Subcommands ─────────────────────────────────────────────────────────

    def _remember(self, text: str) -> str:
        """
        Extract key-value memory from natural language and store it.
        Uses Gemini to parse what to remember with current date/time context.
        """
        now = datetime.now()
        today_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")

        prompt = f"""
The user said: "{text}"
Current Date: {today_str}
Current Time: {time_str} (Philippine Standard Time, UTC+8)

Extract the memory to store and return ONLY a JSON object:
{{
  "key": "short topic label",
  "value": "full detail to remember (Resolve any relative words like 'tomorrow', 'today', 'next week' into concrete dates/times like 'Wednesday, September 16, 2026 at 1:00 PM')"
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
        if not memories:
            return "I don't have any memories stored right now, sir."

        lowered = text.lower()
        search_words = [
            w for w in re.split(r"[^\w]+", lowered)
            if len(w) >= 3 and w not in {
                "forget", "delete", "remove", "clear", "about", "the", "my",
                "our", "that", "this", "memory", "memories", "note", "notes",
                "sir", "maki", "please", "deadline", "task"
            }
        ]

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

        key_to_delete = ""
        try:
            raw_key = self.gemini.send(prompt, "")
            key_to_delete = re.sub(r"^[-*#\s`]+|[`\s]+$", "", raw_key).strip().strip('"').strip("'")
            if key_to_delete.lower().startswith("key:"):
                key_to_delete = key_to_delete[4:].strip()
        except Exception:
            key_to_delete = ""

        target_k = key_to_delete.lower() if key_to_delete and key_to_delete.lower() != "none" else ""
        before = len(memories)

        remaining = []
        deleted_names = []

        for m in memories:
            mk = m.get("key", "").lower()
            mv = m.get("value", "").lower()

            # 1. Match from AI key detection
            matched_by_ai = bool(target_k and (mk == target_k or target_k in mk or mk in target_k))

            # 2. Match from direct keyword tokens in user query
            matched_by_words = bool(search_words and any(w in mk or w in mv for w in search_words))

            if matched_by_ai or matched_by_words:
                deleted_names.append(m.get("key", "Note"))
            else:
                remaining.append(m)

        if len(remaining) < before:
            self._save(remaining)
            deleted_str = ", ".join(deleted_names)
            return f"Done. I've forgotten: {deleted_str}."

        return "I couldn't find that memory in my notes, sir."

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
