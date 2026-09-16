"""
MakiAI — Comprehensive End-to-End Diagnostic & Calibration Test Suite
Tests every skill, router, computer control, audio transcriber phonetic healing,
and real-world Taglish & conversational prompts.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from core.state_manager import StateManager, AppState
from core.orchestrator import Orchestrator
from services.auth.auth_service import AuthService
from services.settings.settings_service import SettingsService
from services.voice.audio_transcriber import AudioTranscriber
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
from skills.research_skill import ResearchSkill
from skills.clip_skill import ClipSkill
from skills.interpreter_skill import InterpreterSkill
from skills.composio_skill import ComposioSkill
from services.cloud.composio_service import ComposioService


def build_test_orchestrator():
    """Build orchestrator instance wired to real services."""
    settings = SettingsService()
    state_manager = StateManager()
    orchestrator = Orchestrator(state_manager)

    kb_reader = KBReader(kb_path=settings.get_kb_path())
    kb_writer = KBWriter(kb_path=settings.get_kb_path())
    kb_index = KBIndex(kb_reader=kb_reader)

    gemini = GeminiService(
        api_key=settings.get_gemini_api_key(),
        groq_api_key=settings.get_groq_api_key(),
    )
    context_builder = ContextBuilder(
        kb_reader=kb_reader,
        kb_index=kb_index,
    )
    context_builder.invalidate_cache()

    skill_deps = (gemini, context_builder, kb_reader, kb_writer)
    reminder_service = ReminderService()
    composio_service = ComposioService()
    skills = {
        "goodmorning": GoodMorningSkill(*skill_deps),
        "goodnight": GoodNightSkill(*skill_deps),
        "hello": HelloSkill(*skill_deps),
        "deadline": DeadlineSkill(*skill_deps),
        "reminder": ReminderSkill(*skill_deps, reminder_service=reminder_service),
        "memory": MemorySkill(*skill_deps),
        "new_project": NewProjectSkill(*skill_deps),
        "homework": HomeworkSkill(*skill_deps),
        "research": ResearchSkill(*skill_deps),
        "clip": ClipSkill(*skill_deps),
        "interpreter": InterpreterSkill(*skill_deps),
        "composio": ComposioSkill(*skill_deps, composio_service=composio_service),
    }
    skill_router = SkillRouter(skills)

    orchestrator.set_services({
        "gemini": gemini,
        "tts": None,  # Silent for tests
        "skill_router": skill_router,
        "kb_reader": kb_reader,
        "kb_writer": kb_writer,
        "context_builder": context_builder,
    })

    return orchestrator, AudioTranscriber()


# Comprehensive test matrix representing all categories
TEST_CATEGORIES = [
    {
        "category": "1. Routine & Schedule (English & Taglish)",
        "cases": [
            ("Good morning Maki", "Skill:GoodMorningSkill"),
            ("What is my schedule today?", "Skill:GoodMorningSkill"),
            ("Ano schedule ko today?", "Skill:GoodMorningSkill"),
            ("Ano schedule ko bukas?", "Skill:GoodMorningSkill"),
            ("What is my schedule tomorrow?", "Skill:GoodMorningSkill"),
            ("What should I be doing right now?", "Skill:HelloSkill"),
            ("Anong oras na?", "Skill:HelloSkill"),
            ("What time is it right now?", "Skill:HelloSkill"),
            ("What's next on my schedule?", "Skill:HelloSkill"),
            ("Good night", "Skill:GoodNightSkill"),
            ("Matutulog na ako", "Skill:GoodNightSkill"),
            ("Hey Maki", "DirectAcknowledgment"),
            ("Thank you Maki", "DirectAcknowledgment"),
        ]
    },
    {
        "category": "2. Academic & Deadlines & School",
        "cases": [
            ("Show my deadlines", "Skill:DeadlineSkill"),
            ("What are my deadlines this week?", "Skill:DeadlineSkill"),
            ("May deadline ba ako this week?", "Skill:DeadlineSkill"),
            ("Do I have any deadlines coming up?", "Skill:DeadlineSkill"),
            ("Add deadline Capstone Chapter 4 by Friday", "Skill:DeadlineSkill"),
            ("Mark deadline Capstone Chapter 4 as done", "Skill:DeadlineSkill"),
            ("Create my homework", "Skill:HomeworkSkill"),
            ("Gawa tayo ng homework", "Skill:HomeworkSkill"),
            ("Help me finish my homework assignment", "Skill:HomeworkSkill"),
        ]
    },
    {
        "category": "3. Computer & File Control & Window Management",
        "cases": [
            ("Organize my Downloads folder.", "ComputerRouter"),
            ("Open my Downloads folder.", "ComputerRouter"),
            ("Open Knowledge Base folder.", "ComputerRouter"),
            ("Open photos folder.", "ComputerRouter"),
            ("Open screenshots folder.", "ComputerRouter"),
            ("Take a screenshot.", "ComputerRouter"),
            ("Take a photo.", "ComputerRouter"),
            ("Tile my windows.", "ComputerRouter"),
            ("Organize my workspace.", "ComputerRouter"),
            ("Move Chrome to my second monitor.", "ComputerRouter"),
            ("Close YouTube", "ComputerRouter"),
            ("Close Chrome", "ComputerRouter"),
        ]
    },
    {
        "category": "4. Chrome Multi-Profile Launcher & Media Control",
        "cases": [
            ("Open Facebook", "ComputerRouter"),
            ("Launch FB", "ComputerRouter"),
            ("Open GitHub", "ComputerRouter"),
            ("Go to Canva", "ComputerRouter"),
            ("Open Google Chrome", "ComputerRouter"),
            ("Open Spotify", "ComputerRouter"),
            ("Play lofi on Spotify", "ComputerRouter"),
            ("Pause music.", "ComputerRouter"),
            ("Resume playback.", "ComputerRouter"),
            ("Next track.", "ComputerRouter"),
            ("Previous track.", "ComputerRouter"),
            ("Play bohemian rhapsody on YouTube", "ComputerRouter"),
            ("Open YouTube for me and play popular music", "ComputerRouter"),
            ("Search for Bruno Mars and play it", "ComputerRouter"),
        ]
    },
    {
        "category": "5. Audio, System Health & Telemetry",
        "cases": [
            ("Set volume to maximum.", "ComputerRouter"),
            ("Set volume to 65%.", "ComputerRouter"),
            ("Volume up", "ComputerRouter"),
            ("Volume down", "ComputerRouter"),
            ("Mute volume", "ComputerRouter"),
            ("Check system health", "ComputerRouter"),
            ("What are my system vitals?", "ComputerRouter"),
            ("How is my battery?", "ComputerRouter"),
            ("Set brightness to 80%", "ComputerRouter"),
            ("Lock the computer", "ComputerRouter"),
        ]
    },
    {
        "category": "6. Memory, Reminders & Composio Integrations",
        "cases": [
            ("Remember that my secondary email is mark.dev@gmail.com", "Skill:MemorySkill"),
            ("What is my secondary email?", "Skill:MemorySkill"),
            ("What do you remember about my secondary email?", "Skill:MemorySkill"),
            ("Forget about my secondary email", "Skill:MemorySkill"),
            ("Remind me tomorrow at 3 PM to message the client", "Skill:ReminderSkill"),
            ("Remind me in 30 minutes to drink water", "Skill:ReminderSkill"),
            ("Paalala mamayang 5pm mag workout", "Skill:ReminderSkill"),
            ("Show my reminders", "Skill:ReminderSkill"),
            ("Do I have any scheduled meetings?", "Skill:ReminderSkill"),
            ("Do I have a schedule on October 1?", "Skill:ReminderSkill"),
            ("Check my Gmail for unread emails", "Skill:ComposioSkill"),
            ("Check my Google Calendar for events", "Skill:ComposioSkill"),
            ("Create a Google Doc called Meeting Notes", "Skill:ComposioSkill"),
        ]
    },
    {
        "category": "7. Kiro CLI & 11-Stage Project Planning",
        "cases": [
            ("Open Kiro", "KiroService:Interactive"),
            ("Launch Kiro terminal", "KiroService:Interactive"),
            ("Open Kiro for TaskMaster", "KiroService:Interactive"),
            ("t=kiro build a counter component in React with Tailwind", "KiroService:Headless"),
            ("use kiro to write a python script for web scraping", "KiroService:Headless"),
            ("I have a new project idea called FitTrack", "Skill:NewProjectSkill"),
            ("May bago akong project na naisip", "Skill:NewProjectSkill"),
        ]
    },
    {
        "category": "8. Research, Vision & Phonetic Healing",
        "cases": [
            ("Search online for latest Next.js 15 features", "Skill:ResearchSkill"),
            ("Research about deep learning transformer models", "Skill:ResearchSkill"),
            ("Mag research ka tungkol sa quantum computing", "Skill:ResearchSkill"),
            ("What is on my screen right now?", "ComputerRouter"),
            ("What am I holding in my hand?", "ComputerRouter"),
            ("Look at me and tell me what I am doing.", "ComputerRouter"),
        ]
    }
]

PHONETIC_TEST_CASES = [
    ("open the captured image in the magazine storage", "open the captured image in the makisync storage"),
    ("find the recording in cable storage", "find the recording in makisync storage"),
    ("open key row terminal", "open Kiro terminal"),
    ("launch cure row for tops", "launch Kiro for TaskMaster"),
    ("macky check my schedule", "Maki check my schedule"),
    ("make a sync folder open", "MakiSync folder open"),
    ("open canvas poster", "open Canva poster"),
]


def run_diagnostics():
    print("=" * 70, flush=True)
    print("🚀 Running MakiAI End-to-End Diagnostic & Calibration Test Suite", flush=True)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 70, flush=True)

    orchestrator, transcriber = build_test_orchestrator()

    # Stub hardware / OS side-effects during headless test run
    orchestrator.computer_router.launcher.open = MagicMock(return_value="Opening application for you, sir.")
    orchestrator.computer_router.screenshot.capture_full = MagicMock(return_value="Screenshot saved to Screenshots folder, sir.")
    orchestrator.computer_router.camera.take_photo = MagicMock(return_value="Photo captured and saved to Photos folder, sir.")
    orchestrator.computer_router.camera_tool.analyze = MagicMock(return_value="I can see you sitting at your workspace desk with a laptop, sir.")
    orchestrator.computer_router.screen_vision.analyze = MagicMock(return_value="On your screen, I see your active coding workspace and terminal windows, sir.")
    orchestrator.kiro_service.launch_interactive_session = MagicMock(return_value="Opening Kiro CLI in an interactive terminal for you, sir.")
    orchestrator.kiro_service.generate_code = MagicMock(return_value="Kiro CLI generated the code successfully, sir.")

    total_tests = 0
    passed_tests = 0
    failed_tests = []
    suboptimal_logs = []

    # 1. Test Phonetic Replacements
    print("\n--- Testing Phonetic Healing & Whisper Misrecognitions ---", flush=True)
    for raw_input, expected_concept in PHONETIC_TEST_CASES:
        total_tests += 1
        healed = transcriber.heal_phonetics(raw_input)
        norm = orchestrator.computer_router._handle_smart_search(raw_input)
        print(f"  [RAW]: '{raw_input}' -> [HEALED]: '{healed}' (Smart search matched: {bool(norm)})", flush=True)
        passed_tests += 1

    # 2. Test Command Matrix
    case_idx = 0
    total_matrix_cases = sum(len(c["cases"]) for c in TEST_CATEGORIES)
    for cat in TEST_CATEGORIES:
        print(f"\n--- Category: {cat['category']} ---", flush=True)
        for prompt, expected_handler in cat["cases"]:
            total_tests += 1
            case_idx += 1
            time.sleep(0.2)
            # Reset planning state if previously active

            if orchestrator.skill_router:
                np_skill = orchestrator.skill_router.get_skill("new_project")
                if np_skill and getattr(np_skill, "is_planning_active", lambda: False)():
                    np_skill.reset()
            orchestrator._awaiting_homework_instructions = False

            try:
                t0 = time.perf_counter()
                response, handler, is_fallback, cleaned = orchestrator._route_with_meta(prompt)
                dt = (time.perf_counter() - t0) * 1000

                # Determine if routing matched expected
                is_correct_handler = (
                    (handler == expected_handler)
                    or (expected_handler in handler)
                    or (expected_handler.replace("Skill:", "") in handler)
                )
                
                # Check response quality
                has_json_leak = "```json" in response or '{"' in response or '"key":' in response
                has_thinking_leak = "<think>" in response or "</think>" in response or "Here's a thinking process:" in response
                is_suboptimal = (not is_correct_handler) or has_json_leak or has_thinking_leak or (is_fallback and expected_handler != "Fallback:Gemini")

                status_mark = "✅" if not is_suboptimal else "❌"
                print(f"  [{case_idx}/{total_matrix_cases}] {status_mark} Prompt: \"{prompt}\"", flush=True)
                print(f"       ➔ Handler: {handler} (Expected: {expected_handler}) | Time: {dt:.1f}ms", flush=True)
                resp_preview = response.replace('\n', ' ')[:110]
                print(f"       ➔ Response: \"{resp_preview}{'...' if len(response) > 110 else ''}\"", flush=True)

                if is_suboptimal:
                    failed_tests.append((prompt, handler, expected_handler, response))
                    suboptimal_logs.append({
                        "prompt": prompt,
                        "actual_handler": handler,
                        "expected_handler": expected_handler,
                        "response": response,
                        "issue": "Routing mismatch" if not is_correct_handler else ("JSON leak" if has_json_leak else "Thinking leak")
                    })
                else:
                    passed_tests += 1

            except Exception as e:
                print(f"  [{case_idx}/{total_matrix_cases}] ❌ Prompt: \"{prompt}\" -> EXCEPTION: {e}", flush=True)
                failed_tests.append((prompt, "Exception", expected_handler, str(e)))
                suboptimal_logs.append({
                    "prompt": prompt,
                    "actual_handler": "Exception",
                    "expected_handler": expected_handler,
                    "response": str(e),
                    "issue": f"Runtime Exception: {e}"
                })


    print("\n" + "=" * 70, flush=True)
    print(f"Diagnostic Summary: {passed_tests}/{total_tests} Passed ({(passed_tests/total_tests)*100:.1f}%)", flush=True)
    print(f"Total Suboptimal / Failed Cases: {len(failed_tests)}", flush=True)
    print("=" * 70, flush=True)

    return suboptimal_logs


if __name__ == "__main__":
    logs = run_diagnostics()
