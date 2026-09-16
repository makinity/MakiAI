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

        return {
            "bot_name": self.bot_name,
            "status": {
                "label": status_label,
                "state": frontend_state,
            },
            "activity": activity_copy,
            "mic_active": (app_state == AppState.LISTENING or self._session_active),
            "auto_listen_enabled": self._auto_listen_enabled,
            "speaking_active": is_speaking,
            "command_busy": self._command_busy,
        }

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
