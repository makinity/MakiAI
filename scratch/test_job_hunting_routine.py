"""
Test Dual-Niche Job Hunting Workspaces, Multi-Profile Engine, and Interactive Niche Modal.
"""

import sys
from pathlib import Path
from datetime import datetime

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


def test_job_hunting():
    print("\n--- TEST 1: Load Niche Routines from Config ---")
    mock_tts = MockVoiceTTS()
    reminder_svc = ReminderService()
    engine = RoutineEngine(reminder_service=reminder_svc, tts_service=mock_tts)

    routines = engine.get_all_routines()
    assert "job_hunting_ai_video" in routines, "Missing job_hunting_ai_video"
    assert "job_hunting_smm" in routines, "Missing job_hunting_smm"

    ai_video = routines["job_hunting_ai_video"]
    assert len(ai_video.get("multi_profiles", [])) == 2
    assert "AI Video" in ai_video.get("storage_folder", "")
    print("[PASS] Both AI Video Creator and SMM dual-profile presets loaded successfully.")

    print("\n--- TEST 2: General Job Hunting Trigger -> Niche Selection Prompt ---")
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

    skill = RoutineSkill(
        gemini_service=None,
        context_builder=None,
        kb_reader=None,
        kb_writer=None,
        routine_engine=engine,
        reminder_service=reminder_svc,
    )
    skill.set_ui_bridge(ui_bridge)

    resp_general = skill.execute("Maki, lets hunt a job")
    print(f"General Hunt Response: {resp_general}")
    active_modal = ui_bridge.get_ui_state().get("active_modal")
    print(f"Active Modal State: {active_modal}")
    assert active_modal is not None
    assert active_modal.get("type") == "job_niche"
    assert "AI Video Creator or Social Media Manager" in resp_general
    print("[PASS] General trigger prompted for niche and displayed interactive modal.")

    print("\n--- TEST 3: Direct AI Video Creator Workspace Launch ---")
    resp_ai_video = skill.execute("Hunt for AI video creator jobs")
    print(f"AI Video Response: {resp_ai_video}")
    assert "ai video" in resp_ai_video.lower()
    print("[PASS] Direct AI Video Creator command launched dual-profile workspace.")

    print("\n--- TEST 4: Direct SMM Workspace Launch ---")
    resp_smm = skill.execute("Let's hunt for SMM jobs")
    print(f"SMM Response: {resp_smm}")
    assert "social media manager" in resp_smm.lower() or "smm" in resp_smm.lower()
    print("[PASS] Direct SMM command launched dual-profile workspace.")

    print("\n==========================================")
    print(" ALL DUAL-NICHE TESTS PASSED! ")
    print("==========================================\n")


if __name__ == "__main__":
    test_job_hunting()
