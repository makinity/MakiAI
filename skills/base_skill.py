"""
MakiAI — Base Skill
Abstract base class for all KB skills.

Every skill must implement execute(text) and declare
its required KB files in REQUIRED_FILES.
"""

from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """
    Abstract base class for all MakiAI KB skills.

    Subclasses must implement:
        - SKILL_ID:       Unique skill identifier string
        - REQUIRED_FILES: List of KB-relative file paths needed
        - execute(text):  Main skill logic — returns response string

    Skills receive injected services via __init__ and are registered
    in the SkillRouter by skill_id.
    """

    SKILL_ID: str = ""
    REQUIRED_FILES: list[str] = []

    def __init__(self, gemini_service, context_builder, kb_reader, kb_writer):
        """
        Args:
            gemini_service:  GeminiService instance for AI responses.
            context_builder: ContextBuilder for building system prompts.
            kb_reader:       KBReader for reading KB files.
            kb_writer:       KBWriter for writing KB files.
        """
        self.gemini = gemini_service
        self.context_builder = context_builder
        self.kb_reader = kb_reader
        self.kb_writer = kb_writer

    @abstractmethod
    def execute(self, text: str) -> str:
        """
        Execute the skill and return a response string to be spoken.

        Args:
            text: The full user input that triggered this skill.

        Returns:
            Response string to be spoken aloud by TTS.
        """
        pass

    def _ask_gemini(self, prompt: str) -> str:
        """
        Helper: send a prompt with this skill's KB context to Gemini/Groq.
        Returns a fallback message if response is empty.
        """
        context = self.context_builder.build_skill_context(
            self.SKILL_ID,
            self.REQUIRED_FILES,
        )
        response = self.gemini.send(prompt, context)
        if not response or not response.strip():
            print(f"[{self.SKILL_ID}] Empty response from AI — using fallback.")
            # Try without KB context (lighter prompt)
            response = self.gemini.send(prompt, "")
        if not response or not response.strip():
            return "I'm having trouble thinking right now. Please try again in a moment."
        return response
