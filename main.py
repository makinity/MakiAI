"""
MakiAI — Entry Point
Launches the modern MakiAI Desktop Interface powered by PyWebView (native WebView2)
and connects the interactive particle orb, glowing sci-fi HUD, hideable command/status/activity
panels, voice engine, Push-to-Talk, and AI skills.

Run with:
    python main.py
"""

import sys
import os
import threading
import traceback
from typing import Optional

# Suppress HuggingFace symlink warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler — log crashes without closing the app."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("\n[MakiAI] Unhandled exception:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)


def handle_thread_exception(args):
    """Catch exceptions in background threads."""
    if args.exc_type == SystemExit:
        return
    print(f"\n[MakiAI] Thread '{args.thread.name}' crashed:")
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)


def bootstrap_maki_services():
    """Initialize and wire all core MakiAI services."""
    from core.orchestrator import Orchestrator
    from core.state_manager import StateManager, AppState
    from services.auth.auth_service import AuthService
    from services.settings.settings_service import SettingsService
    from services.voice.wake_word_service import WakeWordService
    from services.voice.stt_service import STTService
    from services.voice.tts_service import TTSService
    from services.voice.ptt_service import PushToTalkService
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
    from gui.ui_bridge import MakiUIApi

    # Storage initialization
    try:
        from services.storage.maki_sync import initialize_storage
        initialize_storage()
    except Exception as e:
        print(f"[MakiAI] Storage init warning: {e}")

    # 1. State & Settings
    settings = SettingsService()
    auth = AuthService()
    state_manager = StateManager()
    orchestrator = Orchestrator(state_manager)

    # 2. KB & Context
    kb_reader = KBReader(kb_path=settings.get_kb_path())
    kb_writer = KBWriter(kb_path=settings.get_kb_path())
    kb_index = KBIndex(kb_reader=kb_reader)
    memory_service = MemoryService()

    # 3. AI & Router
    gemini = GeminiService(
        api_key=settings.get_gemini_api_key(),
        groq_api_key=settings.get_groq_api_key(),
    )
    context_builder = ContextBuilder(
        kb_reader=kb_reader,
        kb_index=kb_index,
    )
    context_builder.invalidate_cache()

    # Auto-index hook
    _orig_write = kb_writer.write
    _orig_append = kb_writer.append
    def _write_and_invalidate(p, c):
        r = _orig_write(p, c)
        kb_index.index_file(p, c)
        context_builder.invalidate_cache()
        return r
    def _append_and_invalidate(p, c):
        r = _orig_append(p, c)
        updated_c = kb_reader.read(p)
        kb_index.index_file(p, updated_c)
        context_builder.invalidate_cache()
        return r
    kb_writer.write = _write_and_invalidate
    kb_writer.append = _append_and_invalidate

    # 4. Skills
    skill_deps = (gemini, context_builder, kb_reader, kb_writer)
    reminder_service = ReminderService()
    skills = {
        "goodmorning": GoodMorningSkill(*skill_deps),
        "goodnight": GoodNightSkill(*skill_deps),
        "hello": HelloSkill(*skill_deps),
        "deadline": DeadlineSkill(*skill_deps),
        "reminder": ReminderSkill(*skill_deps, reminder_service=reminder_service),
        "memory": MemorySkill(*skill_deps),
        "new_project": NewProjectSkill(*skill_deps),
        "homework": HomeworkSkill(*skill_deps),
    }
    skill_router = SkillRouter(skills)

    # 5. Voice Services
    tts_service = TTSService(
        elevenlabs_api_key=settings.get_elevenlabs_api_key(),
        voice_id=settings.get_elevenlabs_voice_id(),
        on_speaking_start=lambda: state_manager.set_state(AppState.SPEAKING),
        on_speaking_end=lambda: state_manager.set_state(AppState.IDLE),
        on_error=lambda msg: print(f"[TTS] {msg}"),
        use_fallback=settings.get("tts_fallback", True),
    )
    stt_service = STTService(
        model_size="tiny",
        on_transcription_update=lambda r: None,
        on_error=lambda msg: print(f"[STT] {msg}"),
    )
    wake_word_service = WakeWordService(
        access_key=settings.get_porcupine_access_key(),
        on_wake=lambda: state_manager.set_state(AppState.LISTENING),
        on_error=lambda msg: print(f"[WakeWord] {msg}"),
        sensitivity=0.6,
    )

    ptt_hotkey = settings.get("ptt_hotkey", "right alt")
    ptt_service = PushToTalkService(
        hotkey=ptt_hotkey,
        on_ptt_start=lambda: state_manager.set_state(AppState.LISTENING),
        on_ptt_end=lambda: state_manager.set_state(AppState.THINKING),
    )

    # 6. Wire Orchestrator
    orchestrator.set_services({
        "gemini": gemini,
        "tts": tts_service,
        "skill_router": skill_router,
        "kb_reader": kb_reader,
        "kb_writer": kb_writer,
        "context_builder": context_builder,
    })

    # Start reminder background service
    try:
        reminder_service.start()
    except Exception as e:
        print(f"[MakiAI] Reminder service start error: {e}")

    # 7. UI Bridge API
    ui_api = MakiUIApi(
        orchestrator=orchestrator,
        state_manager=state_manager,
        settings=settings,
        tts_service=tts_service,
        stt_service=stt_service,
        wake_word_service=wake_word_service,
        ptt_service=ptt_service,
        reminder_service=reminder_service,
    )

    return ui_api, settings


def main() -> None:
    """Bootstrap and launch the MakiAI desktop application."""
    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception

    # Support legacy PyQt6 if explicitly requested via flag or env
    if "--pyqt" in sys.argv or os.environ.get("MAKI_USE_PYQT") == "1":
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from gui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("MakiAI")
        app.setApplicationVersion("1.0.0")
        app.setFont(QFont("Segoe UI", 10))

        window = MainWindow()
        window.resize(1100, 700)
        window.show()
        sys.exit(app.exec())
        return

    # Modern Web UI with PyWebView
    import webview

    ui_api, settings = bootstrap_maki_services()
    app_dir = os.path.dirname(os.path.abspath(__file__))
    ui_index_path = os.path.join(app_dir, "gui", "web_ui", "index.html")

    window_title = settings.get_app_name()
    print(f"[MakiAI] Launching {window_title} Desktop Interface...")

    window = webview.create_window(
        title=window_title,
        url=ui_index_path,
        js_api=ui_api,
        width=1280,
        height=820,
        min_size=(980, 680),
        resizable=True,
        background_color="#040715",
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
