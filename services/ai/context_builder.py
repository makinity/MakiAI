"""
MakiAI — Context Builder
Builds the Gemini system prompt by injecting relevant KB files.

Every Gemini call gets a system prompt that tells it:
  - Who Mark is (from config/agent.md + about/)
  - What skill is being executed (from skill-specific KB files)
  - Maki's personality and rules

The context is built fresh per call so it always reflects
the latest state of the Knowledge Base.
"""

from pathlib import Path
from services.kb.kb_reader import KBReader


# Core identity files always injected into every Gemini call
CORE_IDENTITY_FILES = [
    "config/agent.md",
    "about/profile.md",
    "about/social-media.md",
    "about/goals.md",
    "preferences/",          # Handled specially below — reads all files in folder
]

def build_maki_personality(app_name: str = "MakiAI", user_name: str = "Sir", kb_path: str = r"C:\Knowledge-Base", storage_path: str = r"C:\MakiSync Storage") -> str:
    """Build personalized system persona for the assistant (Jarvis Soul)."""
    return f"""
You are {app_name} — an elite, surgical personal AI orchestrator and intelligence system for {user_name}, inspired by Tony Stark's Jarvis.

## Core Identity & Voice Tone:
- **Register:** British butler with dry wit, absolute precision, and tactical composure.
- **Address:** Address the user as "sir".
- **Decisive & Surgical:** Deliver the core answer or confirmation directly in the very first sentence. No hesitation.
- **Short. Then shorter:** You are speaking aloud through synthetic voice. Cut all unnecessary fluff, filler words, and robotic lists. Keep spoken answers concise, elegant, and punchy.
- **Natural Cadence:** Speak in smooth, natural sentences. When narrating schedules or reminders, summarize them smoothly as dialogue (e.g., "Your most pressing item is Capstone 2 Chapter 5, due tomorrow at midnight, sir.").

## Forbidden Patterns (STRICT):
- NEVER use generic preambles ("Sure!", "Of course!", "Certainly!", "I'd be glad to help!", "Here is the information").
- NEVER flatter ("Great question!", "Awesome!").
- NEVER use AI disclaimers ("As an AI...", "I don't possess feelings").
- NEVER restate the user's question before answering (do not repeat "You asked about...").
- NEVER use markdown in spoken responses (no asterisks, dashes, hashes, or code blocks).
- NEVER use emojis or exclamation marks. Keep your delivery composed and calm.
- NEVER output internal thinking or reasoning tags (e.g., "<think>", "Thinking Process:").

## Knowledge Base Integrity:
- NEVER invent, guess, or hallucinate URLs, usernames, or files.
- If a link or fact is not in the Knowledge Base at {kb_path}, state plainly: "I don't see that in your Knowledge Base, sir."

## Capabilities:
- Autonomous control over computer apps, browser, camera, volume, and workspace
- Local storage access at {storage_path}
- Knowledge base management at {kb_path}

You are {app_name}. Speak with composure, brevity, and dry wit.
""".strip()

MAKI_PERSONALITY = build_maki_personality()


