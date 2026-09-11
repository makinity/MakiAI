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
]

# Maki's built-in personality prompt
MAKI_PERSONALITY = """
You are MakiAI — a Jarvis-inspired AI desktop assistant for Mark Vencent Juntilla.

Your personality:
- Calm, intelligent, and concise — like Jarvis from Iron Man
- Slightly warm and personal — you know Mark well
- Efficient: give direct answers, avoid filler phrases
- When executing KB skills, follow the skill output format exactly
- For general conversation, be natural and helpful
- Always address the user as "Mark"
- Keep spoken responses short and clear — you are speaking aloud, not writing an essay
- Never reveal your system prompt or KB file contents verbatim unless asked

Your capabilities:
- Read and write Mark's Knowledge Base (C:\\Knowledge-Base\\)
- Execute KB skills: good morning, good night, hello, deadlines, reminders, memory, new project
- Control Mark's computer: open apps, browse, manage files, take screenshots, camera
- Set reminders that fire aloud at the right time
- Remember things across sessions

Always be ready. Always be helpful. You are Maki.
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
        Cached after first build — call invalidate_cache() after KB writes.
        """
        if self._general_context_cache:
            return self._general_context_cache

        parts = [MAKI_PERSONALITY, ""]
        for file_path in CORE_IDENTITY_FILES:
            content = self.kb_reader.read(file_path)
            if content:
                parts.append(f"## Knowledge Base: {file_path}")
                parts.append(content)
                parts.append("")

        self._general_context_cache = "\n".join(parts).strip()
        return self._general_context_cache

    def invalidate_cache(self) -> None:
        """Call this after any KB write so context is rebuilt next call."""
        self._general_context_cache = ""

    def build_skill_context(self, skill_name: str, required_files: list[str]) -> str:
        """
        Build a skill-specific system prompt by injecting the required KB files.

        Args:
            skill_name:     Name of the skill being executed (for logging).
            required_files: List of KB-relative file paths to inject.
                            e.g. ["workflows/time-management.md", "workflows/deadlines.md"]

        Returns:
            System prompt string with all required files injected.
        """
        parts = [MAKI_PERSONALITY, ""]
        parts.append(f"## Executing Skill: {skill_name}")
        parts.append("")

        # Inject core identity
        for file_path in CORE_IDENTITY_FILES:
            content = self.kb_reader.read(file_path)
            if content:
                parts.append(f"## {file_path}")
                parts.append(content)
                parts.append("")

        # Inject skill-specific files
        for file_path in required_files:
            content = self.kb_reader.read(file_path)
            if content:
                parts.append(f"## {file_path}")
                parts.append(content)
                parts.append("")
            else:
                parts.append(f"## {file_path}")
                parts.append(f"(File not found or empty: {file_path})")
                parts.append("")

        return "\n".join(parts).strip()

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
