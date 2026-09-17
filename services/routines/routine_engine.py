"""
MakiAI — Autonomous Routine & Workspace Engine
Monitors schedule, upcoming classes, client work blocks, and interviews.
Proactively prepares browser profiles, SaaS dashboards, documents, and hardware
15 to 30 minutes before events begin.
"""

import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from services.storage.maki_sync import MAKI_SYNC_ROOT

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "routines.json"
_LOCK = threading.Lock()


class RoutineEngine:
    """
    Autonomous background daemon for workspace provisioning and proactive routines.
    """

    def __init__(
        self,
        kb_reader=None,
        reminder_service=None,
        tts_service=None,
        app_launcher=None,
        config_path: Path = CONFIG_PATH,
    ):
        self.kb_reader = kb_reader
        self.reminder_service = reminder_service
        self.tts_service = tts_service
        self.app_launcher = app_launcher
        self.config_path = config_path

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._triggered_today: set[str] = set()
        self._last_date_checked: str = ""

        self._load_config()

    def _load_config(self) -> dict:
        """Load routines configuration from disk."""
        with _LOCK:
            if not self.config_path.exists():
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                return {"settings": {}, "routines": {}}
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    return self.config
            except Exception as e:
                print(f"[RoutineEngine] Config load error: {e}")
                self.config = {"settings": {}, "routines": {}}
                return self.config

    def save_config(self) -> bool:
        """Persist routines configuration to disk."""
        with _LOCK:
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"[RoutineEngine] Config save error: {e}")
                return False

    def start(self) -> None:
        """Start the proactive background monitoring daemon."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._daemon_loop,
            daemon=True,
            name="RoutineEngineDaemon"
        )
        self._thread.start()
        print(f"[RoutineEngine] Autonomous Workspace Routine daemon started (monitoring {len(self.config.get('routines', {}))} routines).")

    def stop(self) -> None:
        """Stop background daemon."""
        self._running = False

    # ─── Proactive Daemon Loop ───────────────────────────────────────────────

    def _daemon_loop(self) -> None:
        """Periodically evaluate upcoming events against current time."""
        while self._running:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")

                # Reset trigger tracking on new day
                if today_str != self._last_date_checked:
                    self._triggered_today.clear()
                    self._last_date_checked = today_str

                self._check_upcoming_routines(now)

            except Exception as e:
                print(f"[RoutineEngine] Daemon loop error: {e}")

            time.sleep(30)  # Check every 30 seconds

    def _check_upcoming_routines(self, now: datetime) -> None:
        """Evaluate both configured routines and ReminderService interviews."""
        routines = self.config.get("routines", {})
        current_day = now.strftime("%A")
        today_ymd = now.strftime("%Y-%m-%d")

        for r_id, r_data in routines.items():
            trigger_key = f"{today_ymd}_{r_id}"
            if trigger_key in self._triggered_today:
                continue

            # Check matching days or specific date
            scheduled_days = r_data.get("days", [])
            scheduled_date = r_data.get("date")

            is_today = False
            if scheduled_date and scheduled_date == today_ymd:
                is_today = True
            elif scheduled_days and current_day in scheduled_days:
                is_today = True

            if not is_today:
                continue

            # Check lead time
            time_str = r_data.get("schedule_time", "")
            if not time_str:
                continue

            try:
                sched_h, sched_m = map(int, time_str.split(":"))
                event_dt = now.replace(hour=sched_h, minute=sched_m, second=0, microsecond=0)
                lead_min = r_data.get("lead_time_minutes", 15)
                prep_dt = event_dt - timedelta(minutes=lead_min)

                # Check if current time is within [prep_dt, event_dt]
                if prep_dt <= now < event_dt:
                    print(f"[RoutineEngine] Proactively triggering routine '{r_data.get('name', r_id)}' (T-{lead_min}m)...")
                    self._triggered_today.add(trigger_key)
                    self.launch_routine(r_id, is_proactive=True)

            except Exception as ex:
                print(f"[RoutineEngine] Error checking routine '{r_id}': {ex}")

    # ─── Execution & Workspace Provisioning ──────────────────────────────────

    def launch_routine(self, routine_id: str, is_proactive: bool = False) -> str:
        """
        Execute workspace provisioning for a routine:
          - Launch URLs in specified Chrome profile
          - Open local directories in MakiSync Storage
          - Launch native desktop apps
          - Deliver spoken voice briefing with smart scheduling reasoning
        """
        r_data = self.config.get("routines", {}).get(routine_id)
        if not r_data:
            return f"Routine '{routine_id}' not found, sir."

        name = r_data.get("name", routine_id)
        category = r_data.get("category", "")
        profile = r_data.get("chrome_profile", "Default")
        links = r_data.get("links", [])
        apps = r_data.get("apps", [])
        storage_folder = r_data.get("storage_folder", "")
        voice_msg = r_data.get("voice_announcement", f"Workspace for {name} is ready, sir.")

        # Check timing context when triggered on-demand manually
        now = datetime.now()
        current_day = now.strftime("%A")
        sched_time_str = r_data.get("schedule_time", "")
        sched_days = r_data.get("days", [])

        is_on_schedule = False
        if sched_time_str:
            try:
                sh, sm = map(int, sched_time_str.split(":"))
                sched_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
                lead_min = r_data.get("lead_time_minutes", 15)
                # On schedule if within [sched_dt - lead_min, sched_dt + 45m] on the scheduled day
                if (not sched_days or current_day in sched_days) and (sched_dt - timedelta(minutes=lead_min) <= now <= sched_dt + timedelta(minutes=45)):
                    is_on_schedule = True
            except Exception:
                pass

        if not is_proactive and not is_on_schedule:
            # User is requesting on-demand early or outside scheduled time
            formatted_time = ""
            if sched_time_str:
                try:
                    formatted_time = datetime.strptime(sched_time_str, "%H:%M").strftime("%I:%M %p").lstrip("0")
                except Exception:
                    formatted_time = sched_time_str

            if "bat-600" in name.lower() or "bat" in name.lower():
                days_label = "Mondays and Wednesdays" if "Monday" in sched_days else "your scheduled class day"
                voice_msg = f"It's not quite time for your BAT-600 class yet, sir, which is set for {days_label} at {formatted_time}. But since you'd like to get an early start, I've prepared your Google Meet, Google Classroom, and Facebook tabs for you."
            elif "icc-600" in name.lower() or "icc" in name.lower():
                days_label = "Tuesdays and Thursdays" if "Tuesday" in sched_days else "your scheduled class day"
                voice_msg = f"It's not your ICC-600 class time yet, sir, which is set for {days_label} at {formatted_time}. But since you want to jump in now, I've loaded your Google Meet, Classroom, Facebook, and coding environment."
            elif "ai video" in name.lower() or "ai_video" in routine_id:
                voice_msg = f"Launching your AI Video Creator job-hunting workspace, sir. I've opened your dual Chrome profiles with OnlineJobs.ph, LinkedIn, ChatGPT, your portfolio, and your AI Video resume folder."
            elif "smm" in name.lower() or "social media" in name.lower():
                voice_msg = f"Launching your Social Media Manager job-hunting workspace, sir. I've opened your dual Chrome profiles with OnlineJobs.ph, LinkedIn, Indeed, ChatGPT, your Canva portfolio, and SMM resume folder."
            elif category == "Work" or "content" in name.lower() or "marketing" in name.lower():
                voice_msg = f"Your client content upload block isn't scheduled until {formatted_time}, sir. But since you want to get ahead of your tasks, I've opened your client Chrome profile with Metricool and all your social dashboards."
            elif category == "Coding" or "coding" in name.lower() or "dev" in name.lower():
                voice_msg = f"Starting your focused coding session ahead of time, sir. I've launched VS Code and loaded your development environment."
            elif category == "Interview" or "interview" in name.lower():
                voice_msg = f"It's not your scheduled interview time yet, sir, but I have prepared your meeting platform and documents so you can review ahead of time."
            else:
                voice_msg = f"It is ahead of your scheduled time for {name}, sir, but since you want to start now, I've prepared your workspace."

        # 1. Launch Browser Links in Profile(s)
        multi_profiles = r_data.get("multi_profiles", [])
        if multi_profiles:
            for mp in multi_profiles:
                p_name = mp.get("profile", "Default")
                p_links = mp.get("links", [])
                if p_links:
                    self._launch_chrome_tabs(p_links, p_name)
        elif links:
            self._launch_chrome_tabs(links, profile)

        # 2. Open Local Storage Folder (Supports Absolute Path or MakiSync relative)
        if storage_folder:
            if os.path.isabs(storage_folder):
                target_p = Path(storage_folder)
            else:
                target_p = MAKI_SYNC_ROOT / storage_folder
            if target_p.exists():
                try:
                    subprocess.Popen(f'explorer "{target_p}"')
                except Exception as e:
                    print(f"[RoutineEngine] Folder open error: {e}")

        # 3. Launch native apps (code, discord, zoom)
        for app in apps:
            self._launch_app(app)

        # 4. Spoken Voice Announcement
        if self.tts_service and voice_msg:
            try:
                self.tts_service.speak(voice_msg)
            except Exception as e:
                print(f"[RoutineEngine] Voice announcement error: {e}")

        return voice_msg

    def _resolve_chrome_profile_directory(self, profile_input: str) -> str:
        """Resolve Chrome profile folder from email, profile name, or directory name."""
        if not profile_input or profile_input == "Default":
            return "Default"
        if profile_input.startswith("Profile "):
            return profile_input

        try:
            local_state_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data" / "Local State"
            if local_state_path.exists():
                with open(local_state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                info_cache = data.get("profile", {}).get("info_cache", {})
                target = profile_input.strip().lower()
                for prof_dir, p_info in info_cache.items():
                    user_email = str(p_info.get("user_name", "")).strip().lower()
                    user_name = str(p_info.get("name", "")).strip().lower()
                    if target in (user_email, user_name, prof_dir.lower()):
                        return prof_dir
        except Exception as e:
            print(f"[RoutineEngine] Profile resolution warning: {e}")

        return profile_input

    def _launch_chrome_tabs(self, links: List[str], profile: str = "Default") -> None:
        """Launch URL tabs inside specific Chrome profile."""
        if not links:
            return

        resolved_profile = self._resolve_chrome_profile_directory(profile)

        chrome_candidates = [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google\\Chrome\\Application\\chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google\\Chrome\\Application\\chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google\\Chrome\\Application\\chrome.exe",
        ]

        chrome_exe = None
        for cand in chrome_candidates:
            if cand.exists():
                chrome_exe = cand
                break

        if chrome_exe:
            profile_arg = f"--profile-directory={resolved_profile}" if resolved_profile else ""
            cmd = [str(chrome_exe)]
            if profile_arg:
                cmd.append(profile_arg)
            cmd.extend(links)
            try:
                subprocess.Popen(cmd)
                print(f"[RoutineEngine] Launched {len(links)} links in Chrome ({resolved_profile}).")
            except Exception as e:
                print(f"[RoutineEngine] Chrome launch error: {e}")
        else:
            # Fallback to default browser
            import webbrowser
            for link in links:
                webbrowser.open(link)

    def _launch_app(self, app_name: str) -> None:
        """Launch standard desktop apps."""
        lowered = app_name.lower().strip()
        try:
            if lowered in ("code", "vscode", "vs code"):
                subprocess.Popen("code", shell=True)
            elif lowered == "discord":
                discord_cand = Path(os.environ.get("LOCALAPPDATA", "")) / "Discord\\Update.exe"
                if discord_cand.exists():
                    subprocess.Popen([str(discord_cand), "--processStart", "Discord.exe"])
                else:
                    subprocess.Popen("discord", shell=True)
            elif lowered in ("zoom", "zoom.exe"):
                subprocess.Popen("zoom", shell=True)
            elif lowered in ("obs", "obs64"):
                subprocess.Popen("obs64", shell=True)
            elif self.app_launcher:
                self.app_launcher.open(app_name)
        except Exception as e:
            print(f"[RoutineEngine] App launch warning for {app_name}: {e}")

    # ─── Public Management & Modal Synchronization ───────────────────────────

    def save_interview_or_routine(self, payload: Dict[str, Any]) -> dict:
        """
        Save a routine or interview created via Interactive Modal or Voice.
        Persists to config/routines.json and ReminderService.
        """
        title = payload.get("title", "").strip() or "Scheduled Session"
        category = payload.get("category", "Interview")
        date_str = payload.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
        time_str = payload.get("time", "").strip() or "09:00"
        link = payload.get("link", "").strip()
        profile = payload.get("chrome_profile", "Default")
        lead_time = int(payload.get("lead_time_minutes", 15))
        platform = payload.get("platform", "Google Meet")

        r_id = f"custom_{re.sub(r'[^a-zA-Z0-9_]', '_', title.lower())}_{date_str.replace('-', '')}"

        # Resolve links
        links = []
        if link:
            links.append(link)
        elif platform == "Google Meet":
            links.append("https://meet.google.com")
        elif platform == "Zoom":
            links.append("https://zoom.us")

        voice_announcement = (
            f"Sir, reminder for {title} scheduled at {time_str}. "
            f"I have opened your {platform} workspace."
        )

        routine_entry = {
            "id": r_id,
            "name": title,
            "category": category,
            "lead_time_minutes": lead_time,
            "date": date_str,
            "schedule_time": time_str,
            "chrome_profile": profile,
            "links": links,
            "apps": [],
            "storage_folder": "Notes",
            "voice_announcement": voice_announcement,
        }

        with _LOCK:
            self.config.setdefault("routines", {})[r_id] = routine_entry

        self.save_config()

        # Also register in ReminderService if available
        if self.reminder_service:
            try:
                import uuid
                sched_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                if sched_dt > datetime.now():
                    self.reminder_service.add(
                        text=f"[{category}] {title} ({platform})",
                        dt=sched_dt,
                        reminder_id=str(uuid.uuid4()),
                    )
            except Exception as e:
                print(f"[RoutineEngine] ReminderService sync warning: {e}")

        confirmation_msg = f"Saved {title} ({category}) for {date_str} at {time_str} with {platform} workspace, sir."
        print(f"[RoutineEngine] {confirmation_msg}")
        return {"ok": True, "routine_id": r_id, "message": confirmation_msg, "entry": routine_entry}

    def update_routine_link(self, routine_id: str, new_link: str) -> bool:
        """Update a specific meeting or class link in config/routines.json."""
        with _LOCK:
            routines = self.config.get("routines", {})
            if routine_id in routines:
                routines[routine_id]["links"] = [new_link]
                self.save_config()
                print(f"[RoutineEngine] Updated link for '{routine_id}' to {new_link}")
                return True
        return False

    def get_all_routines(self) -> dict:
        """Return all active routines."""
        return self.config.get("routines", {})
