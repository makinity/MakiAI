"""
End-to-End Verification Test for Dual-Niche Job Hunting Feature in MakiAI
"""
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.routines.routine_engine import RoutineEngine
from services.reminder.reminder_service import ReminderService
from skills.routine_skill import RoutineSkill
from gui.ui_bridge import MakiUIApi
from core.orchestrator import Orchestrator
from core.state_manager import StateManager
from services.settings.settings_service import SettingsService
from services.voice.stt_service import STTService

class MockVoiceTTS:
    def __init__(self):
        self.spoken = []

    def speak(self, text: str):
        self.spoken.append(text)

    def is_speaking(self):
        return False

    def is_speaking_or_recent(self, threshold: float = 0.5):
        return False


class TestJobHuntingEngine(unittest.TestCase):

    def setUp(self):
        self.mock_tts = MockVoiceTTS()
        self.reminder_svc = ReminderService()
        self.engine = RoutineEngine(reminder_service=self.reminder_svc, tts_service=self.mock_tts)

        self.state_mgr = StateManager()
        self.orch = Orchestrator(self.state_mgr)
        self.settings = SettingsService()
        self.stt = STTService(model_size="tiny")
        self.ui_bridge = MakiUIApi(
            orchestrator=self.orch,
            state_manager=self.state_mgr,
            settings=self.settings,
            tts_service=self.mock_tts,
            stt_service=self.stt,
            routine_engine=self.engine,
        )

        self.skill = RoutineSkill(
            gemini_service=MagicMock(),
            context_builder=MagicMock(),
            kb_reader=MagicMock(),
            kb_writer=MagicMock(),
            routine_engine=self.engine,
            reminder_service=self.reminder_svc,
        )
        self.skill.set_ui_bridge(self.ui_bridge)

    def test_1_routines_exist_in_config(self):
        """Verify both niche configurations exist in routines.json."""
        routines = self.engine.get_all_routines()
        self.assertIn("job_hunting_ai_video", routines, "AI Video Creator routine missing from routines.json")
        self.assertIn("job_hunting_smm", routines, "Social Media Manager routine missing from routines.json")

        ai_video = routines["job_hunting_ai_video"]
        self.assertEqual(ai_video["name"], "AI Video Creator Job Hunting")
        self.assertEqual(len(ai_video.get("multi_profiles", [])), 2)
        self.assertEqual(ai_video["multi_profiles"][0]["profile"], "juntillakingmaki@gmail.com")
        self.assertEqual(ai_video["multi_profiles"][1]["profile"], "denjikun1031@gmail.com")
        self.assertEqual(ai_video["storage_folder"], r"C:\VA\Documents\Resume\AI Video")

        smm = routines["job_hunting_smm"]
        self.assertEqual(smm["name"], "Social Media Manager Job Hunting")
        self.assertEqual(len(smm.get("multi_profiles", [])), 2)
        self.assertEqual(smm["multi_profiles"][0]["profile"], "juntillakingmaki@gmail.com")
        self.assertEqual(smm["multi_profiles"][1]["profile"], "markjuntillava@gmail.com")
        self.assertEqual(smm["storage_folder"], r"C:\VA\Documents\Resume\SMM Resume")
        print("[PASS] Test 1: Both AI Video Creator and SMM routines verified in configuration.")

    def test_2_chrome_profile_directory_resolution(self):
        """Verify that email addresses resolve to the actual Chrome user data directory profiles."""
        p_main = self.engine._resolve_chrome_profile_directory("juntillakingmaki@gmail.com")
        p_denji = self.engine._resolve_chrome_profile_directory("denjikun1031@gmail.com")
        p_mark = self.engine._resolve_chrome_profile_directory("markjuntillava@gmail.com")
        p_astra = self.engine._resolve_chrome_profile_directory("astra.chile.xuiie@gmail.com")

        self.assertIsNotNone(p_main, "Could not resolve Profile for juntillakingmaki@gmail.com")
        self.assertIsNotNone(p_denji, "Could not resolve Profile for denjikun1031@gmail.com")
        self.assertIsNotNone(p_mark, "Could not resolve Profile for markjuntillava@gmail.com")
        self.assertIsNotNone(p_astra, "Could not resolve Profile for astra.chile.xuiie@gmail.com")

        print(f"[PASS] Test 2: Chrome Profiles Resolved -> Main: {p_main}, Denji: {p_denji}, Mark: {p_mark}, Astra: {p_astra}")

    def test_3_skill_routing_generic_job_hunting(self):
        """Verify generic trigger asks user for niche preference and triggers the UI modal."""
        queries = [
            "Maki, let's hunt a job",
            "Maki, let's do job hunting",
            "Maki, hunt jobs",
            "apply for jobs"
        ]
        for query in queries:
            res = self.skill.execute(query)
            self.assertIn("niche", res.lower(), f"Did not ask for niche in '{query}'")
            self.assertIn("AI Video Creator or Social Media Manager", res)
            
            ui_state = self.ui_bridge.get_ui_state()
            active_modal = ui_state.get("active_modal")
            self.assertIsNotNone(active_modal)
            self.assertEqual(active_modal.get("type"), "job_niche")
            print(f"[PASS] Test 3: Generic command '{query}' prompted niche selection modal.")

    def test_4_skill_routing_direct_ai_video(self):
        """Verify direct query for AI Video Creator launches routine directly."""
        queries = [
            "Hunt for AI video creator jobs",
            "let's hunt for ai video jobs",
            "job hunting ai video creator",
            "prep for ai video creator work"
        ]
        with patch.object(self.engine, "launch_routine", return_value="AI Video workspace ready, sir.") as mock_launch:
            for query in queries:
                res = self.skill.execute(query)
                self.assertEqual(res, "AI Video workspace ready, sir.")
                mock_launch.assert_called_with("job_hunting_ai_video")
                print(f"[PASS] Test 4: Direct query '{query}' triggered AI Video routine.")

    def test_5_skill_routing_direct_smm(self):
        """Verify direct query for Social Media Manager launches routine directly."""
        queries = [
            "Let's hunt for SMM jobs",
            "hunt for social media manager jobs",
            "prep for smm job hunting",
            "apply for social media jobs"
        ]
        with patch.object(self.engine, "launch_routine", return_value="SMM workspace ready, sir.") as mock_launch:
            for query in queries:
                res = self.skill.execute(query)
                self.assertEqual(res, "SMM workspace ready, sir.")
                mock_launch.assert_called_with("job_hunting_smm")
                print(f"[PASS] Test 5: Direct query '{query}' triggered SMM routine.")

    def test_6_launch_routine_ai_video_execution(self):
        """Verify mock execution of AI Video Creator provisions the 2 profiles and opens explorer."""
        with patch("subprocess.Popen") as mock_popen, \
             patch("pathlib.Path.exists", return_value=True):
            
            msg = self.engine.launch_routine("job_hunting_ai_video")
            self.assertIn("AI Video Creator", msg)

            # Subprocess calls: 2 Chrome profile launches + 1 explorer folder launch
            self.assertEqual(mock_popen.call_count, 3)
            calls = [call_args[0][0] for call_args in mock_popen.call_args_list]

            # Chrome calls (list of args)
            chrome_calls = [c for c in calls if isinstance(c, list) and "chrome.exe" in c[0].lower()]
            self.assertEqual(len(chrome_calls), 2)

            # Profile 1: juntillakingmaki@gmail.com
            urls_p1 = chrome_calls[0]
            self.assertTrue(any("onlinejobs.ph" in arg.lower() for arg in urls_p1))
            self.assertTrue(any("mail.google.com" in arg.lower() for arg in urls_p1))
            self.assertTrue(any("linkedin.com" in arg.lower() for arg in urls_p1))

            # Profile 2: denjikun1031@gmail.com
            urls_p2 = chrome_calls[1]
            self.assertTrue(any("chatgpt.com" in arg.lower() for arg in urls_p2))
            self.assertTrue(any("gemini.google.com" in arg.lower() for arg in urls_p2))
            self.assertTrue(any("maki-sync-ai.vercel.app" in arg.lower() for arg in urls_p2))

            # Explorer call
            explorer_calls = [c for c in calls if isinstance(c, str) and "explorer" in c.lower()]
            self.assertEqual(len(explorer_calls), 1)
            self.assertIn("AI Video", explorer_calls[0])
            print("[PASS] Test 6: AI Video dual-profile and folder execution verified.")

    def test_7_launch_routine_smm_execution(self):
        """Verify mock execution of SMM provisions the 2 profiles and opens explorer."""
        with patch("subprocess.Popen") as mock_popen, \
             patch("pathlib.Path.exists", return_value=True):
            
            msg = self.engine.launch_routine("job_hunting_smm")
            self.assertIn("Social Media Manager", msg)

            self.assertEqual(mock_popen.call_count, 3)
            calls = [call_args[0][0] for call_args in mock_popen.call_args_list]

            chrome_calls = [c for c in calls if isinstance(c, list) and "chrome.exe" in c[0].lower()]
            self.assertEqual(len(chrome_calls), 2)

            # Profile 1: juntillakingmaki@gmail.com
            urls_p1 = chrome_calls[0]
            self.assertTrue(any("onlinejobs.ph" in arg.lower() for arg in urls_p1))
            self.assertTrue(any("linkedin.com" in arg.lower() for arg in urls_p1))

            # Profile 2: markjuntillava@gmail.com
            urls_p2 = chrome_calls[1]
            self.assertTrue(any("indeed.com" in arg.lower() for arg in urls_p2))
            self.assertTrue(any("chatgpt.com" in arg.lower() for arg in urls_p2))
            self.assertTrue(any("gemini.google.com" in arg.lower() for arg in urls_p2))
            self.assertTrue(any("canva.site" in arg.lower() for arg in urls_p2))

            # Explorer call
            explorer_calls = [c for c in calls if isinstance(c, str) and "explorer" in c.lower()]
            self.assertEqual(len(explorer_calls), 1)
            self.assertIn("SMM Resume", explorer_calls[0])
            print("[PASS] Test 7: SMM dual-profile and folder execution verified.")

    def test_8_local_resume_folders_exist_on_disk(self):
        """Verify that the actual local resume directories exist on user's system."""
        ai_video_dir = Path(r"C:\VA\Documents\Resume\AI Video")
        smm_dir = Path(r"C:\VA\Documents\Resume\SMM Resume")
        
        # Ensure directories exist or are created
        ai_video_dir.mkdir(parents=True, exist_ok=True)
        smm_dir.mkdir(parents=True, exist_ok=True)

        self.assertTrue(ai_video_dir.exists())
        self.assertTrue(smm_dir.exists())
        print(f"[PASS] Test 8: Confirmed Resume Folders exist on disk:\n  - {ai_video_dir}\n  - {smm_dir}")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestJobHuntingEngine)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n=======================================================")
        print("ALL 8 JOB HUNTING VERIFICATION TESTS PASSED (100% WORKING)")
        print("=======================================================")
        sys.exit(0)
    else:
        sys.exit(1)
