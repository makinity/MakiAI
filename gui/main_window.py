"""
MakiAI — Main Window
Root PyQt6 application window.
Manages page navigation between LoginPage and MainPage using QStackedWidget.
Bootstraps all core services on startup.
Starts voice engine background threads on login.
"""

import threading

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QApplication
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QIcon

from core.orchestrator import Orchestrator
from core.state_manager import StateManager, AppState
from services.auth.auth_service import AuthService
from services.settings.settings_service import SettingsService
from services.voice.wake_word_service import WakeWordService
from services.voice.stt_service import STTService, TranscriptionResult
from services.voice.tts_service import TTSService
from services.ai.gemini_service import GeminiService
from services.ai.context_builder import ContextBuilder
from services.kb.kb_reader import KBReader
from services.kb.kb_writer import KBWriter
from services.kb.kb_index import KBIndex
from services.kb.skill_router import SkillRouter
from services.reminder.reminder_service import ReminderService
from services.memory.memory_service import MemoryService
from skills.goodmorning_skill import GoodMorningSkill
from skills.goodnight_skill import GoodNightSkill
from skills.hello_skill import HelloSkill
from skills.deadline_skill import DeadlineSkill
from skills.reminder_skill import ReminderSkill
from skills.memory_skill import MemorySkill
from skills.new_project_skill import NewProjectSkill
from skills.homework_skill import HomeworkSkill
from gui.pages.LoginPage import LoginPage
from gui.pages.MainPage import MainPage
from gui.pages.SettingsPage import SettingsPage


# Page indices in the QStackedWidget
PAGE_LOGIN    = 0
PAGE_MAIN     = 1
PAGE_SETTINGS = 2


