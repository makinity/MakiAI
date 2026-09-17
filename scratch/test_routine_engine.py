"""
Test script for MakiAI Routine Engine, Interactive Interview Modal, and RoutineSkill.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.routines.routine_engine import RoutineEngine
from services.reminder.reminder_service import ReminderService
from skills.routine_skill import RoutineSkill
from gui.ui_bridge import MakiUIApi
from core.orchestrator import Orchestrator
from core.state_manager import StateManager
from services.settings.settings_service import SettingsService
from services.voice.tts_service import TTSService
from services.voice.stt_service import STTService


class MockVoiceTTS:
    def __init__(self):
        self.spoken = []

    def speak(self, text: str):
        self.spoken.append(text)
        print(f"[MockTTS] Spoke: '{text}'")

    def is_speaking(self):
        return False

    def is_speaking_or_recent(self, threshold: float = 0.5):
        return False


def test_routine_engine():
    print("\n--- TEST 1: Routine Engine Configuration ---")
    mock_tts = MockVoiceTTS()
    reminder_svc = ReminderService()
    engine = RoutineEngine(reminder_service=reminder_svc, tts_service=mock_tts)

    routines = engine.get_all_routines()
    print(f"Total loaded routines: {len(routines)}")
    assert len(routines) >= 8, f"Expected at least 8 routines, got {len(routines)}"
    assert "online_class_bat600" in routines
    assert "online_class_icc600" in routines
    assert "client_content_work" in routines
    assert "interview_essence" in routines
    print("[PASS] All routine presets correctly loaded from config/routines.json.")

    print("\n--- TEST 2: Save New Interview Routine ---")
    test_payload = {
        "title": "Google Technical Interview",
        "category": "Interview",
        "date": "2026-10-15",
        "time": "14:00",
        "platform": "Google Meet",
        "link": "https://meet.google.com/abc-defg-hij",
        "chrome_profile": "Default",
        "lead_time_minutes": 30,
    }
    save_res = engine.save_interview_or_routine(test_payload)
    assert save_res.get("ok") is True
    assert "Google Technical Interview" in engine.get_all_routines()[save_res["routine_id"]]["name"]
    print(f"[PASS] Saved interview successfully: {save_res['routine_id']}")

    print("\n--- TEST 3: RoutineSkill Execution & Fast Prep Triggers ---")
    skill = RoutineSkill(
        gemini_service=None,
        context_builder=None,
        kb_reader=None,
        kb_writer=None,
        routine_engine=engine,
        reminder_service=reminder_svc,
    )

    # Class prep
    resp_class = skill.execute("prep for class")
    print(f"Prep Class Output: {resp_class}")
    assert any(k in resp_class.lower() for k in ["class", "prepared", "workspace", "meet"])

    # Client work prep
    resp_client = skill.execute("prep for client work")
    print(f"Prep Client Output: {resp_client}")
    assert any(k in resp_client.lower() for k in ["content", "metricool", "scheduled", "dashboards", "workspace"])

    # Coding prep
    resp_coding = skill.execute("prep for coding")
    print(f"Prep Coding Output: {resp_coding}")
    assert any(k in resp_coding.lower() for k in ["coding", "code", "development", "workspace", "ahead"])

    print("\n--- TEST 4: Interactive Modal Trigger via Voice Command ---")
    # Mock UI Bridge
    state_mgr = StateManager()
    orch = Orchestrator(state_mgr)
    settings = SettingsService()
    stt = STTService(model_size="tiny")
    ui_bridge = MakiUIApi(
        orchestrator=orch,
        state_manager=state_mgr,
        settings=settings,
        tts_service=mock_tts,
        stt_service=stt,
        routine_engine=engine,
    )
    skill.set_ui_bridge(ui_bridge)

    resp_modal = skill.execute("schedule interview with Acme Corp tomorrow at 3 PM")
    print(f"Schedule Interview Output: {resp_modal}")
    active_modal = ui_bridge.get_ui_state().get("active_modal")
    print(f"Active Modal State: {active_modal}")
    assert active_modal is not None
    assert active_modal.get("type") == "interview"
    assert "Acme Corp" in active_modal.get("data", {}).get("title", "")
    print("[PASS] Interactive Interview Modal triggered with pre-filled company and category.")

    print("\n--- TEST 5: Bridge save_routine() Dispatch ---")
    bridge_payload = {
        "title": "Shopee Final Round Interview",
        "category": "Interview",
        "date": "2026-10-20",
        "time": "10:00",
        "platform": "Zoom",
        "link": "https://zoom.us/j/9876543210",
        "chrome_profile": "Default",
        "lead_time_minutes": 30,
    }
    bridge_res = ui_bridge.save_routine(bridge_payload)
    assert bridge_res.get("ok") is True
    assert ui_bridge.get_ui_state().get("active_modal") is None
    print("[PASS] Bridge save_routine successfully persisted and dismissed modal.")

    print("\n==========================================")
    print(" ALL ROUTINE & INTERVIEW TESTS PASSED! ")
    print("==========================================\n")


if __name__ == "__main__":
    test_routine_engine()
