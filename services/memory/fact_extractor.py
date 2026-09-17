"""
MakiAI — Automatic Fact & Preference Extractor
Asynchronously analyzes conversational turns and extracts durable user facts,
preferences, contacts, projects, and hardware setups into the FactStore.

Runs in a non-blocking background daemon thread.
"""

import json
import re
import threading
from typing import Optional, List, Dict, Any

from services.memory.fact_store import FactStore


# Transient queries to skip extraction for (to save API tokens and avoid noise)
SKIP_PATTERNS = [
    r"^(open|close|launch|kill|exit|shut\s*down|restart|mute|unmute|play|pause|skip|next|prev|volume|tile|maximize|drag|move|minimize)\b",
    r"^(what\s+time|what\s+is\s+the\s+time|what\s+date|what\s+day|what'?s\s+the\s+weather|weather\s+today)\b",
    r"^(take\s+a\s+photo|take\s+a\s+screenshot|start\s+recording|stop\s+recording)\b",
    r"^(good\s+morning|good\s+night|hello|hi|hey|test|testing|ping)\b",
    r"^(clear|cls|help|status|ping)\b",
]


EXTRACTION_PROMPT = """You are the Memory Extraction Engine for MakiAI, a personal AI assistant for Mark Vencent Juntilla.
Analyze the following conversational turn between the user (Mark) and MakiAI.
Extract ONLY durable, long-term, factual knowledge about the user, their preferences, their contacts, their active projects/assignments, their hardware/environment, or their daily routines.

CATEGORIES:
- "preference": Tool choices, coding styles, language preferences, UI themes, likes/dislikes.
- "contact": Names of friends, family, colleagues, email addresses, phone numbers, usernames.
- "project": Ongoing work, homework, school assignments, GitHub repos, active tasks.
- "hardware": Monitors, PC specs, peripherals, screen layout, audio devices.
- "routine": Sleeping habits, exercise schedules, study hours.
- "personal": Bio details, education, birthday, location.

RULES:
1. Extract ONLY facts that are permanently or semi-permanently true.
2. DO NOT extract transient commands, one-time requests (e.g. "open Chrome", "what time is it", "play a song"), or temporary feelings.
3. State each fact clearly in third-person starting with "Mark" or "User" (e.g., "Mark prefers Python for automation scripts").
4. If no durable facts are present in this turn, return an empty list: {"facts": []}.
5. Return ONLY a valid JSON object. Do not include markdown code blocks or conversational commentary.

OUTPUT FORMAT:
{
  "facts": [
    {
      "fact": "Full descriptive statement of the fact",
      "category": "preference|contact|project|hardware|routine|personal",
      "confidence": 0.95
    }
  ]
}
"""


class FactExtractor:
    """
    Background worker that continuously extracts durable facts from conversations.
    """

    def __init__(self, ai_service=None, fact_store: Optional[FactStore] = None):
        self.ai_service = ai_service
        self.fact_store = fact_store or FactStore()

    def set_ai_service(self, ai_service) -> None:
        """Inject AI service (GeminiService / GroqService)."""
        self.ai_service = ai_service

    def should_extract(self, user_text: str) -> bool:
        """Heuristic check to skip purely operational or trivial commands."""
        cleaned = user_text.lower().strip()
        if len(cleaned) < 8:
            return False

        for pattern in SKIP_PATTERNS:
            if re.search(pattern, cleaned):
                return False

        return True

    def extract_async(self, user_text: str, assistant_response: str) -> None:
        """Trigger background extraction in a detached daemon thread."""
        if not self.should_extract(user_text):
            return

        thread = threading.Thread(
            target=self._extract_worker,
            args=(user_text, assistant_response),
            daemon=True,
            name="FactExtractorThread"
        )
        thread.start()

    def extract_sync(self, user_text: str, assistant_response: str = "") -> List[Dict[str, Any]]:
        """Synchronously extract facts (useful for tests and direct ingestion)."""
        if not self.ai_service:
            return []

        prompt = f"""User: {user_text}
MakiAI: {assistant_response}

Extract durable facts:"""

        try:
            raw_result = self.ai_service.send(prompt, system_context=EXTRACTION_PROMPT)
            if not raw_result:
                return []

            # Clean JSON markdown fences if present
            cleaned = raw_result.strip()
            if "```" in cleaned:
                code_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
                if code_match:
                    cleaned = code_match.group(1).strip()
                else:
                    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

            # Extract outermost JSON object if surrounded by extra text
            obj_match = re.search(r"(\{[\s\S]*\})", cleaned)
            if obj_match:
                cleaned = obj_match.group(1).strip()

            # Remove trailing commas before closing braces/brackets
            cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

            facts = []
            try:
                data = json.loads(cleaned)
                facts = data.get("facts", [])
            except Exception:
                # Regex fallback extraction if LLM emitted malformed JSON
                fact_matches = re.findall(r'["\']fact["\']\s*:\s*["\']([^"\']+)["\']', cleaned)
                cat_matches = re.findall(r'["\']category["\']\s*:\s*["\']([^"\']+)["\']', cleaned)
                for idx, f_text in enumerate(fact_matches):
                    cat_text = cat_matches[idx] if idx < len(cat_matches) else "general"
                    facts.append({"fact": f_text, "category": cat_text, "confidence": 1.0})

            saved_facts = []
            for f in facts:
                fact_text = f.get("fact", "").strip()
                cat = f.get("category", "general").strip()
                conf = float(f.get("confidence", 1.0))
                if fact_text and len(fact_text) > 5:
                    fact_id = self.fact_store.save_fact(fact_text, category=cat, confidence=conf)
                    saved_facts.append({"id": fact_id, "fact": fact_text, "category": cat, "confidence": conf})

            if saved_facts:
                print(f"[FactExtractor] Auto-remembered {len(saved_facts)} durable facts into memory.")
            return saved_facts

        except Exception as e:
            print(f"[FactExtractor] Extraction error: {e}")
            return []

    def _extract_worker(self, user_text: str, assistant_response: str) -> None:
        """Internal worker method executed on background thread."""
        self.extract_sync(user_text, assistant_response)
