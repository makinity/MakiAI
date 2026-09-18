"""
MakiAI — Chrome Multi-Profile Site Launcher
Automatically opens specific web platforms in their dedicated Google Chrome profiles
(e.g., Personal vs Dev vs Work) rather than defaulting to whichever account was last active.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


# Central Platform -> Profile & URL Mapping
# Note: ChatGPT is intentionally omitted per instructions.
SITE_PROFILE_MAP = {
    "facebook": {
        "display_name": "Facebook",
        "url": "https://www.facebook.com",
        "profile": "juntillakingmaki@gmail.com",
        "profile_label": "main",
        "aliases": ["facebook", "fb", "my facebook", "my fb"],
    },
    "github": {
        "display_name": "GitHub",
        "url": "https://github.com",
        "profile": "Default",
        "profile_label": "development",
        "aliases": ["github", "git", "my github", "github repo", "repos"],
    },
    "linkedin": {
        "display_name": "LinkedIn",
        "url": "https://www.linkedin.com",
        "profile": "Default",
        "profile_label": "personal",
        "aliases": ["linkedin", "my linkedin", "linked in"],
    },
    "tiktok": {
        "display_name": "TikTok",
        "url": "https://www.tiktok.com",
        "profile": "Default",
        "profile_label": "personal",
        "aliases": ["tiktok", "my tiktok", "tik tok"],
    },
    "youtube": {
        "display_name": "YouTube",
        "url": "https://www.youtube.com",
        "profile": "Default",
        "profile_label": "personal",
        "aliases": ["youtube", "yt", "my youtube"],
    },
    "canva": {
        "display_name": "Canva",
        "url": "https://www.canva.com",
        "profile": "Default",
        "profile_label": "design",
        "aliases": ["canva", "my canva", "canva designs"],
    },
    "gemini": {
        "display_name": "Gemini",
        "url": "https://gemini.google.com",
        "profile": "Default",
        "profile_label": "personal",
        "aliases": ["gemini", "google gemini", "ask gemini", "gemini ai"],
    },
    "google_flow": {
        "display_name": "Google Flow",
        "url": "https://flow.google.com",
        "profile": "Default",
        "profile_label": "workspace",
        "aliases": ["google flow", "flow", "google flows", "my flow"],
    },
    "classroom": {
        "display_name": "Google Classroom",
        "url": "https://classroom.google.com",
        "profile": "Default",
        "profile_label": "school",
        "aliases": ["google classroom", "classroom", "my classroom", "google class", "my class"],
    },
}


class ChromeProfileLauncher:
    """
    Service for inspecting Chrome profile directory metadata and
    launching platforms into specific Google Chrome profiles.
    """

    def __init__(self):
        self._chrome_path: Optional[Path] = self._detect_chrome_executable()

    # ─── Chrome Executable Discovery ─────────────────────────────────────────

    def _detect_chrome_executable(self) -> Optional[Path]:
        """Dynamically locate chrome.exe across common Windows installation paths."""
        candidates = [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
        for path in candidates:
            if path.exists() and path.is_file():
                return path
        return None

    # ─── Profile Discovery & Inspection Utility ──────────────────────────────

    @staticmethod
    def get_chrome_profiles() -> List[Dict]:
        """
        Inspect Chrome's Local State JSON file and extract a clean list of
        all detected Chrome profile directories, display names, and emails.
        """
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        local_state_file = Path(local_app_data) / "Google" / "Chrome" / "User Data" / "Local State"

        profiles = []
        if not local_state_file.exists():
            return profiles

        try:
            with open(local_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            info_cache = data.get("profile", {}).get("info_cache", {})
            for prof_dir, info in info_cache.items():
                name = info.get("name", "Unnamed Profile")
                email = info.get("user_name", "") or info.get("hosted_domain", "")
                gaia_name = info.get("gaia_name", "")
                is_active = info.get("is_using_default_name", False)

                profiles.append({
                    "directory": prof_dir,
                    "name": name,
                    "email": email,
                    "gaia_name": gaia_name,
                    "shortcut_name": info.get("shortcut_name", name),
                })
        except Exception as e:
            print(f"[ChromeProfileLauncher] Error reading Local State: {e}")

        # Sort profiles: Default first, then Profile 1, Profile 2...
        def sort_key(p):
            d = p["directory"]
            if d == "Default":
                return 0
            num = "".join(filter(str.isdigit, d))
            return int(num) if num else 999

        profiles.sort(key=sort_key)
        return profiles

    def get_profile_for_email(self, email: str) -> Optional[str]:
        """Find the Chrome profile directory (e.g. 'Profile 4') for a given email."""
        for p in self.get_chrome_profiles():
            if p.get("email", "").lower() == email.lower():
                return p["directory"]
        return None

    # ─── Process Launcher ────────────────────────────────────────────────────

    def launch_site_in_profile(
        self,
        service_key: str,
        profile_override: Optional[str] = None,
        url_override: Optional[str] = None
    ) -> str:
        """
        Launch a site in its assigned Google Chrome profile asynchronously.

        Args:
            service_key: Key from SITE_PROFILE_MAP (e.g. 'facebook', 'github', 'canva').
            profile_override: Optional Chrome profile directory override (e.g. 'Profile 4').
            url_override: Optional URL override.

        Returns:
            Spoken feedback confirmation.
        """
        site_info = SITE_PROFILE_MAP.get(service_key.lower())
        if not site_info and not url_override:
            return f"I don't have a profile configuration for '{service_key}', sir."

        url = url_override or (site_info["url"] if site_info else service_key)
        target_profile = profile_override or (site_info["profile"] if site_info else "Default")
        
        # If target_profile is specified as an email address, resolve to Chrome profile directory
        if "@" in target_profile:
            resolved_dir = self.get_profile_for_email(target_profile)
            if resolved_dir:
                target_profile = resolved_dir

        display_name = site_info["display_name"] if site_info else service_key.title()
        profile_label = site_info.get("profile_label", target_profile) if site_info else target_profile

        chrome_exe = self._chrome_path or self._detect_chrome_executable()
        if not chrome_exe:
            # Fallback to default webbrowser
            import webbrowser
            webbrowser.open(url)
            return f"Opening {display_name} in your default browser."

        try:
            # Launch Chrome with specific profile asynchronously
            cmd = [
                str(chrome_exe),
                f"--profile-directory={target_profile}",
                url,
            ]
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
            print(f"[ChromeProfileLauncher] Launched: {display_name} ({url}) in profile '{target_profile}'")
            return f"Opening {display_name} in your {profile_label} profile, sir."

        except Exception as e:
            print(f"[ChromeProfileLauncher] Launch error: {e}")
            import webbrowser
            webbrowser.open(url)
            return f"Opening {display_name} in your browser."

    # ─── Intent & Voice Trigger Matching ─────────────────────────────────────

    def match_and_launch(self, text: str) -> Optional[str]:
        """
        Match natural voice phrases to configured platform profiles and launch.
        Examples:
          - "open my facebook"
          - "launch fb"
          - "go to canva"
          - "open github"
          - "check linkedin"
          - "open gemini"
          - "launch google flow"
          - "open tiktok"
          - "open youtube"
        """
        lowered = text.lower().strip()

        # Check each configured platform
        for key, config in SITE_PROFILE_MAP.items():
            for alias in config["aliases"]:
                # Matches: "open facebook", "launch facebook", "go to facebook", "show facebook", "check facebook", "open my fb", "fb"
                patterns = [
                    rf"\b(?:open|launch|start|go\s+to|check|show|view)\s+(?:my\s+)?{re.escape(alias)}\b",
                    rf"^{re.escape(alias)}$",
                ]
                for pat in patterns:
                    if re.search(pat, lowered):
                        return self.launch_site_in_profile(key)

        return None
