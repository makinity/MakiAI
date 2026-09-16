"""
MakiAI — UI Bridge API
Provides the desktop bridge connecting the frontend HTML5/Canvas/CSS interface
with MakiAI's core Orchestrator, StateManager, Voice Engine, and AI subsystem.
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
import speech_recognition as sr

from core.state_manager import StateManager, AppState
from core.orchestrator import Orchestrator
from services.settings.settings_service import SettingsService
from services.voice.tts_service import TTSService
from services.voice.stt_service import STTService
from services.voice.wake_word_service import WakeWordService
from services.voice.ptt_service import PushToTalkService
from services.reminder.reminder_service import ReminderService


class MakiUIApi:
    """
    JS API Bridge for the MakiAI Desktop Interface.
    Exposes methods callable from JavaScript in the web frontend.
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        state_manager: StateManager,
        settings: SettingsService,
        tts_service: TTSService,
        stt_service: STTService,
        wake_word_service: Optional[WakeWordService] = None,
        ptt_service: Optional[PushToTalkService] = None,
        reminder_service: Optional[ReminderService] = None,
    ):
        self.orchestrator = orchestrator
        self.state_manager = state_manager
        self.settings = settings
        self.tts_service = tts_service
        self.stt_service = stt_service
        self.wake_word_service = wake_word_service
        self.ptt_service = ptt_service
        self.reminder_service = reminder_service

        self.bot_name = self.settings.get_app_name()
        self._lock = threading.Lock()
        self._activity: List[Dict[str, str]] = []
        self._auto_listen_enabled = True
        self._command_busy = False
        self._session_active = False
        self._session_expires_at = 0.0
        self._last_command_text = ""
        self._last_command_time = 0.0
        self._active_modal: Optional[Dict[str, Any]] = None

        # Add initial welcome greeting to activity
        self._activity.append({
            "type": "system",
            "text": "MakiAI core initialized. Desktop interface ready.",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

        # Connect state changes
        self.state_manager.on_state_change(self._on_app_state_changed)

        # Connect reminder callback if available
        if self.reminder_service:
            self.reminder_service.on_reminder_fire = self._on_reminder_fire

        # Connect PTT callback if available
        if self.ptt_service:
            self.ptt_service.set_callbacks(
                on_ptt_start=lambda: self.state_manager.set_state(AppState.LISTENING),
                on_ptt_end=lambda: self.state_manager.set_state(AppState.THINKING),
                on_result=self.on_ptt_command,
                on_empty=lambda: self.state_manager.set_state(AppState.IDLE),
            )

        # Connect WakeWord callbacks if available
        if self.wake_word_service:
            self.wake_word_service.on_wake = self._on_wake_detected
            self.wake_word_service.on_wake_with_command = self._on_wake_with_command

    # ─── State Mapping ────────────────────────────────────────────────────────

    def _on_app_state_changed(self, new_state: AppState) -> None:
        """Called when Python AppState transitions."""
        pass

    # ─── Conversational Voice Engine (Active Session Mode) ────────────────────

    def _on_wake_detected(self) -> None:
        """Wake word heard alone — greet user and enter Active Conversation Session."""
        if not self.state_manager.is_idle():
            return
        print("[UIBridge] Wake word detected — activating conversation session.")
        if self.wake_word_service and self.wake_word_service.is_running:
            self.wake_word_service.stop()
        self._start_active_session("hello")

    def _on_wake_with_command(self, command: str) -> None:
        """Wake word + command — handle command and enter Active Conversation Session."""
        clean = (command or "").strip()
        if not clean or not self.state_manager.is_idle():
            return
        print(f"[UIBridge] Wake word + command: '{clean}' — activating conversation session.")
        if self.wake_word_service and self.wake_word_service.is_running:
            self.wake_word_service.stop()
        self._start_active_session(clean)

    def _start_active_session(self, initial_command: str = "") -> None:
        """Start or refresh the 45-second active conversation session."""
        self._session_active = True
        self._session_expires_at = time.time() + 45.0
        threading.Thread(
            target=self._session_worker,
            args=(initial_command,),
            daemon=True,
            name="ActiveSessionThread"
        ).start()

    def _session_worker(self, initial_command: str = "") -> None:
        """Runs the active listening session without requiring 'Hey Maki'."""
        if initial_command:
            self._handle_voice_command_sync(initial_command)
            self._session_expires_at = time.time() + 45.0

        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = False
        recognizer.energy_threshold = 250
        recognizer.pause_threshold = 0.45
        recognizer.non_speaking_duration = 0.35

        while self._session_active and self._auto_listen_enabled:
            # Check timeout (45s of silence)
            if time.time() > self._session_expires_at:
                print("[UIBridge] Active session timed out — returning to standby.")
                self._exit_active_session()
                return

            # Wait while Maki is speaking or PTT is recording
            if (self.tts_service and self.tts_service.is_speaking_or_recent(0.5)) or (self.ptt_service and self.ptt_service.is_recording):
                time.sleep(0.1)
                continue

            try:
                self.state_manager.set_state(AppState.LISTENING)
                with sr.Microphone() as source:
                    audio = recognizer.listen(source, timeout=4, phrase_time_limit=10)

                # Gate check: discard if TTS spoke or PTT recorded during listening
                if (self.tts_service and self.tts_service.is_speaking_or_recent(0.5)) or (self.ptt_service and self.ptt_service.is_recording):
                    continue

                self.state_manager.set_state(AppState.THINKING)
                wav_bytes = audio.get_wav_data()
                text, provider = self.stt_service._transcriber.transcribe_wav_bytes(wav_bytes)

                if not text or len(text.strip()) < 2:
                    self.state_manager.set_state(AppState.IDLE)
                    continue

                print(f"[ActiveSession] Heard ({provider}): '{text}'")

                # Check if user asked to sleep/standby (ensuring action commands like "remove the zoom meeting because it was cancelled" are not mistaken for standby)
                clean_lower = text.strip().lower().rstrip(".!?,")
                standby_phrases = {
                    "go to sleep", "sleep", "goodbye", "good night", "stop listening",
                    "never mind", "dismiss", "that's all", "that is all", "standby", "go to standby"
                }
                is_standby_phrase = (
                    clean_lower in standby_phrases or
                    clean_lower in ["cancel", "cancel that"] or
                    clean_lower.startswith(("go to sleep", "stop listening", "go to standby"))
                )
                is_action_command = any(k in clean_lower for k in [
                    "meeting", "schedule", "reminder", "timer", "alarm", "event", "zoom",
                    "remove", "delete", "clear", "forget", "deadline", "video", "clip", "volume", "open", "launch"
                ])

                if is_standby_phrase and not is_action_command:
                    self._exit_active_session("Going back to standby, sir.")
                    return

                # Execute command directly!
                self._handle_voice_command_sync(text)
                # Reset 45s activity timer so session stays open
                self._session_expires_at = time.time() + 45.0

            except sr.WaitTimeoutError:
                self.state_manager.set_state(AppState.IDLE)
                time.sleep(0.05)
            except sr.UnknownValueError:
                self.state_manager.set_state(AppState.IDLE)
                time.sleep(0.05)
            except Exception as e:
                print(f"[ActiveSession] Error: {e}")
                self.state_manager.set_state(AppState.IDLE)
                time.sleep(0.2)

    def _exit_active_session(self, farewell: str = "") -> None:
        """End active session and restart wake word listener."""
        self._session_active = False
        self.state_manager.set_state(AppState.IDLE)
        if farewell:
            self.add_activity("assistant", farewell)
            self.tts_service.speak(farewell)
            waited = 0
            while self.tts_service.is_speaking() and waited < 6:
                time.sleep(0.1)
                waited += 0.1

        time.sleep(0.3)
        if self._auto_listen_enabled and self.wake_word_service:
            if not self.wake_word_service.is_running:
                self.wake_word_service.start()
        print("[UIBridge] Returned to Standby (Wake Word Mode).")

    def on_ptt_command(self, text: str) -> None:
        """Called when PTT hotkey audio is transcribed."""
        clean = (text or "").strip()
        if not clean:
            self.state_manager.set_state(AppState.IDLE)
            return

        print(f"[UIBridge] PTT voice command received: '{clean}'")
        threading.Thread(
            target=self._handle_voice_command_sync,
            args=(clean,),
            daemon=True,
            name="PTTWorkerThread"
        ).start()

    def _handle_voice_command_sync(self, text: str) -> None:
        """Execute command, speak response, and return cleanly to IDLE."""
        clean = (text or "").strip()
        if not clean:
            self.state_manager.set_state(AppState.IDLE)
            return

        # Deduplication shield: prevent duplicate triggers within 1.8s
        now = time.time()
        if clean.lower() == self._last_command_text.lower() and (now - self._last_command_time) < 1.8:
            print(f"[UIBridge] Suppressed duplicate command within 1.8s: '{clean}'")
            return
        self._last_command_text = clean
        self._last_command_time = now

        self.add_activity("user", clean)
        self.state_manager.set_state(AppState.THINKING)

        try:
            response = self.orchestrator.handle_command(clean)
            if response:
                self.add_activity("assistant", response)
                waited = 0
                while self.tts_service.is_speaking() and waited < 30:
                    time.sleep(0.05)
                    waited += 0.05
                # Brief reverb decay buffer
                time.sleep(0.2)
        except Exception as e:
            print(f"[UIBridge] Handle command error: {e}")
            self.add_activity("system", f"Command error: {e}")
        finally:
            self.state_manager.set_state(AppState.IDLE)

    def _on_reminder_fire(self, text: str) -> None:
        """Called when a background reminder triggers."""
        with self._lock:
            self._activity.append({
                "type": "assistant",
                "text": f"Reminder: {text}",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            })
        self.tts_service.speak(f"Reminder: {text}")

    def add_activity(self, item_type: str, text: str) -> None:
        """Add an entry to the recent activity log."""
        with self._lock:
            self._activity.append({
                "type": item_type.lower(),
                "text": text,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            })
            if len(self._activity) > 100:
                self._activity = self._activity[-100:]

    # ─── Frontend Callable API ────────────────────────────────────────────────

    def get_bootstrap_data(self) -> Dict[str, Any]:
        """Called once on page load to initialize the frontend state."""
        return self.get_ui_state()

    def get_ui_state(self) -> Dict[str, Any]:
        """Polled by frontend to keep orb, status badge, and activity synced."""
        app_state = self.state_manager.get_state()
        is_speaking = self.tts_service.is_speaking()

        # Map AppState to frontend state vocabulary ("ready", "listening", "processing", "error")
        if is_speaking:
            frontend_state = "processing"
            status_label = "Speaking..."
        elif app_state == AppState.LISTENING:
            frontend_state = "listening"
            status_label = "Listening..."
        elif app_state == AppState.THINKING:
            frontend_state = "processing"
            status_label = "Thinking..."
        else:
            frontend_state = "ready"
            status_label = "Ready" if self._auto_listen_enabled else "Voice Standby Paused"

        with self._lock:
            activity_copy = list(self._activity)
            modal_copy = dict(self._active_modal) if self._active_modal else None

        return {
            "bot_name": self.bot_name,
            "status": {
                "label": status_label,
                "state": frontend_state,
            },
            "activity": activity_copy,
            "active_modal": modal_copy,
            "mic_active": (app_state == AppState.LISTENING or self._session_active),
            "auto_listen_enabled": self._auto_listen_enabled,
            "speaking_active": is_speaking,
            "command_busy": self._command_busy,
        }

    # ─── Situational Interactive Modals API ───────────────────────────────────

    def set_active_modal(self, modal_type: str, data: Dict[str, Any]) -> None:
        """Trigger an interactive modal card in the desktop frontend."""
        with self._lock:
            self._active_modal = {
                "type": modal_type,
                "data": data,
                "timestamp": time.time(),
            }
        print(f"[UIBridge] Interactive modal opened: {modal_type} ({data.get('title', '')})")

    def clear_active_modal(self) -> None:
        """Clear active modal card."""
        with self._lock:
            self._active_modal = None

    def dismiss_modal(self) -> Dict[str, Any]:
        """Dismiss active modal without saving."""
        self.clear_active_modal()
        return {"ok": True, **self.get_ui_state()}

    def save_deadline(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Save or update structured deadline entry directly to deadlines.md."""
        if not payload or not isinstance(payload, dict):
            return {"ok": False, "message": "Invalid deadline payload"}

        title = str(payload.get("title", "New Task")).strip()
        category = str(payload.get("category", "School")).strip()
        due_date = str(payload.get("due_date", "")).strip()
        due_time = str(payload.get("due_time", "23:59")).strip()
        priority = str(payload.get("priority", "Normal")).strip()

        kb_reader = getattr(self.orchestrator, "kb_reader", None)
        kb_writer = getattr(self.orchestrator, "kb_writer", None)
        context_builder = getattr(self.orchestrator, "context_builder", None)

        if not kb_reader or not kb_writer:
            return {"ok": False, "message": "KB services unavailable"}

        current = kb_reader.read("workflows/deadlines.md") or "# ⏳ Deadlines\n\n## 🎓 School Deadlines\n\n## 💼 Work / Client Deadlines\n\n## 🚀 Projects Deadlines\n\n## 👤 Personal Deadlines\n\n## ✅ Completed\n"

        entry = f"- [ ] **{title}** — Due: {due_date} {due_time} ({priority})"
        cat_header = f"## 🎓 School Deadlines" if category == "School" else (
            "## 💼 Work / Client Deadlines" if category == "Work" else (
                "## 🚀 Projects Deadlines" if category == "Projects" else "## 👤 Personal Deadlines"
            )
        )

        # Remove existing line if updating by title match
        lines = current.splitlines()
        filtered_lines = [l for l in lines if not (title.lower() in l.lower() and "- [ ]" in l)]
        current = "\n".join(filtered_lines)

        if cat_header in current:
            updated = current.replace(cat_header, f"{cat_header}\n{entry}")
        elif "## Pending" in current:
            updated = current.replace("## Pending", f"## Pending\n{entry}")
        else:
            updated = f"{current.rstrip()}\n\n{cat_header}\n{entry}\n"

        kb_writer.write("workflows/deadlines.md", updated)
        kb_writer.update_last_updated("workflows/deadlines.md")
        if context_builder:
            context_builder.invalidate_cache()

        self.clear_active_modal()
        confirmation = f"Saved {title} to your {category} deadlines for {due_date}, sir."
        self.add_activity("assistant", confirmation)
        self.tts_service.speak(confirmation)

        return {"ok": True, "message": confirmation, **self.get_ui_state()}

    def save_reminder(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Save structured reminder to ReminderService and reminders.json."""
        if not payload or not isinstance(payload, dict):
            return {"ok": False, "message": "Invalid reminder payload"}

        title = str(payload.get("title", "Reminder")).strip()
        category = str(payload.get("category", "Task")).strip()
        target_date = str(payload.get("target_date", "")).strip()
        target_time = str(payload.get("target_time", "12:00")).strip()

        import uuid
        from datetime import datetime
        try:
            target_dt = datetime.strptime(f"{target_date} {target_time}", "%Y-%m-%d %H:%M")
        except Exception:
            target_dt = datetime.now()

        if self.reminder_service:
            self.reminder_service.add(
                reminder_id=str(uuid.uuid4()),
                text=f"[{category}] {title}",
                dt=target_dt,
            )

        self.clear_active_modal()
        confirmation = f"Reminder set for {title} on {target_date} at {target_time}, sir."
        self.add_activity("assistant", confirmation)
        self.tts_service.speak(confirmation)

        return {"ok": True, "message": confirmation, **self.get_ui_state()}

    def generate_homework(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Compile and generate formatted .docx assignment via HomeworkSkill."""
        if not payload or not isinstance(payload, dict):
            return {"ok": False, "message": "Invalid homework payload"}

        subject = str(payload.get("subject", "Assignment")).strip()
        instructions = str(payload.get("instructions", "")).strip()
        format_style = str(payload.get("format", "Standard Academic")).strip()

        combined_prompt = f"Subject: {subject}\nFormat: {format_style}\nInstructions:\n{instructions}"

        skill_router = getattr(self.orchestrator, "skill_router", None)
        homework_skill = skill_router.get_skill("homework") if skill_router else None

        self.clear_active_modal()
        self.add_activity("assistant", f"Generating {subject} ({format_style})...")

        if homework_skill and hasattr(homework_skill, "create_homework"):
            threading.Thread(
                target=lambda: homework_skill.create_homework(combined_prompt),
                daemon=True,
                name="HomeworkGenThread"
            ).start()
            confirmation = f"Generating your {subject} document in {format_style} format, sir. I will open it as soon as it is ready."
        else:
            confirmation = "Homework generator service unavailable, sir."

        self.tts_service.speak(confirmation)
        return {"ok": True, "message": confirmation, **self.get_ui_state()}

    def scaffold_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate project structure and write Knowledge Base specification suite."""
        if not payload or not isinstance(payload, dict):
            return {"ok": False, "message": "Invalid project payload"}

        name = str(payload.get("name", "NewProject")).strip()
        vision = str(payload.get("vision", "")).strip()
        stack = str(payload.get("stack", "Vite + React")).strip()
        target_path = str(payload.get("target_path", "c:\\development\\Python")).strip()

        skill_router = getattr(self.orchestrator, "skill_router", None)
        project_skill = skill_router.get_skill("new_project") if skill_router else None

        self.clear_active_modal()

        if project_skill:
            project_skill._project_data["name"] = name
            project_skill._project_data["summary"] = vision
            project_skill._project_data["stack"] = stack
            cleaned_path = target_path.rstrip("/\\")
            project_skill._project_data["dev_path"] = f"{cleaned_path}\\{name}\\"
            confirmation = project_skill._finalize_project()
        else:
            confirmation = f"Project {name} setup initiated, sir."

        self.add_activity("assistant", confirmation)
        self.tts_service.speak(confirmation)
        return {"ok": True, "message": confirmation, **self.get_ui_state()}

    def send_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send or draft an email via Composio Gmail integration."""
        if not payload or not isinstance(payload, dict):
            return {"ok": False, "message": "Invalid email payload"}

        to_email = str(payload.get("to", "")).strip()
        subject = str(payload.get("subject", "No Subject")).strip()
        body = str(payload.get("body", "")).strip()

        skill_router = getattr(self.orchestrator, "skill_router", None)
        composio_skill = skill_router.get_skill("composio") if skill_router else None

        self.clear_active_modal()

        if composio_skill and hasattr(composio_skill, "composio"):
            res = composio_skill.composio.execute_action(
                "GMAIL_SEND_EMAIL",
                {"recipient_email": to_email, "subject": subject, "body": body}
            )
            if res.get("success"):
                confirmation = f"Email sent successfully to {to_email}, sir."
            else:
                confirmation = f"Could not send email: {res.get('error', 'Check connection')}"
        else:
            confirmation = f"Email to {to_email} drafted, sir."

        self.add_activity("assistant", confirmation)
        self.tts_service.speak(confirmation)
        return {"ok": True, "message": confirmation, **self.get_ui_state()}

    def render_clip(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Render and slice a video highlight via ClipSkill."""
        if not payload or not isinstance(payload, dict):
            return {"ok": False, "message": "Invalid clip payload"}

        source_path = str(payload.get("source_path", "")).strip()
        start_time = str(payload.get("start_time", "00:00")).strip()
        end_time = str(payload.get("end_time", "00:45")).strip()
        title = str(payload.get("title", "Highlight Clip")).strip()
        ratio = str(payload.get("ratio", "9:16")).strip()

        skill_router = getattr(self.orchestrator, "skill_router", None)
        clip_skill = skill_router.get_skill("clip") if skill_router else None

        self.clear_active_modal()
        layout = "vertical-blur" if ratio == "9:16" else "landscape"

        def _worker():
            if clip_skill and hasattr(clip_skill, "clip_service"):
                from pathlib import Path
                src = Path(source_path) if source_path else clip_skill.clip_service.get_latest_recording()
                if src and src.exists():
                    # Parse start / end seconds
                    def _to_secs(t):
                        try:
                            parts = t.split(":")
                            if len(parts) == 2:
                                return int(parts[0]) * 60 + float(parts[1])
                            return float(t)
                        except Exception:
                            return 0.0
                    s_sec = _to_secs(start_time)
                    e_sec = _to_secs(end_time) or (s_sec + 45.0)
                    out = clip_skill.clip_service.slice_clip(
                        source=src,
                        start_time=s_sec,
                        end_time=e_sec,
                        output_filename=title.replace(" ", "_"),
                        layout=layout,
                        is_youtube=False
                    )
                    if out and out.exists():
                        clip_skill.clip_service.open_clips_folder()

        threading.Thread(target=_worker, daemon=True, name="ClipRenderThread").start()
        confirmation = f"Rendering your clip '{title}' in {ratio} format, sir. I'll open your Clips folder once complete."
        self.add_activity("assistant", confirmation)
        self.tts_service.speak(confirmation)
        return {"ok": True, "message": confirmation, **self.get_ui_state()}

    def send_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a text command through the Orchestrator.
        Called when user submits from the Command panel input.
        """
        clean_command = (command or "").strip()
        if not clean_command:
            return {"ok": False, **self.get_ui_state()}

        self.add_activity("user", clean_command)
        self._command_busy = True
        self.state_manager.set_state(AppState.THINKING)

        try:
            response = self.orchestrator.handle_command(clean_command)
            if response:
                self.add_activity("assistant", response)
            return {
                "ok": True,
                "command": clean_command,
                "response": response,
                **self.get_ui_state(),
            }
        except Exception as e:
            error_msg = f"Command error: {e}"
            self.add_activity("system", error_msg)
            return {
                "ok": False,
                "command": clean_command,
                "response": error_msg,
                **self.get_ui_state(),
            }
        finally:
            self._command_busy = False

    def toggle_mic(self) -> Dict[str, Any]:
        """Toggle voice standby on or off."""
        self._auto_listen_enabled = not self._auto_listen_enabled

        if self._auto_listen_enabled:
            self.start_voice_standby()
            self.add_activity("system", "Voice standby enabled.")
        else:
            self.stop_voice_standby()
            self.add_activity("system", "Voice standby paused.")

        return self.get_ui_state()

    def start_voice_standby(self) -> Dict[str, Any]:
        """Start the wake word listener."""
        self._auto_listen_enabled = True
        if not self._session_active and self.wake_word_service and not self.wake_word_service.is_running:
            self.wake_word_service.start()
        return self.get_ui_state()

    def stop_voice_standby(self) -> Dict[str, Any]:
        """Pause voice listening and stop active conversations."""
        self._auto_listen_enabled = False
        self._session_active = False
        if self.wake_word_service and self.wake_word_service.is_running:
            self.wake_word_service.stop()
        self.state_manager.set_state(AppState.IDLE)
        return self.get_ui_state()

    # ─── Settings API ─────────────────────────────────────────────────────────

    def get_settings(self) -> Dict[str, Any]:
        """Fetch current configuration values for the settings panel."""
        return {
            "app_name": self.settings.get_app_name(),
            "wake_word": self.settings.get_wake_word(),
            "ptt_hotkey": self.settings.get("ptt_hotkey", "right alt"),
            "gemini_api_key": self.settings.get_gemini_api_key(),
            "groq_api_key": self.settings.get_groq_api_key(),
            "elevenlabs_api_key": self.settings.get_elevenlabs_api_key(),
            "elevenlabs_voice_id": self.settings.get_elevenlabs_voice_id(),
            "tts_fallback": self.settings.get("tts_fallback", True),
            "kb_path": self.settings.get_kb_path(),
            "debug": self.settings.is_debug(),
        }

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Save settings to SQLite + .env and hot-apply to running services."""
        if not new_settings or not isinstance(new_settings, dict):
            return {"ok": False, "message": "Invalid settings payload"}

        try:
            from pathlib import Path

            # 1. Update App Name
            if "app_name" in new_settings and new_settings["app_name"]:
                app_name = str(new_settings["app_name"]).strip()
                self.settings.set_env("APP_NAME", app_name)
                self.bot_name = app_name

            # 2. Update Wake Word
            if "wake_word" in new_settings and new_settings["wake_word"]:
                wake_word = str(new_settings["wake_word"]).strip()
                self.settings.set_env("WAKE_WORD", wake_word)
                if self.wake_word_service:
                    self.wake_word_service.wake_word = wake_word

            # 3. Update PTT Hotkey
            if "ptt_hotkey" in new_settings and new_settings["ptt_hotkey"]:
                hotkey = str(new_settings["ptt_hotkey"]).strip().lower()
                self.settings.set("ptt_hotkey", hotkey)
                if self.ptt_service:
                    self.ptt_service.hotkey = hotkey

            # 4. Update Gemini / Groq Keys
            if "gemini_api_key" in new_settings:
                gemini_key = str(new_settings["gemini_api_key"]).strip()
                self.settings.set_env("GEMINI_API_KEY", gemini_key)
                if self.orchestrator.gemini_service:
                    self.orchestrator.gemini_service.update_api_key(gemini_key, provider="gemini")

            if "groq_api_key" in new_settings:
                groq_key = str(new_settings["groq_api_key"]).strip()
                self.settings.set_env("GROQ_API_KEY", groq_key)
                if self.orchestrator.gemini_service:
                    self.orchestrator.gemini_service.update_api_key(groq_key, provider="groq")

            # 5. Update ElevenLabs Voice Credentials
            if "elevenlabs_api_key" in new_settings or "elevenlabs_voice_id" in new_settings:
                api_key = str(new_settings.get("elevenlabs_api_key", self.settings.get_elevenlabs_api_key())).strip()
                voice_id = str(new_settings.get("elevenlabs_voice_id", self.settings.get_elevenlabs_voice_id())).strip()
                self.settings.set_env("ELEVENLABS_API_KEY", api_key)
                self.settings.set_env("ELEVENLABS_VOICE_ID", voice_id)
                if self.tts_service:
                    self.tts_service.update_credentials(api_key=api_key, voice_id=voice_id)

            if "tts_fallback" in new_settings:
                fallback_bool = bool(new_settings["tts_fallback"])
                self.settings.set("tts_fallback", fallback_bool)
                if self.tts_service:
                    self.tts_service.use_fallback = fallback_bool

            # 6. Update Knowledge Base Path
            if "kb_path" in new_settings and new_settings["kb_path"]:
                kb_path = str(new_settings["kb_path"]).strip()
                self.settings.set_env("KB_PATH", kb_path)
                kb_reader = getattr(self.orchestrator, "kb_reader", None)
                if kb_reader:
                    kb_reader.kb_path = Path(kb_path)
                kb_writer = getattr(self.orchestrator, "kb_writer", None)
                if kb_writer:
                    kb_writer.kb_path = Path(kb_path)

            self.add_activity("system", "Settings saved and applied successfully.")
            return {"ok": True, "settings": self.get_settings()}

        except Exception as e:
            print(f"[UIBridge] Error saving settings: {e}")
            return {"ok": False, "message": str(e)}
