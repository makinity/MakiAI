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
        self._conversation_active = False

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
            )

        # Connect WakeWord callbacks if available
        if self.wake_word_service:
            self.wake_word_service.on_wake = self._on_wake_detected
            self.wake_word_service.on_wake_with_command = self._on_wake_with_command

    # ─── State Mapping ────────────────────────────────────────────────────────

    def _on_app_state_changed(self, new_state: AppState) -> None:
        """Called when Python AppState transitions."""
        pass

    # ─── Conversational Voice Engine ──────────────────────────────────────────

    def _on_wake_detected(self) -> None:
        """Wake word heard alone — greet and enter continuous conversation."""
        if not self.state_manager.is_idle():
            return
        print("[UIBridge] Wake word detected alone — entering conversation mode.")
        if self.wake_word_service and self.wake_word_service.is_running:
            self.wake_word_service.stop()
        self._enter_conversation_mode(initial_command="")

    def _on_wake_with_command(self, command: str) -> None:
        """Wake word + command in single phrase — handle command and enter conversation."""
        clean = (command or "").strip()
        if not self.state_manager.is_idle():
            return
        print(f"[UIBridge] Wake word + command detected: '{clean}'")
        if self.wake_word_service and self.wake_word_service.is_running:
            self.wake_word_service.stop()
        self._enter_conversation_mode(initial_command=clean)

    def on_ptt_command(self, text: str) -> None:
        """Called when PTT hotkey audio is transcribed."""
        clean = (text or "").strip()
        if not clean:
            self.state_manager.set_state(AppState.IDLE)
            return

        print(f"[UIBridge] PTT voice command received: '{clean}'")
        self.add_activity("user", clean)
        self.state_manager.set_state(AppState.THINKING)
        try:
            response = self.orchestrator.handle_command(clean)
            if response:
                self.add_activity("assistant", response)
        except Exception as e:
            print(f"[UIBridge] Error executing PTT command: {e}")
            self.add_activity("system", f"Voice error: {e}")

    def _enter_conversation_mode(self, initial_command: str = "") -> None:
        """Start continuous conversation listening loop."""
        self._conversation_active = True
        threading.Thread(
            target=self._run_conversation_loop,
            args=(initial_command,),
            daemon=True,
            name="ConversationLoopThread",
        ).start()

    def _run_conversation_loop(self, initial_command: str = "") -> None:
        """Continuous listening session in background thread."""
        if initial_command:
            self._handle_voice_command_sync(initial_command)
        else:
            print("[UIBridge] Running Hello greeting on wake.")
            self._handle_voice_command_sync("hello")

        INACTIVITY_TIMEOUT = 90  # 90 seconds of silence before sleeping
        last_activity = time.time()
        print("[UIBridge] Conversation loop active — listening continuously.")

        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 1.0
        recognizer.energy_threshold = 300

        while self._conversation_active and self._auto_listen_enabled:
            if time.time() - last_activity > INACTIVITY_TIMEOUT:
                self._exit_conversation_mode("Going back to standby. Say Hey Maki to wake me.")
                return

            try:
                self.state_manager.set_state(AppState.LISTENING)

                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=8, phrase_time_limit=12)

                self.state_manager.set_state(AppState.THINKING)
                text = recognizer.recognize_google(audio, language="en-US").strip()
                print(f"[ConversationLoop] Heard: '{text}'")
                last_activity = time.time()

                if any(kw in text.lower() for kw in ["go to sleep", "sleep", "goodbye", "stop listening"]):
                    self._exit_conversation_mode("Alright, going back to standby.")
                    return

                self._handle_voice_command_sync(text)

            except sr.WaitTimeoutError:
                self.state_manager.set_state(AppState.IDLE)
                time.sleep(0.3)
            except sr.UnknownValueError:
                self.state_manager.set_state(AppState.IDLE)
                time.sleep(0.2)
            except Exception as e:
                print(f"[ConversationLoop] Error: {e}")
                self.state_manager.set_state(AppState.IDLE)
                time.sleep(1)

    def _handle_voice_command_sync(self, text: str) -> None:
        """Execute command and block until TTS finishes speaking."""
        clean = (text or "").strip()
        if not clean:
            return

        self.add_activity("user", clean)
        self.state_manager.set_state(AppState.THINKING)

        try:
            response = self.orchestrator.handle_command(clean)
            if response:
                self.add_activity("assistant", response)
                time.sleep(0.5)
                waited = 0
                while self.tts_service.is_speaking() and waited < 30:
                    time.sleep(0.1)
                    waited += 0.1
                time.sleep(0.5)
        except Exception as e:
            print(f"[UIBridge] Handle command error: {e}")
            self.add_activity("system", f"Command error: {e}")

    def _exit_conversation_mode(self, farewell: str = "") -> None:
        """Exit conversation mode and restart wake word listener."""
        self._conversation_active = False
        self.state_manager.set_state(AppState.IDLE)
        if farewell:
            self.add_activity("assistant", farewell)
            self.tts_service.speak(farewell)
            waited = 0
            while self.tts_service.is_speaking() and waited < 10:
                time.sleep(0.1)
                waited += 0.1

        time.sleep(1)
        if self._auto_listen_enabled and self.wake_word_service:
            if not self.wake_word_service.is_running:
                self.wake_word_service.start()
        print("[UIBridge] Returned to wake word mode.")

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
            "mic_active": (app_state == AppState.LISTENING or self._conversation_active),
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
        if not self._conversation_active and self.wake_word_service and not self.wake_word_service.is_running:
            self.wake_word_service.start()
        return self.get_ui_state()

    def stop_voice_standby(self) -> Dict[str, Any]:
        """Pause voice listening and stop active conversations."""
        self._auto_listen_enabled = False
        self._conversation_active = False
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
                if self.orchestrator.kb_reader:
                    self.orchestrator.kb_reader.kb_path = Path(kb_path)
                if self.orchestrator.kb_writer:
                    self.orchestrator.kb_writer.kb_path = Path(kb_path)

            self.add_activity("system", "Settings saved and applied successfully.")
            return {"ok": True, "settings": self.get_settings()}

        except Exception as e:
            print(f"[UIBridge] Error saving settings: {e}")
            return {"ok": False, "message": str(e)}