class MainWindow(QMainWindow):
    """
    The root application window for MakiAI.

    Holds all pages in a QStackedWidget and controls which page is visible.
    On startup, checks auth state and navigates accordingly:
      - First launch or logged out → LoginPage
      - Session active → MainPage directly
    """

    def __init__(self):
        super().__init__()

        # ── Bootstrap services ────────────────────────────────────────────────
        self.settings = SettingsService()
        self.auth = AuthService()
        self.state_manager = StateManager()
        self.orchestrator = Orchestrator(self.state_manager)

        # Conversation mode flag
        self._conversation_active = False

        # ── KB services ───────────────────────────────────────────────────────
        self.kb_reader = KBReader(kb_path=self.settings.get_kb_path())
        self.kb_writer = KBWriter(kb_path=self.settings.get_kb_path())
        self.kb_index = KBIndex(kb_reader=self.kb_reader)

        # ── Reminder & Memory services ────────────────────────────────────────
        self.memory_service = MemoryService()
        self.reminder_service = ReminderService(
            on_fire=self._on_reminder_fire
        )

        # ── AI services ───────────────────────────────────────────────────────
        self.gemini = GeminiService(
            api_key=self.settings.get_gemini_api_key(),
            groq_api_key=self.settings.get_groq_api_key(),
        )
        self.context_builder = ContextBuilder(
            kb_reader=self.kb_reader,
            kb_index=self.kb_index,
        )
        self.context_builder.invalidate_cache()

        # Auto-update index and invalidate context cache whenever KB is written
        _orig_write = self.kb_writer.write
        _orig_append = self.kb_writer.append
        _ctx = self.context_builder
        _idx = self.kb_index
        def _write_and_invalidate(p, c):
            r = _orig_write(p, c)
            _idx.index_file(p, c)
            _ctx.invalidate_cache()
            return r
        def _append_and_invalidate(p, c):
            r = _orig_append(p, c)
            updated_c = self.kb_reader.read(p)
            _idx.index_file(p, updated_c)
            _ctx.invalidate_cache()
            return r
        self.kb_writer.write = _write_and_invalidate
        self.kb_writer.append = _append_and_invalidate

        # ── Skills ────────────────────────────────────────────────────────────
        skill_deps = (self.gemini, self.context_builder, self.kb_reader, self.kb_writer)
        skills = {
            "goodmorning":  GoodMorningSkill(*skill_deps),
            "goodnight":    GoodNightSkill(*skill_deps),
            "hello":        HelloSkill(*skill_deps),
            "deadline":     DeadlineSkill(*skill_deps),
            "reminder":     ReminderSkill(*skill_deps, reminder_service=self.reminder_service),
            "memory":       MemorySkill(*skill_deps),
            "new_project":  NewProjectSkill(*skill_deps),
            "homework":     HomeworkSkill(*skill_deps),
        }
        self.skill_router = SkillRouter(skills)

        # ── Voice services ────────────────────────────────────────────────────
        self.tts_service = TTSService(
            elevenlabs_api_key=self.settings.get_elevenlabs_api_key(),
            voice_id=self.settings.get_elevenlabs_voice_id(),
            on_speaking_start=lambda: self.state_manager.set_state(AppState.SPEAKING),
            on_speaking_end=lambda: self.state_manager.set_state(AppState.IDLE),
            on_error=lambda msg: print(f"[TTS] {msg}"),
            use_fallback=self.settings.get("tts_fallback", True),
        )
        self.stt_service = STTService(
            model_size="tiny",
            on_transcription_update=self._on_transcription_update,
            on_error=lambda msg: print(f"[STT] {msg}"),
        )
        self.wake_word_service = WakeWordService(
            access_key=self.settings.get_porcupine_access_key(),
            on_wake=self._on_wake_word_detected,
            on_error=lambda msg: print(f"[WakeWord] {msg}"),
            sensitivity=0.6,
        )

        # ── Wire Orchestrator ─────────────────────────────────────────────────
        self.orchestrator.set_services({
            "gemini":           self.gemini,
            "tts":              self.tts_service,
            "skill_router":     self.skill_router,
            "kb_reader":        self.kb_reader,
            "context_builder":  self.context_builder,
        })

        # ── Window configuration ──────────────────────────────────────────────
        self.setWindowTitle(self.settings.get_app_name())
        self.setMinimumSize(QSize(900, 650))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._apply_base_style()

        # ── Page stack ────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage(self.auth, self.settings, self._on_login_success)
        self.main_page = MainPage(
            self.orchestrator,
            self.state_manager,
            self.settings,
            self.auth,
            self._on_logout,
            self._on_open_settings,
        )
        self.settings_page = SettingsPage(
            settings=self.settings,
            on_back=self._on_settings_back,
            on_logout=self._on_logout,
        )
        self.settings_page.settings_saved.connect(self._on_settings_saved)

        self.stack.addWidget(self.login_page)    # index 0
        self.stack.addWidget(self.main_page)     # index 1
        self.stack.addWidget(self.settings_page) # index 2

        # ── Initial navigation ────────────────────────────────────────────────
        self._navigate_on_startup()

    # ─── Navigation ──────────────────────────────────────────────────────────

    def _navigate_on_startup(self) -> None:
        """
        Decide which page to show on launch.
        Skip login if session is still active.
        """
        if self.auth.is_logged_in():
            print("[MainWindow] Session active — auto-login.")
            self.stack.setCurrentIndex(PAGE_MAIN)
            self.main_page.on_enter()
            self.reminder_service.start()
            self._start_voice_engine()  # ← start voice on auto-login too
        else:
            print("[MainWindow] No active session — showing login.")
            self.stack.setCurrentIndex(PAGE_LOGIN)

    def _on_login_success(self) -> None:
        """Called by LoginPage when the user successfully logs in."""
        print("[MainWindow] Login success — navigating to MainPage.")
        self.stack.setCurrentIndex(PAGE_MAIN)
        self.main_page.on_enter()
        self.reminder_service.start()
        self._start_voice_engine()

    def _on_logout(self) -> None:
        """Called by MainPage or SettingsPage when the user logs out."""
        print("[MainWindow] Logout — returning to LoginPage.")
        self._stop_voice_engine()
        self.reminder_service.stop()
        self.auth.logout()
        self.login_page.reset()
        self.stack.setCurrentIndex(PAGE_LOGIN)

    def _on_open_settings(self) -> None:
        """Navigate to SettingsPage."""
        self.settings_page._load_current_values()
        self.stack.setCurrentIndex(PAGE_SETTINGS)

    def _on_settings_back(self) -> None:
        """Return to MainPage from SettingsPage."""
        self.stack.setCurrentIndex(PAGE_MAIN)

    def _on_settings_saved(self, changed: dict) -> None:
        """
        Hot-swap services when settings are saved.
        Called by SettingsPage.settings_saved signal.
        """
        print(f"[MainWindow] Settings saved — updating services.")

        # Update Groq/Gemini API keys
        if "GROQ_API_KEY" in changed or "GEMINI_API_KEY" in changed:
            self.gemini.update_api_key(
                new_key=self.settings.get_gemini_api_key(),
                provider="gemini"
            )
            if changed.get("GROQ_API_KEY"):
                self.gemini.update_api_key(
                    new_key=self.settings.get_groq_api_key(),
                    provider="groq"
                )

        # Update ElevenLabs credentials
        if "ELEVENLABS_API_KEY" in changed or "ELEVENLABS_VOICE_ID" in changed:
            self.tts_service.update_credentials(
                api_key=self.settings.get_elevenlabs_api_key(),
                voice_id=self.settings.get_elevenlabs_voice_id(),
            )

        # Update wake word — restart voice engine
        if "WAKE_WORD" in changed:
            self._stop_voice_engine()
            import time
            time.sleep(0.5)
            self._start_voice_engine()

    def _on_reminder_fire(self, text: str) -> None:
        """
        Called by ReminderService when a reminder triggers.
        Shows in chat log and speaks aloud.
        """
        print(f"[MainWindow] Reminder fired: '{text}'")
        self.main_page.add_message_signal.emit("maki", f"Reminder: {text}")
        self.tts_service.speak(text)

    # ─── Voice Engine ─────────────────────────────────────────────────────────

    def _start_voice_engine(self) -> None:
        """Start wake word listener after short delay."""
        def delayed_start():
            import time
            time.sleep(2)
            self.wake_word_service = WakeWordService(
                wake_word=self.settings.get_wake_word(),
                on_wake=self._on_wake_word_detected,
                on_wake_with_command=self._on_wake_with_command,
                on_error=lambda msg: print(f"[WakeWord] {msg}"),
            )
            self.wake_word_service.start()

        threading.Thread(target=delayed_start, daemon=True, name="VoiceStartThread").start()

    def _stop_voice_engine(self) -> None:
        """Stop all voice services."""
        self._conversation_active = False
        if self.wake_word_service and self.wake_word_service.is_running:
            self.wake_word_service.stop()

    def _on_wake_word_detected(self) -> None:
        """Wake word heard alone — greet and enter conversation mode."""
        if not self.state_manager.is_idle():
            return
        if self.wake_word_service and self.wake_word_service.is_running:
            self.wake_word_service.stop()
        print("[MainWindow] Wake word — entering conversation mode.")
        self._enter_conversation_mode()

    def _on_wake_with_command(self, command: str) -> None:
        """Wake word + command — handle command and enter conversation mode."""
        if not self.state_manager.is_idle():
            return
        if self.wake_word_service and self.wake_word_service.is_running:
            self.wake_word_service.stop()
        print(f"[MainWindow] Wake+command: '{command}'")
        self._enter_conversation_mode(initial_command=command)

    def _enter_conversation_mode(self, initial_command: str = "") -> None:
        """Enter conversational mode — runs in background thread."""
        self._conversation_active = True
        threading.Thread(
            target=self._run_conversation,
            args=(initial_command,),
            daemon=True,
            name="ConversationThread"
        ).start()

    def _run_conversation(self, initial_command: str = "") -> None:
        """Full conversation session in background thread."""
        import time
        import speech_recognition as sr

        # Wake response — wait for it to fully finish before listening
        if initial_command:
            self._handle_voice_command_sync(initial_command)
        else:
            print("[MainWindow] Running HelloSkill on wake.")
            self._handle_voice_command_sync("hello")

        # Conversation loop
        INACTIVITY_TIMEOUT = 120  # 2 minutes of silence before sleeping
        last_activity = time.time()
        print("[ConversationLoop] Active — listening continuously.")

        while self._conversation_active:
            if time.time() - last_activity > INACTIVITY_TIMEOUT:
                self._exit_conversation_mode("Going back to sleep. Say Hey Maki to wake me.")
                return

            recognizer = sr.Recognizer()
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 1.0
            recognizer.energy_threshold = 300

            try:
                self.state_manager.set_state(AppState.LISTENING)
                self.main_page.update_transcription_signal.emit("Listening...")

                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=8, phrase_time_limit=12)

                self.state_manager.set_state(AppState.THINKING)
                text = recognizer.recognize_google(audio, language="en-US").strip()
                print(f"[ConversationLoop] Heard: '{text}'")
                self.main_page.update_transcription_signal.emit(text)
                last_activity = time.time()

                if any(kw in text.lower() for kw in ["go to sleep", "sleep", "goodbye", "stop listening"]):
                    self._exit_conversation_mode("Alright, going to sleep.")
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

    def _conversation_loop(self) -> None:
        """Legacy — kept for compatibility."""
        pass

    def _handle_voice_command_sync(self, text: str) -> None:
        """Handle command and block until TTS finishes."""
        import time
        self.main_page.add_message_signal.emit("user", text)
        response = self.orchestrator.handle_command(text)
        print(f"[MainWindow] Response: '{response[:80] if response else 'EMPTY'}'")
        if response:
            self.main_page.add_message_signal.emit("maki", response)
            time.sleep(0.8)
            waited = 0
            while self.tts_service.is_speaking() and waited < 30:
                time.sleep(0.1)
                waited += 0.1
            time.sleep(0.8)
        else:
            print("[MainWindow] WARNING: Empty response from orchestrator")

    def _exit_conversation_mode(self, farewell: str = "") -> None:
        """Exit conversation mode and restart wake word listener."""
        import time
        self._conversation_active = False
        self.state_manager.set_state(AppState.IDLE)
        if farewell:
            self.main_page.add_message_signal.emit("maki", farewell)
            self.tts_service.speak(farewell)
        time.sleep(2)
        self._start_voice_engine()
        print("[MainWindow] Returned to wake word mode.")

    def _handle_voice_command(self, text: str) -> None:
        """Route a voice command — alias for sync version."""
        self._handle_voice_command_sync(text)

    def _on_transcription_update(self, text: str) -> None:
        if self.stack.currentIndex() == PAGE_MAIN:
            self.main_page.update_transcription_signal.emit(text)

    # ─── Window close ────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        """Clean up background threads before closing the app."""
        self._stop_voice_engine()
        self.reminder_service.stop()
        event.accept()

    # ─── Window dragging (frameless) ─────────────────────────────────────────

    def mousePressEvent(self, event):
        """Allow dragging the frameless window."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Handle window drag movement."""
        if hasattr(self, "_drag_pos") and event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    # ─── Styling ─────────────────────────────────────────────────────────────

    def _apply_base_style(self) -> None:
        """Apply MakiSync sleek dark theme to the main window."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0f1a;
                border: 1px solid rgba(140, 171, 214, 0.15);
                border-radius: 12px;
            }
            QWidget {
                background-color: #0a0f1a;
                color: #f1f5f9;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, sans-serif;
                font-size: 13px;
            }
            QStackedWidget {
                background-color: #0a0f1a;
            }
            QScrollBar:vertical {
                background: #0a0f1a;
                width: 6px;
                border-radius: 3px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3b82f6;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
