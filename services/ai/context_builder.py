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

    def __init__(self, kb_reader: KBReader):
        self.kb_reader = kb_reader
        self._general_context_cache: str = ""

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

    def build_topic_context(self, topic: str) -> str:
        """
        Build context by reading ALL relevant KB directories.
        Prioritizes critical workflow and personal info first,
        and evenly balances content across all directories.
        """
        ALL_KB_DIRS = [
            "workflows",
            "about",
            "preferences",
            "school",
            "career",
            "projects",
            "business",
            "config",
            "learning",
            "va",
            "web-development",
            "faq",
            "decisions",
            "resources",
        ]

        DIRECT_FILES = [
            "preferences/preferences.md",
        ]

        SKIP_FILES = {"voice.md"}  # Skip 11.5k audio transcript dumps

        parts = [MAKI_PERSONALITY, ""]
        parts.append("## Mark's Full Knowledge Base")
        parts.append("")

        total_chars = len(MAKI_PERSONALITY)
        MAX_TOTAL = 20000
        loaded_files = []

        FULL_FILES_NAMES = {
            "time-management.md",
            "deadlines.md",
            "carryover.md",
            "social-media.md",
            "profile.md",
            "goals.md",
            "biodata.md",
            "coding-standards.md",
            "preferences.md",
        }

        # Direct files first
        for file_path in DIRECT_FILES:
            if total_chars >= MAX_TOTAL:
                break
            try:
                content = self.kb_reader.read(file_path)
                if content and len(content.strip()) > 20:
                    truncated = content[:1500]
                    parts.append(f"### {file_path}")
                    parts.append(truncated)
                    parts.append("")
                    total_chars += len(truncated)
                    loaded_files.append(file_path)
            except Exception as e:
                print(f"[ContextBuilder] Skipping {file_path}: {e}")

        # Read across all directories
        for source in ALL_KB_DIRS:
            if total_chars >= MAX_TOTAL:
                break
            try:
                files = self.kb_reader.list_files(source, "*.md")
                for file_path in sorted(files):
                    if total_chars >= MAX_TOTAL:
                        break
                    norm_path = file_path.replace("\\", "/")
                    filename = norm_path.split("/")[-1]
                    if filename in SKIP_FILES:
                        continue
                    if norm_path in [d.replace("\\", "/") for d in loaded_files]:
                        continue

                    content = self.kb_reader.read(file_path)
                    if content and len(content.strip()) > 20:
                        is_full = filename in FULL_FILES_NAMES
                        truncated = content if is_full else content[:800]
                        parts.append(f"### {file_path}")
                        parts.append(truncated)
                        parts.append("")
                        total_chars += len(truncated)
                        loaded_files.append(file_path)
            except Exception as e:
                print(f"[ContextBuilder] Skipping {source}: {e}")
                continue

        # Read project files — overview.md, README.md, or plan.md
        if total_chars < MAX_TOTAL:
            try:
                for pattern in ["overview.md", "README.md", "PLAN.md"]:
                    project_files = self.kb_reader.list_files("projects", pattern)
                    seen_projects = set()
                    for file_path in sorted(project_files):
                        if total_chars >= MAX_TOTAL:
                            break
                        if any(skip in file_path for skip in ["node_modules", "dist", "build", ".next", "src"]):
                            continue
                        norm_p = file_path.replace("\\", "/")
                        parts_split = norm_p.split("/")
                        project_name = parts_split[1] if len(parts_split) > 1 else norm_p
                        if project_name in seen_projects:
                            continue
                        seen_projects.add(project_name)
                        content = self.kb_reader.read(file_path)
                        if content and len(content.strip()) > 20:
                            truncated = content[:800]
                            parts.append(f"### {file_path}")
                            parts.append(truncated)
                            parts.append("")
                            total_chars += len(truncated)
                            loaded_files.append(file_path)
            except Exception as e:
                print(f"[ContextBuilder] Skipping projects: {e}")

        result = "\n".join(parts).strip()
        print(f"[ContextBuilder] Loaded {len(loaded_files)} KB files, {total_chars} chars: {loaded_files[:10]}")
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
