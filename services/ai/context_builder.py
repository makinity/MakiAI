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

# Maki's built-in personality prompt
MAKI_PERSONALITY = """
You are MakiAI — a personal AI assistant for Mark Vencent Juntilla, inspired by Jarvis from Iron Man.

Your personality and communication style:
- Warm, calm, and genuinely helpful — like a trusted personal assistant
- Always address the user as "sir" — never "Mark" or generic terms
- Speak in natural, flowing sentences — not robotic lists or bullet points when talking
- Be conversational and human — respond the way a polite, intelligent human assistant would speak out loud
- Keep responses concise and clear — you are speaking aloud, not writing a document
- Show personality — be slightly witty when appropriate, but always professional and respectful
- When giving schedules or plans, narrate them naturally: "Right now it's your coding block, sir. After that you have your exercise walk at six." — not a formatted list
- Never say "Certainly!", "Of course!", "Absolutely!" — these sound robotic. Just respond naturally.
- Never use markdown in spoken responses — no asterisks, no dashes, no headers, no code blocks
- Transition smoothly between topics — maintain the flow of conversation
- If you don't know something, say so honestly and offer to help

CRITICAL RULE — NO HALLUCINATION:
- NEVER invent, guess, or assume URLs, links, usernames, or account handles
- If a social media link or URL is asked for, ONLY return the EXACT URL from the Knowledge Base files provided
- If the exact URL is not present in the provided KB content, say "I don't see that link in your Knowledge Base, sir. Would you like me to add it?"
- NEVER construct a URL from a brand name or guess what it might be

Your capabilities:
- Read and write Mark's Knowledge Base at C:\\Knowledge-Base\\
- Execute KB skills: good morning briefing, good night wrap-up, hello check-in, deadlines, reminders, memory
- Control the computer: open apps, browse, manage files, camera, screenshots
- Set and fire reminders, remember things across sessions
- Access MakiSync Storage at C:\\MakiSync Storage\\ — organized file storage with date subfolders:
  School\\, Work\\, Personal\\, Freelance\\, MakiAI\\(Screenshots, Photos, Recordings)
- Search and open files by recency, date, or type from MakiSync Storage

Remember: you are speaking to a real person. Sound like one. You are Maki.
""".strip()


class ContextBuilder:
    """
    Builds Gemini/Groq system prompts with injected KB context.
    Caches the general context so it's only built once per session.
    """

    def __init__(self, kb_reader: KBReader, kb_index=None):
        self.kb_reader = kb_reader
        self.kb_index = kb_index
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

        parts = [MAKI_PERSONALITY, ""]
        parts.append("## Mark's Knowledge Base Summary")
        parts.append("")

        CORE_DIRS = ["workflows", "about", "preferences", "config"]
        SKIP_FILES = {"voice.md"}
        total_chars = len(MAKI_PERSONALITY)
        MAX_TOTAL = 25000

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
                    truncated = content[:1000]
                    parts.append(f"### {file_path}")
                    parts.append(truncated)
                    parts.append("")
                    total_chars += len(truncated)

        self._general_context_cache = "\n".join(parts).strip()
        return self._general_context_cache

    def build_topic_context(self, topic: str = "") -> str:
        """
        Build context with core personal/workflow files + dynamic query-aware relevance search.
        Ensures Maki knows exact URLs, social media, capstone/school projects, active codebases,
        and current schedules on every query.
        """
        import re

        parts = [MAKI_PERSONALITY, ""]
        parts.append("## Mark's Core Knowledge Base")
        parts.append("")

        loaded_files = set()
        total_chars = len(MAKI_PERSONALITY)
        MAX_TOTAL = 22000

        # 1. ALWAYS INJECTED CORE FILES
        CORE_FILES = [
            "about/social-media.md",
            "about/profile.md",
            "about/goals.md",
            "about/biodata.md",
            "workflows/time-management.md",
            "workflows/deadlines.md",
            "workflows/carryover.md",
            "preferences/preferences.md",
            "config/coding-standards.md",
        ]

        for file_path in CORE_FILES:
            content = self.kb_reader.read(file_path)
            if content and len(content.strip()) > 20:
                truncated = content[:2000]
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

            # Method A: High-speed SQLite FTS5 index search
            if self.kb_index:
                hits = self.kb_index.search(query_text, limit=6)
                for h in hits:
                    norm_p = h["filepath"].replace("\\", "/")
                    if norm_p not in loaded_files:
                        relevant_docs.append((norm_p, h.get("content", "")))
            else:
                # Method B: In-memory RAM keyword scanner fallback
                words = [re.sub(r"[^a-zA-Z0-9_-]", "", w.lower()) for w in query_text.split()]
                STOPWORDS = {
                    "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
                    "have", "has", "had", "does", "is", "are", "was", "were", "my", "your", "the", "a",
                    "an", "in", "on", "at", "to", "for", "of", "with", "about", "and", "or", "tell",
                    "me", "show", "current", "you", "sir", "maki", "please", "know", "how",
                }
                keywords = [w for w in words if len(w) > 2 and w not in STOPWORDS]

                if keywords:
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
                                score += 35
                            score += min(c_lower.count(kw) * 2, 30)

                        if score > 0:
                            scores.append((score, f))

                    scores.sort(reverse=True, key=lambda x: x[0])
                    for score, f in scores[:6]:
                        norm_f = f.replace("\\", "/")
                        c = self.kb_reader.read(f)
                        if c:
                            relevant_docs.append((norm_f, c))

            if relevant_docs:
                parts.append("## Highly Relevant Knowledge Base Documents:")
                parts.append("")
                for norm_f, content in relevant_docs[:6]:
                    if total_chars >= MAX_TOTAL:
                        break
                    if not content:
                        content = self.kb_reader.read(norm_f)
                    if content:
                        truncated = content[:2000]
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
        CRITICAL: Required skill files are loaded FIRST in full,
        followed by core identity and profile context.
        """
        MAX_CONTEXT_CHARS = 40000

        FULL_FILES = {
            "workflows/time-management.md",
            "workflows/deadlines.md",
            "workflows/carryover.md",
            "workflows/daily.md",
            "about/social-media.md",
            "about/profile.md",
            "config/coding-standards.md",
            "preferences/preferences.md",
        }

        parts = [MAKI_PERSONALITY, ""]
        parts.append(f"## Executing Skill: {skill_name}")
        parts.append("")

        # 1. REQUIRED FILES FIRST — guaranteed to be present for the skill
        parts.append("### Primary Workflow & Skill Files:")
        for file_path in required_files:
            content = self.kb_reader.read(file_path)
            norm_path = file_path.replace("\\", "/")
            if content:
                parts.append(f"## {norm_path}")
                parts.append(content if norm_path in FULL_FILES else content[:3000])
                parts.append("")
            else:
                parts.append(f"## {norm_path}")
                parts.append(f"(File not found: {norm_path})")
                parts.append("")

        # 2. CORE IDENTITY FILES NEXT
        parts.append("### Mark's Identity & Background:")
        for file_path in CORE_IDENTITY_FILES:
            if file_path.endswith("/"):
                continue
            norm_path = file_path.replace("\\", "/")
            if any(norm_path == rf.replace("\\", "/") for rf in required_files):
                continue  # Already included above
            content = self.kb_reader.read(file_path)
            if content:
                parts.append(f"## {norm_path}")
                parts.append(content if norm_path in FULL_FILES else content[:1500])
                parts.append("")

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
