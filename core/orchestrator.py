"""
MakiAI — Orchestrator
Central command router. Every voice/text command passes through here.
Routes to the correct service or skill based on intent.
"""

import os
import re
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Tuple

from core.state_manager import StateManager, AppState
from services.computer.computer_router import ComputerRouter
from services.ai.kiro_service import KiroService

TRAINING_MD_PATH = Path(__file__).resolve().parents[1] / "training.md"
COMMAND_LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "command_log.json"
_LOGGER_LOCK = threading.Lock()

# Set to False anytime to turn off training.md auto-logging
ENABLE_TRAINING_LOGGER = True


# Lightweight system prompt for general conversation — no KB files injected
# Keeps responses fast for questions outside the knowledge base
LIGHT_SYSTEM_PROMPT = """You are MakiAI — a personal AI assistant for Mark Vencent Juntilla, inspired by Jarvis from Iron Man.
Always address the user as "sir". Be warm, conversational, and natural — like a trusted human assistant speaking out loud.
Keep responses concise and spoken — no markdown, no bullet points, no asterisks. Just clear, natural English.
Never say "Certainly!" or "Of course!" — just respond naturally. Be polite, intelligent, and slightly witty when appropriate.

CRITICAL: NEVER output your internal thinking, reasoning process, translation steps, or analysis breakdown (e.g. NEVER output "Here's a thinking process: 1. **Analyze User Input:**"). Always speak directly to sir immediately in clear English.

CRITICAL: Never invent, guess, or construct URLs, social media links, or usernames. Only return exact URLs from the Knowledge Base content provided. If a link is not in the KB content, say you don't see it and offer to add it.

You have full access to:
- C:\\Knowledge Base\\ — sir's schedule, deadlines, projects, preferences
- C:\\MakiSync Storage\\ — organized file storage (School, Work, Personal, Freelance, MakiAI with Screenshots/Photos/Recordings in date folders)
- Windows System Control — audio volume, mute, brightness, application launching, media controls, multi-monitor window tiling/relocation, screen vision, and physical webcam vision.
You CAN create, edit, append to, search, open, and manage files and control these system features."""


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
        self.kb_writer = None
        self.context_builder = None

        # Homework state — tracks if we're waiting for homework instructions
        self._awaiting_homework_instructions = False
        self._homework_skill = None

        # Computer control router
        self.computer_router = ComputerRouter()

        # Kiro CLI Coding Engine
        self.kiro_service = KiroService()

    def set_services(self, services: dict) -> None:
        """Inject all backend services after initialization."""
        self.gemini_service = services.get("gemini") or services.get("gemini_service")
        self.tts_service = services.get("tts") or services.get("tts_service")
        self.skill_router = services.get("skill_router")
        self.kb_reader = services.get("kb_reader")
        self.kb_writer = services.get("kb_writer")
        self.context_builder = services.get("context_builder")

        # Pass Gemini to ComputerRouter for vision/smart features
        if self.gemini_service and self.computer_router:
            self.computer_router.set_ai_service(self.gemini_service)

        if self.tts_service and self.computer_router and hasattr(self.computer_router, "health"):
            self.computer_router.health.set_tts_callback(self._speak)

    def handle_command(self, text: str) -> str:
        """
        Main entry point for all voice/text commands.
        Transitions state, routes command, gets response, speaks it,
        and logs the command to training.md and command_log.json.
        """
        if not text or not text.strip():
            return ""

        print(f"[Orchestrator] Command received: {text}")
        self.state_manager.set_state(AppState.THINKING)

        response = ""
        handler_name = "Unknown"
        is_fallback = False
        cleaned_cmd = text.strip()

        try:
            response, handler_name, is_fallback, cleaned_cmd = self._route_with_meta(text.strip())
            if response:
                self._speak(response)
        except Exception as e:
            print(f"[Orchestrator] Error handling command: {e}")
            response = "I encountered an error. Please try again."
            handler_name = "Error"
            is_fallback = True
            self._speak(response)
        finally:
            # Asynchronously log command for self-improvement and training review
            self._log_command_event(text.strip(), cleaned_cmd, handler_name, response, is_fallback)

            # State resets to IDLE after TTS finishes (via tts_service callbacks)
            if not self.tts_service or not self.tts_service.is_speaking():
                self.state_manager.set_state(AppState.IDLE)

        return response

    def _log_command_event(self, raw_text: str, cleaned_text: str, handler_name: str, response: str, is_fallback: bool = False):
        """Asynchronously appends command execution details to training.md and data/command_log.json."""
        if not ENABLE_TRAINING_LOGGER:
            return

        def worker():
            try:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                short_time = datetime.now().strftime("%I:%M:%S %p")
                status_icon = "⚠️ **Fallback / Needs Calibration**" if is_fallback else "✅ **Optimal & Routed**"

                with _LOGGER_LOCK:
                    # 1. Update data/command_log.json
                    COMMAND_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                    log_entries = []
                    if COMMAND_LOG_PATH.exists():
                        try:
                            with open(COMMAND_LOG_PATH, "r", encoding="utf-8") as f:
                                log_entries = json.load(f)
                        except Exception:
                            log_entries = []

                    new_entry = {
                        "timestamp": now_str,
                        "raw_command": raw_text,
                        "cleaned_command": cleaned_text,
                        "handler": handler_name,
                        "response": response,
                        "is_fallback": is_fallback,
                        "flagged_for_review": is_fallback,
                    }
                    log_entries.append(new_entry)
                    if len(log_entries) > 200:
                        log_entries = log_entries[-200:]

                    with open(COMMAND_LOG_PATH, "w", encoding="utf-8") as f:
                        json.dump(log_entries, f, indent=2, ensure_ascii=False)

                    # 2. Append to training.md
                    if TRAINING_MD_PATH.exists():
                        md_block = f"""
### 🔹 Live Session Command — {short_time}
* **Spoken / Typed Command:** `"{raw_text}"`
* **Extracted Payload:** `"{cleaned_text}"`
* **Matched Handler:** `{handler_name}`
* **Status:** {status_icon}
* **Maki Spoken Response:** `"{response[:140].replace(chr(10), ' ')}{'...' if len(response) > 140 else ''}"`

---
"""
                        with open(TRAINING_MD_PATH, "a", encoding="utf-8") as f:
                            f.write(md_block)
            except Exception as e:
                print(f"[Orchestrator] Command logger error: {e}")


        threading.Thread(target=worker, daemon=True, name="CommandLoggerThread").start()

    def _route(self, text: str) -> str:
        """Compatibility wrapper for _route_with_meta."""
        res, _, _, _ = self._route_with_meta(text)
        return res

    def _route_with_meta(self, text: str) -> Tuple[str, str, bool, str]:
        """
        Route priority with metadata capture:
          0. Homework follow-up / Kiro CLI coding requests
          1. KB Skills (good morning, deadlines, etc.)
          2. Computer control (open, volume, shutdown, etc.)
          3. Gemini/Groq fallback (general conversation)
        """
        # Strip wake word before routing
        import re
        raw_stripped = text.strip()
        cleaned = re.sub(r"^(hey\s+maki[,.]?\s*|maki[,.]?\s*)", "", raw_stripped, flags=re.IGNORECASE).strip()

        # Instant acknowledgment for bare name calls ("Maki.", "Hey Maki") without redundant LLM latency
        if re.match(r"^(hey\s+maki|maki|maki\s*ai|hey)[.,?!]?$", raw_stripped, flags=re.IGNORECASE) or not cleaned:
            return "Yes, sir? I'm listening.", "DirectAcknowledgment", False, cleaned

        # Instant acknowledgment for simple pleasantries ("Thank you.", "Thanks Maki")
        if re.match(r"^(thank\s+you|thanks|thank\s+you\s+maki|thanks\s+maki)[.,?!]?$", raw_stripped, flags=re.IGNORECASE):
            return "You're welcome, sir.", "DirectAcknowledgment", False, cleaned

        # 0. Kiro CLI Integration (Interactive Terminal or Headless Code Gen)
        if "kiro" in cleaned.lower():
            is_interactive = bool(re.search(r"\b(open|launch|start|terminal|window|develop|interactive)\b", cleaned, flags=re.IGNORECASE))
            
            # Extract project name if mentioned
            proj_name = "TaskMaster"
            proj_match = re.search(r"\b(?:for|on|in|developing|build|building)\s+([a-zA-Z0-9_\-]+)", cleaned, flags=re.IGNORECASE)
            if proj_match:
                cand = proj_match.group(1).strip()
                if cand.lower() not in ("kiro", "the", "a", "an", "my", "this", "that"):
                    proj_name = cand

            if is_interactive:
                # Check if user requested a specific sub-task or stage
                task_spec = ""
                stage_match = re.search(r"(stage\s+\d+|phase\s+\d+|step\s+\d+|[^\w\s].+)", cleaned, flags=re.IGNORECASE)
                if stage_match:
                    task_spec = f"Focus on implementing {stage_match.group(0).strip()}."
                return self.kiro_service.launch_interactive_session(initial_prompt=task_spec, project_name=proj_name), "KiroService:Interactive", False, cleaned
            else:
                # Strip kiro trigger keywords for clean headless instruction
                instruction = re.sub(r"^(?:t|target)\s*=\s*kiro\s+", "", cleaned, flags=re.IGNORECASE)
                instruction = re.sub(r"\b(?:use\s+kiro\s+to|with\s+kiro|ask\s+kiro\s+to|have\s+kiro|kiro)\b", "", instruction, flags=re.IGNORECASE).strip()
                kb_ctx = ""
                if self.context_builder:
                    kb_ctx = self.context_builder.build_topic_context(instruction or cleaned)
                return self.kiro_service.generate_code(instruction or cleaned, kb_context=kb_ctx), "KiroService:Headless", False, cleaned

        # 0. Active Project Planning session follow-up
        if self.skill_router:
            new_proj_skill = self.skill_router.get_skill("new_project")
            if new_proj_skill and getattr(new_proj_skill, "is_planning_active", lambda: False)():
                # Check for explicit cancellation
                if re.search(r"\b(cancel|stop|abort|exit|quit|nevermind|never\s+mind)\b", cleaned, flags=re.IGNORECASE):
                    new_proj_skill.reset()
                    return "Project planning session cancelled, sir.", "NewProjectSkill:ActivePlanning", False, cleaned

                # If the user issues a distinct skill command or computer control, route it properly without being trapped
                other_skill = self.skill_router.detect(cleaned)
                if other_skill and getattr(other_skill, "SKILL_ID", "") != "new_project":
                    skill_name = other_skill.__class__.__name__
                    return other_skill.execute(cleaned), f"Skill:{skill_name}", False, cleaned

                comp_res = self.computer_router.handle(cleaned)
                if comp_res:
                    return comp_res, "ComputerRouter", False, cleaned

                # Otherwise send input to the planning engine
                return new_proj_skill.execute(cleaned), "NewProjectSkill:ActivePlanning", False, cleaned

        # 0. Homework follow-up — if waiting for instructions after Temp-Guide was opened
        if self._awaiting_homework_instructions and self._homework_skill:
            if re.search(r"\b(cancel|stop|abort|nevermind|never\s+mind)\b", cleaned, flags=re.IGNORECASE):
                self._awaiting_homework_instructions = False
                return "Homework creation cancelled, sir.", "HomeworkSkill:Cancelled", False, cleaned

            # Check if input is a distinct skill command
            other_skill = self.skill_router.detect(cleaned) if self.skill_router else None
            if other_skill and getattr(other_skill, "SKILL_ID", "") != "homework":
                self._awaiting_homework_instructions = False
                skill_name = other_skill.__class__.__name__
                return other_skill.execute(cleaned), f"Skill:{skill_name}", False, cleaned

            # Check if input is a computer control command
            comp_res = self.computer_router.handle(cleaned)
            if comp_res:
                self._awaiting_homework_instructions = False
                return comp_res, "ComputerRouter", False, cleaned

            self._awaiting_homework_instructions = False
            return self._homework_skill.create_homework(cleaned), "HomeworkSkill:GenerateDocx", False, cleaned

        # 1. KB Skills
        if self.skill_router:
            skill = self.skill_router.detect(cleaned)
            if skill:
                skill_name = skill.__class__.__name__
                print(f"[Orchestrator] Skill matched: {skill_name}")
                result = skill.execute(cleaned)
                # If HomeworkSkill — set waiting state for follow-up
                if skill_name == "HomeworkSkill":
                    self._awaiting_homework_instructions = True
                    self._homework_skill = skill
                return result, f"Skill:{skill_name}", False, cleaned

        # 2. Computer control
        result = self.computer_router.handle(cleaned)
        if result:
            return result, "ComputerRouter", False, cleaned

        # 3. Gemini/Groq fallback — general conversation
        # Inject KB context for project/coding/personal questions
        if self.gemini_service:
            context = self._build_context(cleaned)
            return self.gemini_service.send(cleaned, context), "Fallback:Gemini", True, cleaned

        return f"I heard: {cleaned}. Full AI will be connected once your API key is set.", "Fallback:Stub", True, cleaned

    def _match_kiro_intent(self, text: str) -> str | None:
        """Detect if the user is delegating a coding instruction to Kiro."""
        import re
        lowered = text.lower().strip()

        # Direct tag: "t=kiro [prompt]" or "target=kiro [prompt]"
        tag_match = re.match(r"^(?:t|target)\s*=\s*kiro\s+(.+)$", text, flags=re.IGNORECASE)
        if tag_match:
            return tag_match.group(1).strip()

        # Voice / Natural language triggers
        patterns = [
            r"^(?:use\s+kiro\s+(?:to\s+)?|ask\s+kiro\s+(?:to\s+)?|have\s+kiro\s+)(.+)$",
            r"^(?:code\s+with\s+kiro|build\s+with\s+kiro|generate\s+(?:code\s+)?with\s+kiro)\s*[:,\s]+(.+)$",
            r"^kiro[:,\s]+(.+)$",
            r"^(?:kiro\s+)(.+)$",
        ]
        for p in patterns:
            m = re.match(p, lowered)
            if m:
                return text[m.start(1):].strip()

        return None

    def _build_context(self, text: str) -> str:
        """
        Inject KB context into the system prompt with query-aware relevance search.
        """
        if self.context_builder:
            return self.context_builder.build_topic_context(text)
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
            try:
                print(f"[Orchestrator] (TTS stub) Maki says: {text}")
            except Exception:
                safe_text = text.encode("ascii", errors="replace").decode("ascii")
                print(f"[Orchestrator] (TTS stub) Maki says: {safe_text}")