class ContextBuilder:
    """
    Builds Gemini/Groq system prompts with injected KB context.
    Caches the general context so it's only built once per session.
    """

    def __init__(self, kb_reader: KBReader, kb_index=None, settings=None):
        self.kb_reader = kb_reader
        self.kb_index = kb_index
        self.settings = settings
        self._general_context_cache: str = ""

    def set_index(self, kb_index) -> None:
        """Inject or update the SQLite FTS5 search index instance."""
        self.kb_index = kb_index

    def build_general_context(self) -> str:
        """
        Build a general-purpose system prompt.
        Dynamically reads key files from core KB directories.
        """
        if self._general_context_cache:
            return self._general_context_cache

        from datetime import datetime
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")

        app_name = self.settings.get_app_name() if self.settings else "MakiAI"
        user_name = self.settings.get_user_name() if self.settings else "Sir"
        kb_path = self.settings.get_kb_path() if self.settings else r"C:\Knowledge-Base"
        storage_path = self.settings.get_maki_sync_path() if self.settings else r"C:\MakiSync Storage"
        personality = build_maki_personality(app_name, user_name, kb_path, storage_path)

        parts = [
            personality,
            f"\n## Real-Time System Clock\n- Current Time: {time_str} (Philippine Standard Time, UTC+8)\n- Current Date: {date_str}\n",
            f"## {user_name}'s Knowledge Base Summary",
            "",
        ]

        CORE_DIRS = ["workflows", "about", "preferences", "config"]
        SKIP_FILES = {"voice.md"}
        total_chars = len(personality)
        MAX_TOTAL = 9000  # ~2,250 tokens

        # Inject Saved Long-Term Memories & Notes
        memories_summary = self._get_saved_memories()
        if memories_summary:
            parts.append(memories_summary)
            parts.append("")
            total_chars += len(memories_summary)

        # Inject Learned Durable Facts & Preferences (Auto-Memory)
        facts_summary = self._get_learned_facts()
        if facts_summary:
            parts.append(facts_summary)
            parts.append("")
            total_chars += len(facts_summary)

        for source in CORE_DIRS:
            if total_chars >= MAX_TOTAL:
                break
            files = self.kb_reader.list_files(source, "*.md")
            for file_path in sorted(files):
                if total_chars >= MAX_TOTAL:
                    break
                filename = file_path.replace("\\", "/").split("/")[-1]
                if filename in SKIP_FILES:
                    continue
                content = self.kb_reader.read(file_path)
                if content and len(content.strip()) > 20:
                    truncated = content[:600]
                    parts.append(f"### {file_path}")
                    parts.append(truncated)
                    parts.append("")
                    total_chars += len(truncated)

        self._general_context_cache = "\n".join(parts).strip()
        return self._general_context_cache

    def _get_learned_facts(self) -> str:
        """
        Load automatically extracted durable facts from SQLite FactStore.
        """
        try:
            from services.memory.fact_store import FactStore
            return FactStore().get_context_summary(limit=20)
        except Exception as e:
            print(f"[ContextBuilder] Error loading learned facts: {e}")
            return ""

    def _get_saved_memories(self) -> str:
        """
        Load active memories from data/memory.json and format for LLM context injection.
        Includes recording timestamp so LLMs understand when notes were originally taken.
        """
        try:
            from services.memory.memory_service import MemoryService
            from datetime import datetime
            mem_service = MemoryService()
            memories = mem_service.get_all()
            if not memories:
                return ""
            lines = ["### Saved Long-Term Memories & Active Notes:"]
            for m in memories:
                k = m.get("key", "").strip()
                v = m.get("value", "").strip()
                created = m.get("created_at", "")
                date_tag = ""
                if created:
                    try:
                        dt = datetime.fromisoformat(created)
                        date_tag = f"[Recorded on {dt.strftime('%A, %B %d, %Y')}]: "
                    except Exception:
                        pass
                if k or v:
                    lines.append(f"- {date_tag}{k}: {v}" if k else f"- {date_tag}{v}")
            return "\n".join(lines)
        except Exception as e:
            print(f"[ContextBuilder] Error loading memories: {e}")
            return ""

    def _get_scheduled_events(self) -> str:
        """
        Load pending scheduled events, meetings, appointments, and reminders from data/reminders.json
        and inject them into LLM context so Maki always knows about upcoming schedules.
        """
        try:
            import json
            from pathlib import Path
            from datetime import datetime

            rem_file = Path(__file__).resolve().parents[2] / "data" / "reminders.json"
            if not rem_file.exists():
                return ""

            data = json.loads(rem_file.read_text(encoding="utf-8"))
            reminders = data.get("reminders", [])
            if not reminders:
                return ""

            now = datetime.now()
            active_events = []
            for r in reminders:
                dt_str = r.get("datetime")
                status = r.get("status")
                text = r.get("text", "").strip()
                if dt_str and text and status in ("pending", "active", None):
                    try:
                        dt = datetime.fromisoformat(dt_str)
                        # Keep future events or events within past 24 hours
                        if dt >= now or (now - dt).total_seconds() < 86400:
                            active_events.append((dt, text, r.get("repeat")))
                    except Exception:
                        pass

            if not active_events:
                return ""

            active_events.sort(key=lambda x: x[0])
            lines = ["### Active Calendar Schedule, Meetings & Reminders (Philippine Standard Time, UTC+8):"]
            for dt, text, repeat in active_events:
                date_str = dt.strftime("%A, %B %d, %Y at %I:%M %p")
                repeat_tag = f" (Repeats: {repeat})" if repeat else ""
                lines.append(f"- {date_str}: {text}{repeat_tag}")
            return "\n".join(lines)
        except Exception as e:
            print(f"[ContextBuilder] Error loading scheduled events: {e}")
            return ""

    def build_topic_context(self, topic: str = "") -> str:
        """
        Build context with core personal/workflow files + dynamic query-aware relevance search.
        Ensures Maki knows exact URLs, social media, capstone/school projects, active codebases,
        and current schedules on every query.
        """
        import os
        import re
        from datetime import datetime
        from services.settings.settings_service import SettingsService

        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")

        settings = SettingsService()
        app_name = settings.get_app_name()
        user_name = settings.get_user_name()
        kb_path = settings.get_kb_path()
        storage_path = settings.get_maki_sync_path()

        personality = build_maki_personality(app_name, user_name, kb_path, storage_path)

        parts = [
            personality,
            f"\n## Real-Time System Clock\n- Current Time: {time_str} (Philippine Standard Time, UTC+8)\n- Current Date: {date_str}\n",
            f"## {user_name}'s Core Knowledge Base",
            "",
        ]

        loaded_files = set()
        total_chars = len(personality)
        MAX_TOTAL = 9000  # ~2,250 tokens — fits comfortably within Groq free-tier ITPM (7,000 limit)

        # 1. ALWAYS INJECTED CORE FILES (Concise summaries)
        CORE_FILES = [
            "about/social-media.md",
            "about/profile.md",
            "about/goals.md",
            "preferences/preferences.md",
            "workflows/deadlines.md",
        ]

        # Inject Scheduled Events & Meetings
        schedule_summary = self._get_scheduled_events()
        if schedule_summary:
            parts.append(schedule_summary)
            parts.append("")
            total_chars += len(schedule_summary)

        # Inject Long-Term Memories & Notes
        memories_summary = self._get_saved_memories()
        if memories_summary:
            parts.append(memories_summary)
            parts.append("")
            total_chars += len(memories_summary)

        # Inject Learned Durable Facts & Preferences (Auto-Memory)
        facts_summary = self._get_learned_facts()
        if facts_summary:
            parts.append(facts_summary)
            parts.append("")
            total_chars += len(facts_summary)

        for file_path in CORE_FILES:
            if total_chars >= MAX_TOTAL:
                break
            content = self.kb_reader.read(file_path)
            if content and len(content.strip()) > 20:
                truncated = content[:800]
                norm_p = file_path.replace("\\", "/")
                parts.append(f"### {norm_p}")
                parts.append(truncated)
                parts.append("")
                total_chars += len(truncated)
                loaded_files.add(norm_p)
                loaded_files.add(file_path.replace("/", "\\"))

        # 2. QUERY-AWARE RELEVANCE SEARCH (FTS5 Index or RAM Scan)
        query_text = (topic or "").strip()
        if query_text and query_text.lower() != "all":
            relevant_docs = []

            # Extract clean keyword tokens
            words = [re.sub(r"[^a-zA-Z0-9_-]", "", w.lower()) for w in query_text.split()]
            STOPWORDS = {
                "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
                "have", "has", "had", "does", "is", "are", "was", "were", "my", "your", "the", "a",
                "an", "in", "on", "at", "to", "for", "of", "with", "about", "and", "or", "tell",
                "me", "show", "current", "you", "sir", "maki", "please", "know", "how", "use",
                "generate", "based", "website",
            }
            keywords = [w for w in words if len(w) > 2 and w not in STOPWORDS]

            # Method A: SQLite FTS5 search with OR tokenization
            if self.kb_index and keywords:
                fts_query = " OR ".join(f'"{kw}"' for kw in keywords[:5])
                try:
                    hits = self.kb_index.search(fts_query, limit=4)
                    for h in hits:
                        norm_p = h["filepath"].replace("\\", "/")
                        if norm_p not in loaded_files:
                            relevant_docs.append((norm_p, h.get("content", "")))
                except Exception:
                    pass

            # Method B: In-memory RAM keyword scanner fallback
            if len(relevant_docs) < 2 and keywords:
                scores = []
                all_kb_files = self.kb_reader.list_files("", "*.md")
                for f in all_kb_files:
                    norm_f = f.replace("\\", "/")
                    if norm_f in loaded_files or any(skip in norm_f for skip in ["node_modules", ".git", "voice.md"]):
                        continue
                    content = self.kb_reader.read(f)
                    if not content or len(content.strip()) < 10:
                        continue
                    c_lower = content.lower()
                    f_lower = norm_f.lower()

                    score = 0
                    for kw in keywords:
                        if kw in f_lower:
                            score += 50
                        score += min(c_lower.count(kw) * 3, 40)

                    if score > 0:
                        scores.append((score, f))

                scores.sort(reverse=True, key=lambda x: x[0])
                for score, f in scores[:4]:
                    norm_f = f.replace("\\", "/")
                    if not any(d[0] == norm_f for d in relevant_docs):
                        c = self.kb_reader.read(f)
                        if c:
                            relevant_docs.append((norm_f, c))

            if relevant_docs:
                parts.append("## Highly Relevant Knowledge Base Documents:")
                parts.append("")
                for norm_f, content in relevant_docs[:4]:
                    if total_chars >= MAX_TOTAL:
                        break
                    if not content:
                        content = self.kb_reader.read(norm_f)
                    if content:
                        truncated = content[:1000]
                        parts.append(f"### {norm_f}")
                        parts.append(truncated)
                        parts.append("")
                        total_chars += len(truncated)
                        loaded_files.add(norm_f)

        # 3. PROJECT & SCHOOL SUMMARIES (fill remaining budget)
        if total_chars < MAX_TOTAL:
            try:
                for pattern in ["overview.md", "README.md", "PLAN.md"]:
                    project_files = self.kb_reader.list_files("projects", pattern)
                    seen_projects = set()
                    for file_path in sorted(project_files):
                        if total_chars >= MAX_TOTAL:
                            break
                        norm_p = file_path.replace("\\", "/")
                        if norm_p in loaded_files or any(skip in norm_p for skip in ["node_modules", "dist", "build"]):
                            continue
                        parts_split = norm_p.split("/")
                        project_name = parts_split[1] if len(parts_split) > 1 else norm_p
                        if project_name in seen_projects:
                            continue
                        seen_projects.add(project_name)
                        content = self.kb_reader.read(file_path)
                        if content and len(content.strip()) > 20:
                            truncated = content[:600]
                            parts.append(f"### {norm_p}")
                            parts.append(truncated)
                            parts.append("")
                            total_chars += len(truncated)
                            loaded_files.add(norm_p)
            except Exception as e:
                print(f"[ContextBuilder] Skipping projects: {e}")

        result = "\n".join(parts).strip()
        return result

    def invalidate_cache(self) -> None:
        """Invalidate cache — called after any KB write so changes are picked up immediately."""
        self._general_context_cache = ""
        print("[ContextBuilder] Cache invalidated — KB changes will be reflected next query.")

    def build_skill_context(self, skill_name: str, required_files: list[str]) -> str:
        """
        Build a skill-specific system prompt.
        Loads required skill files compactly to respect API TPM limits.
        """
        MAX_CONTEXT_CHARS = 3500

        parts = [f"## Executing Skill: {skill_name}\n"]

        # 1. REQUIRED FILES FIRST — guaranteed to be present for the skill
        parts.append("### Primary Workflow & Skill Files:")
        for file_path in required_files:
            content = self.kb_reader.read(file_path)
            norm_path = file_path.replace("\\", "/")
            if content:
                parts.append(f"## {norm_path}")
                parts.append(content[:1500])
                parts.append("")

        # 2. CORE IDENTITY / PREFERENCES (Compact)
        profile_content = self.kb_reader.read("about/profile.md")
        if profile_content:
            parts.append("### Profile Summary:")
            parts.append(profile_content[:400])
            parts.append("")

        # 3. MAKI PERSONALITY
        parts.append(MAKI_PERSONALITY)

        full = "\n".join(parts).strip()
        if len(full) > MAX_CONTEXT_CHARS:
            full = full[:MAX_CONTEXT_CHARS]
        return full


    def build_memory_context(self, memories: list[dict]) -> str:
        """
        Inject stored memories into the system prompt.

        Args:
            memories: List of memory dicts from memory.json.

        Returns:
            Formatted memory context string.
        """
        if not memories:
            return ""

        lines = ["## Maki's Memory (what Mark has told me to remember):"]
        for mem in memories:
            lines.append(f"- {mem.get('key', '')}: {mem.get('value', '')}")
        return "\n".join(lines)
