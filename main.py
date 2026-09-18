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


def ensure_user_environment_initialized():
    """Ensure data files, default templates, and directories exist on first boot."""
    import json
    from pathlib import Path

    project_root = Path(__file__).resolve().parent
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize data/memory.json if missing
    mem_file = data_dir / "memory.json"
    if not mem_file.exists():
        try:
            mem_file.write_text(json.dumps({"memories": [], "learned_facts": []}, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Init] Memory init warning: {e}")

    # 2. Initialize data/reminders.json if missing
    rem_file = data_dir / "reminders.json"
    if not rem_file.exists():
        try:
            rem_file.write_text(json.dumps({"reminders": []}, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Init] Reminders init warning: {e}")

    # 3. Initialize data/command_log.json if missing
    cmd_file = data_dir / "command_log.json"
    if not cmd_file.exists():
        try:
            cmd_file.write_text(json.dumps([], indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Init] Command log init warning: {e}")

    # 4. Initialize config/routines.json if missing
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    routines_file = config_dir / "routines.json"
    routines_example = config_dir / "routines.example.json"
    if not routines_file.exists() and routines_example.exists():
        try:
            routines_file.write_text(routines_example.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"[Init] Initialized config/routines.json from template.")
        except Exception as e:
            print(f"[Init] Routines init warning: {e}")

    # 5. Initialize training.md if missing
    training_file = project_root / "training.md"
    training_example = project_root / "training.example.md"
    if not training_file.exists() and training_example.exists():
        try:
            training_file.write_text(training_example.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"[Init] Initialized training.md from template.")
        except Exception as e:
            print(f"[Init] Training log init warning: {e}")


def bootstrap_maki_services():
    """Initialize and wire all core MakiAI services."""
    # First-boot environment initialization
    ensure_user_environment_initialized()

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
    from services.skills.skill_registry import SkillRegistry
    from services.reminder.reminder_service import ReminderService
    from services.memory.memory_service import MemoryService
    from services.cloud.composio_service import ComposioService
    from services.routines.routine_engine import RoutineEngine
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

    # 2. AI & KB Services
    gemini = GeminiService(
        api_key=settings.get_gemini_api_key(),
        groq_api_key=settings.get_groq_api_key(),
    )
    kb_path = settings.get_kb_path()
    kb_reader = KBReader(kb_path)
    kb_writer = KBWriter(kb_path)
    kb_index = KBIndex(kb_reader=kb_reader)
    context_builder = ContextBuilder(kb_reader, kb_index=kb_index)
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

    # 4. Skills & Routine Engine
    reminder_service = ReminderService()
    composio_service = ComposioService()

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
        tts_service=tts_service,
    )

    ptt_hotkey = settings.get("ptt_hotkey", "right alt")
    ptt_service = PushToTalkService(
        hotkey=ptt_hotkey,
        on_ptt_start=lambda: state_manager.set_state(AppState.LISTENING),
        on_ptt_end=lambda: state_manager.set_state(AppState.THINKING),
        on_empty=lambda: state_manager.set_state(AppState.IDLE),
    )

    # 6. Routine Engine (Workspace Provisioning & Background Scheduling)
    routine_engine = RoutineEngine(
        kb_reader=kb_reader,
        reminder_service=reminder_service,
        tts_service=tts_service,
    )

    # Dynamic Skills Discovery
    skill_registry = SkillRegistry({
        "gemini": gemini,
        "context_builder": context_builder,
        "kb_reader": kb_reader,
        "kb_writer": kb_writer,
        "reminder_service": reminder_service,
        "composio_service": composio_service,
        "routine_engine": routine_engine,
    })
    skill_registry.discover_and_load()
    skill_router = SkillRouter(skill_registry)
    skill_registry.start_hot_reloader(on_reload_callback=skill_router.reload)

    # 7. Wire Orchestrator
    orchestrator.set_services({
        "gemini": gemini,
        "tts": tts_service,
        "skill_router": skill_router,
        "kb_reader": kb_reader,
        "kb_writer": kb_writer,
        "context_builder": context_builder,
    })

    # Start reminder and routine background services
    try:
        reminder_service.start()
    except Exception as e:
        print(f"[MakiAI] Reminder service start error: {e}")

    try:
        routine_engine.start()
    except Exception as e:
        print(f"[MakiAI] Routine engine start error: {e}")

    # 8. UI Bridge API
    ui_api = MakiUIApi(
        orchestrator=orchestrator,
        state_manager=state_manager,
        settings=settings,
        tts_service=tts_service,
        stt_service=stt_service,
        wake_word_service=wake_word_service,
        ptt_service=ptt_service,
        reminder_service=reminder_service,
        routine_engine=routine_engine,
    )

    # Connect UI Bridge to all interactive skills
    for skill_name, skill_inst in skill_registry.get_all_skills().items():
        if hasattr(skill_inst, "set_ui_bridge"):
            skill_inst.set_ui_bridge(ui_api)

    # 8. Telegram Mobile Remote Bridge (24/7 Phone Access)
    try:
        from services.remote.telegram_service import TelegramRemoteService
        telegram_service = TelegramRemoteService(
            settings_service=settings,
            orchestrator=orchestrator,
            state_manager=state_manager,
            tts_service=tts_service,
            skill_router=skill_router,
        )
        telegram_service.start()
        if routine_engine:
            routine_engine.set_telegram_service(telegram_service)
    except Exception as e:
        print(f"[MakiAI] Telegram service init error: {e}")

    # 9. Discord Remote Voice & Messaging Bridge
    try:
        from services.remote.discord_service import DiscordRemoteService
        discord_service = DiscordRemoteService(
            settings_service=settings,
            orchestrator=orchestrator,
            state_manager=state_manager,
            tts_service=tts_service,
            skill_router=skill_router,
        )
        discord_service.start()
        if routine_engine:
            routine_engine.set_discord_service(discord_service)
    except Exception as e:
        print(f"[MakiAI] Discord service init error: {e}")

    # 10. Mobile Web Phone VoIP Bridge (WebRTC / WebSocket HD Audio Calling)
    try:
        if settings.is_phone_bridge_enabled():
            from services.remote.phone_call_service import PhoneCallService
            phone_call_service = PhoneCallService(
                settings_service=settings,
                orchestrator=orchestrator,
                state_manager=state_manager,
                tts_service=tts_service,
                stt_service=stt_service,
                skill_router=skill_router,
                port=settings.get_phone_bridge_port(),
            )
            phone_call_service.start()
    except Exception as e:
        print(f"[MakiAI] Mobile Phone bridge init error: {e}")

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
        background_color="#060402",
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
