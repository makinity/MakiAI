"""
MakiAI — Orchestrator
Central command router. Every voice/text command passes through here.
Routes to the correct service or skill based on intent.
"""

from core.state_manager import StateManager, AppState
from services.computer.computer_router import ComputerRouter

# Lightweight system prompt for general conversation — no KB files injected
# Keeps responses fast for questions outside the knowledge base
LIGHT_SYSTEM_PROMPT = """You are MakiAI — a personal AI assistant for Mark Vencent Juntilla, inspired by Jarvis from Iron Man.
Always address the user as "sir". Be warm, conversational, and natural — like a trusted human assistant speaking out loud.
Keep responses concise and spoken — no markdown, no bullet points, no asterisks. Just clear, natural English.
Never say "Certainly!" or "Of course!" — just respond naturally. Be polite, intelligent, and slightly witty when appropriate.

CRITICAL: Never invent, guess, or construct URLs, social media links, or usernames. Only return exact URLs from the Knowledge Base content provided. If a link is not in the KB content, say you don't see it and offer to add it.

You have full access to:
- C:\\Knowledge Base\\ — sir's schedule, deadlines, projects, preferences
- C:\\MakiSync Storage\\ — organized file storage (School, Work, Personal, Freelance, MakiAI with Screenshots/Photos/Recordings in date folders)
You CAN search, open, and manage files in these locations."""


class Orchestrator:
    """
    The brain of MakiAI's command pipeline.

    Receives transcribed text from the voice engine,
    determines intent via the skill router,
    delegates to the correct service or skill,
    and returns the response back to the TTS service.

    Services are injected after initialization to avoid circular imports.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

        # Services — injected via set_services() after all modules initialize
        self.gemini_service = None
        self.tts_service = None
        self.skill_router = None
        self.kb_reader = None
        self.context_builder = None

        # Homework state — tracks if we're waiting for homework instructions
        self._awaiting_homework_instructions = False
        self._homework_skill = None

        # Computer control router
        self.computer_router = ComputerRouter()

    def set_services(self, services: dict) -> None:
        """
        Inject all service dependencies after initialization.

        Args:
            services: A dict of service instances keyed by name.
                Expected keys: gemini, tts, skill_router, kb_reader, context_builder
        """
        self.gemini_service = services.get("gemini")
        self.tts_service = services.get("tts")
        self.skill_router = services.get("skill_router")
        self.kb_reader = services.get("kb_reader")
        self.context_builder = services.get("context_builder")

    def handle_command(self, text: str) -> str:
        """
        Main entry point for all voice/text commands.
        Transitions state, routes command, gets response, speaks it.

        Args:
            text: The transcribed or typed command from the user.

        Returns:
            The response string (also spoken via TTS).
        """
        if not text or not text.strip():
            return ""

        print(f"[Orchestrator] Command received: {text}")
        self.state_manager.set_state(AppState.THINKING)

        response = ""
        try:
            response = self._route(text.strip())
            if response:
                self._speak(response)
        except Exception as e:
            print(f"[Orchestrator] Error handling command: {e}")
            response = "I encountered an error. Please try again."
            self._speak(response)
        finally:
            # State resets to IDLE after TTS finishes (via tts_service callbacks)
            # If TTS is stub, reset here
            if not self.tts_service or not self.tts_service.is_speaking():
                self.state_manager.set_state(AppState.IDLE)

        return response

    def _route(self, text: str) -> str:
        """
        Route priority:
          1. KB Skills (good morning, deadlines, etc.)
          2. Computer control (open, volume, shutdown, etc.)
          3. Gemini fallback (general conversation)
        """
        # Strip wake word before routing
        import re
        cleaned = re.sub(r"^(hey\s+maki[,.]?\s*)", "", text, flags=re.IGNORECASE).strip()

        # 0. Homework follow-up — if waiting for instructions after Temp-Guide was opened
        if self._awaiting_homework_instructions and self._homework_skill:
            self._awaiting_homework_instructions = False
            return self._homework_skill.create_homework(cleaned)

        # 1. KB Skills
        if self.skill_router:
            skill = self.skill_router.detect(cleaned)
            if skill:
                print(f"[Orchestrator] Skill matched: {skill.__class__.__name__}")
                result = skill.execute(cleaned)
                # If HomeworkSkill — set waiting state for follow-up
                if skill.__class__.__name__ == "HomeworkSkill":
                    self._awaiting_homework_instructions = True
                    self._homework_skill = skill
                return result

        # 2. Computer control
        result = self.computer_router.handle(cleaned)
        if result:
            return result

        # 3. Gemini/Groq fallback — general conversation
        # Inject KB context for project/coding/personal questions
        if self.gemini_service:
            context = self._build_context(cleaned)
            return self.gemini_service.send(cleaned, context)

        return f"I heard: {cleaned}. Full AI will be connected once your API key is set."

    def _build_context(self, text: str) -> str:
        """
        Always inject the full KB context.
        build_topic_context reads ALL KB directories dynamically.
        Any KB update is reflected immediately.
        """
        if self.context_builder:
            return self.context_builder.build_topic_context("all")
        return LIGHT_SYSTEM_PROMPT

    def _speak(self, text: str) -> None:
        """
        Send a response to the TTS service for audio output.

        Args:
            text: The text to speak aloud.
        """
        self.state_manager.set_state(AppState.SPEAKING)

        if self.tts_service:
            self.tts_service.speak(text)
        else:
            # Phase 1 stub — TTS not yet connected
            print(f"[Orchestrator] (TTS stub) Maki says: {text}")
