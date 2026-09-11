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
        Dynamically reads all .md files from key KB directories — no hardcoded file list.
        Any KB update is reflected immediately after cache invalidation.
        """
        if self._general_context_cache:
            return self._general_context_cache

        parts = [MAKI_PERSONALITY, ""]
        parts.append("## Mark's Knowledge Base")
        parts.append("")

        # Core identity directories — always loaded
        CORE_DIRS = ["about", "preferences", "config"]
        total_chars = len(MAKI_PERSONALITY)
        MAX_TOTAL = 5000

        for source in CORE_DIRS:
            if total_chars >= MAX_TOTAL:
                break
            files = self.kb_reader.list_files(source, "*.md")
            for file_path in sorted(files):
                if total_chars >= MAX_TOTAL:
                    break
                content = self.kb_reader.read(file_path)
                if content and len(content.strip()) > 20:
                    truncated = content[:800]
                    parts.append(f"### {file_path}")
                    parts.append(truncated)
                    parts.append("")
                    total_chars += len(truncated)

        self._general_context_cache = "\n".join(parts).strip()
        return self._general_context_cache

    def build_topic_context(self, topic: str) -> str:
        """
        Build context by reading ALL relevant KB directories.
        Handles permission errors gracefully — skips unreadable directories.
        """
        ALL_KB_DIRS = [
            "about",
            "config",
            "career",
            "school",
            "workflows",
            "business",
            "smm",
            "web-development",
            "learning",
            "va",
            "resources",
            "faq",
            "decisions",
        ]

        # Files to read directly (avoid directory permission issues)
        DIRECT_FILES = [
            "preferences/preferences.md",
        ]

        parts = [MAKI_PERSONALITY, ""]
        parts.append("## Mark's Full Knowledge Base")
        parts.append("")

        total_chars = len(MAKI_PERSONALITY)
        MAX_TOTAL = 7000
        loaded_files = []

        # Read all standard directories
        for source in ALL_KB_DIRS:
            if total_chars >= MAX_TOTAL:
                break
            try:
                files = self.kb_reader.list_files(source, "*.md")
                for file_path in sorted(files):
                    if total_chars >= MAX_TOTAL:
                        break
                    content = self.kb_reader.read(file_path)
                    if content and len(content.strip()) > 20:
                        truncated = content[:600]
                        parts.append(f"### {file_path}")
                        parts.append(truncated)
                        parts.append("")
                        total_chars += len(truncated)
                        loaded_files.append(file_path)
            except Exception as e:
                print(f"[ContextBuilder] Skipping {source}: {e}")
                continue

        # Read direct files
        for file_path in DIRECT_FILES:
            if total_chars >= MAX_TOTAL:
                break
            try:
                content = self.kb_reader.read(file_path)
                if content and len(content.strip()) > 20:
                    truncated = content[:600]
                    parts.append(f"### {file_path}")
                    parts.append(truncated)
                    parts.append("")
                    total_chars += len(truncated)
            except Exception as e:
                print(f"[ContextBuilder] Skipping {file_path}: {e}")

        # Read project overviews only
        if total_chars < MAX_TOTAL:
            try:
                project_overviews = self.kb_reader.list_files("projects", "overview.md")
                for file_path in sorted(project_overviews):
                    if total_chars >= MAX_TOTAL:
                        break
                    if any(skip in file_path for skip in ["node_modules", "dist", "build", ".next"]):
                        continue
                    content = self.kb_reader.read(file_path)
                    if content and len(content.strip()) > 20:
                        truncated = content[:500]
                        parts.append(f"### {file_path}")
                        parts.append(truncated)
                        parts.append("")
                        total_chars += len(truncated)
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
        """Build a skill-specific system prompt with truncated KB files."""
        MAX_CONTEXT_CHARS = 6000  # Stay well within Groq token limit

        parts = [MAKI_PERSONALITY, ""]
        parts.append(f"## Executing Skill: {skill_name}")
        parts.append("")

        for file_path in CORE_IDENTITY_FILES:
            content = self.kb_reader.read(file_path)
            if content:
                parts.append(f"## {file_path}")
                parts.append(content[:1500])  # Cap identity files
                parts.append("")

        for file_path in required_files:
            content = self.kb_reader.read(file_path)
            if content:
                parts.append(f"## {file_path}")
                parts.append(content[:1000])  # Cap each skill file
                parts.append("")
            else:
                parts.append(f"## {file_path}")
                parts.append(f"(File not found: {file_path})")
                parts.append("")

        full = "\n".join(parts).strip()
        # Final safety truncation
        if len(full) > MAX_CONTEXT_CHARS:
            full = full[:MAX_CONTEXT_CHARS] + "\n...(truncated)"
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
