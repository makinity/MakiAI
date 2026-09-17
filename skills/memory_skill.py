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
    NAME = "Long-Term Memory & Durable Facts"
    DESCRIPTION = "Store, recall, and manage user preferences, learned facts, and notes across sessions."
    REQUIRED_FILES = []   # Uses local memory.json and memory_facts.db

    TRIGGERS = [
        r"\b(remember\s+that|remember\s+this|remember\s+my|remember\s+our)\b",
        r"\b(what\s+do\s+you\s+remember|what\s+did\s+i\s+tell\s+you|what\s+did\s+i\s+say)\b",
        r"\b(what\s+do\s+you\s+know(?:\s+about\s+me)?|show\s+what\s+you\s+know(?:\s+about\s+me)?|list\s+what\s+you\s+know)\b",
        r"\b(list|show|view|get|tell\s+me)\s+(all\s+)?(learned\s+facts|my\s+facts|facts|memories|memory|stored\s+facts)\b",
        r"\b(what\s+are|what'?s)\s+my\s+(learned\s+facts|preferences|facts|memories)\b",
        r"\b(forget|delete|remove|clear)\s+(about|the|my|this|that|fact|memory)?\b",
        r"\b(do\s+you\s+remember|do\s+you\s+recall|recall)\b",
        r"\b(tandaan\s+mo|naaalala\s+mo\s+ba)\b",
    ]

    def can_handle(self, text: str) -> bool:
        """Custom matcher for natural memory queries."""
        lowered = text.lower().strip()
        return any(kw in lowered for kw in [
            "show what you know", "what you know about me", "what do you know about me",
            "list learned facts", "show learned facts", "show my memory", "list memories",
            "remember that", "remember this", "forget about"
        ])

    def execute(self, text: str) -> str:
        """Route to remember, recall, or forget subcommand."""
        lowered = text.lower()

        if any(kw in lowered for kw in [
            "what do you remember", "recall", "do you know", "what is my", "what's my", "ano ang",
            "show what you know", "what you know about me", "what do you know about me",
            "list learned facts", "show learned facts", "list memories", "show my memory",
            "show memories", "what are my preferences", "my facts"
        ]):
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
        """Search stored memories and auto-extracted facts, returning matching ones."""
        from services.memory.fact_store import FactStore
        memories = self._load()
        facts = FactStore().get_all_facts()

        if not memories and not facts:
            return "I don't have any memories or learned facts stored yet, sir."

        # Build memory + fact summary for Gemini to search
        summary_lines = []
        if memories:
            summary_lines.append("Explicit Notes & Memories:")
            for m in memories:
                summary_lines.append(f"- {m['key']}: {m['value']}")
        if facts:
            summary_lines.append("Auto-Learned Facts & Preferences:")
            for f in facts:
                summary_lines.append(f"- [{f.get('category', 'general')}]: {f.get('fact')}")

        all_text = "\n".join(summary_lines)

        prompt = f"""
The user asked: "{text}"

Here is everything currently in memory and learned facts:
{all_text}

Find and answer the user's question accurately in a natural, spoken tone.
Keep the answer concise (1 to 3 sentences).
If nothing is relevant, say "I don't have anything stored about that, sir."
""".strip()

        return self.gemini.send(prompt, "")

    def _forget(self, text: str) -> str:
        """Remove a memory or learned fact matching the topic mentioned."""
        from services.memory.fact_store import FactStore
        memories = self._load()
        fact_store = FactStore()
        facts = fact_store.get_all_facts()

        if not memories and not facts:
            return "I don't have any memories stored right now, sir."

        lowered = text.lower()
        search_words = [
            w for w in re.split(r"[^\w]+", lowered)
            if len(w) >= 3 and w not in {
                "forget", "delete", "remove", "clear", "about", "the", "my",
                "our", "that", "this", "memory", "memories", "note", "notes",
                "sir", "maki", "please", "deadline", "task", "fact", "facts",
                "preference", "preferences"
            }
        ]

        # Let Gemini identify which memory key or fact text to remove
        all_lines = []
        for m in memories:
            all_lines.append(f"- [NOTE] {m['key']}: {m['value']}")
        for f in facts:
            all_lines.append(f"- [FACT:{f['id']}] {f['fact']}")

        all_text = "\n".join(all_lines)

        prompt = f"""
The user said: "{text}"

Stored memories & facts:
{all_text}

Which item should be deleted?
If it's a note, return: NOTE:<key>
If it's a fact, return: FACT:<id>
If nothing matches, return: NONE
""".strip()

        target_to_delete = ""
        try:
            raw_target = self.gemini.send(prompt, "")
            target_to_delete = re.sub(r"^[-*#\s`]+|[`\s]+$", "", raw_target).strip().strip('"').strip("'")
        except Exception:
            target_to_delete = ""

        deleted_items = []

        # Check FactStore deletion
        if target_to_delete.startswith("FACT:"):
            try:
                fid = int(target_to_delete[5:].strip())
                if fact_store.delete_fact(fact_id=fid):
                    deleted_items.append("learned fact")
            except Exception:
                pass

        # Check keyword deletion in FactStore
        if not deleted_items and search_words:
            for w in search_words:
                if fact_store.delete_fact(keyword=w):
                    deleted_items.append(f"fact about '{w}'")

        # Check memory.json deletion
        target_k = target_to_delete[5:].strip().lower() if target_to_delete.startswith("NOTE:") else ""
        before_mem = len(memories)
        remaining = []

        for m in memories:
            mk = m.get("key", "").lower()
            mv = m.get("value", "").lower()
            matched_by_ai = bool(target_k and (mk == target_k or target_k in mk or mk in target_k))
            matched_by_words = bool(search_words and any(w in mk or w in mv for w in search_words))
            if matched_by_ai or matched_by_words:
                deleted_items.append(m.get("key", "Note"))
            else:
                remaining.append(m)

        if len(remaining) < before_mem:
            self._save(remaining)

        if deleted_items:
            deleted_str = ", ".join(deleted_items)
            return f"Done, sir. I've forgotten: {deleted_str}."

        return "I couldn't find that memory or fact in my records, sir."

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
