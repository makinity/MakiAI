"""
MakiAI — App Launcher
Opens desktop applications and websites by name.

Handles voice commands like:
  "open VS Code"
  "open Spotify"
  "open YouTube"
  "open Chrome"
  "open File Explorer"
"""

import os
import subprocess
import webbrowser
from pathlib import Path


# Common app name → executable mapping for Windows
APP_MAP = {
    # Browsers
    "chrome":           "chrome.exe",
    "google chrome":    "chrome.exe",
    "firefox":          "firefox.exe",
    "edge":             "msedge.exe",
    "microsoft edge":   "msedge.exe",
    "brave":            "brave.exe",

    # Dev tools
    "vs code":          "code",
    "vscode":           "code",
    "visual studio code": "code",
    "visual studio":    "devenv.exe",
    "git bash":         "git-bash.exe",
    "terminal":         "wt.exe",
    "windows terminal": "wt.exe",
    "powershell":       "powershell.exe",
    "cmd":              "cmd.exe",
    "notepad":          "notepad.exe",
    "notepad++":        "notepad++.exe",

    # Productivity
    "word":             "WINWORD.EXE",
    "excel":            "EXCEL.EXE",
    "powerpoint":       "POWERPNT.EXE",
    "outlook":          "OUTLOOK.EXE",
    "teams":            "ms-teams.exe",
    "microsoft teams":  "ms-teams.exe",
    "onenote":          "ONENOTE.EXE",

    # Media
    "spotify":          "spotify.exe",
    "vlc":              "vlc.exe",
    "media player":     "wmplayer.exe",

    # System
    "file explorer":    "explorer.exe",
    "explorer":         "explorer.exe",
    "task manager":     "taskmgr.exe",
    "control panel":    "control.exe",
    "settings":         "ms-settings:",
    "calculator":       "calc.exe",
    "paint":            "mspaint.exe",
    "snipping tool":    "SnippingTool.exe",
    "camera":           "microsoft.windows.camera:",

    # Communication
    "discord":          "discord.exe",
    "telegram":         "telegram.exe",
    "zoom":             "zoom.exe",
    "slack":            "slack.exe",
    "whatsapp":         "whatsapp.exe",
}

# Common website name → URL mapping
WEBSITE_MAP = {
    "youtube":          "https://youtube.com",
    "google":           "https://google.com",
    "github":           "https://github.com",
    "gmail":            "https://mail.google.com",
    "google drive":     "https://drive.google.com",
    "google docs":      "https://docs.google.com",
    "google sheets":    "https://sheets.google.com",
    "notion":           "https://notion.so",
    "reddit":           "https://reddit.com",
    "twitter":          "https://twitter.com",
    "x":                "https://x.com",
    "facebook":         "https://facebook.com",
    "instagram":        "https://instagram.com",
    "linkedin":         "https://linkedin.com",
    "spotify":          "https://open.spotify.com",
    "netflix":          "https://netflix.com",
    "stackoverflow":    "https://stackoverflow.com",
    "stack overflow":   "https://stackoverflow.com",
    "chatgpt":          "https://chatgpt.com",
    "gemini":           "https://gemini.google.com",
    "claude":           "https://claude.ai",
    "groq":             "https://console.groq.com",
}


class AppLauncher:
    """
    Launches desktop applications and opens browser URLs by name.

    Usage:
        launcher = AppLauncher()
        result = launcher.open("VS Code")
        result = launcher.open("YouTube")
        result = launcher.open_url("https://github.com")
    """

    def is_known(self, name: str) -> bool:
        """Check if name matches a known desktop application or website."""
        n = name.strip().lower()
        if n in APP_MAP or any(k in n or n in k for k in APP_MAP):
            return True
        if n in WEBSITE_MAP or any(k in n or n in k for k in WEBSITE_MAP):
            return True
        return False

    def open(self, app_name: str) -> str:
        """
        Open a desktop app or website by name.
        Tries desktop app first, falls back to browser URL if not found.

        Args:
            app_name: Natural language app or website name.

        Returns:
            Response string describing what was opened.
        """
        name_lower = app_name.strip().lower()

        name_clean = name_lower.strip().rstrip(".,;!?")

        # Try desktop app first
        result = self._open_app(name_clean)
        if result:
            return result

        # Try as a website
        result = self._open_website(name_clean)
        if result:
            return result

        # Try as a raw URL — strictly require http:// or valid domain without spaces
        is_url = bool(
            name_clean.startswith("http://")
            or name_clean.startswith("https://")
            or ("." in name_clean and " " not in name_clean and re.search(r"\.[a-zA-Z]{2,}(/.*)?$", name_clean))
        )
        if is_url:
            return self.open_url(name_clean)

        return f"I couldn't find an app or website called '{app_name}'. Try saying the full name."

    def open_url(self, url: str) -> str:
        """
        Open a URL directly in the default browser.

        Args:
            url: Full URL string.

        Returns:
            Response string.
        """
        try:
            if not url.startswith("http"):
                url = "https://" + url
            webbrowser.open(url)
            return f"Opening {url}."
        except Exception as e:
            print(f"[AppLauncher] URL open error: {e}")
            return f"I couldn't open that URL."

    # ─── Internal ────────────────────────────────────────────────────────────

    def _open_app(self, name_lower: str) -> str | None:
        """Try to launch a desktop app by mapped name or direct search."""
        # Check app map
        executable = APP_MAP.get(name_lower)

        # Fuzzy match — check if any key is contained in the input
        if not executable:
            for key, exe in APP_MAP.items():
                if key in name_lower or name_lower in key:
                    executable = exe
                    break

        if not executable:
            return None

        try:
            # Handle ms- protocol URIs (e.g. ms-settings:)
            if executable.endswith(":") or executable.startswith("ms-"):
                os.startfile(executable)
            else:
                subprocess.Popen(
                    executable,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            display_name = name_lower.title()
            return f"Opening {display_name}."
        except Exception as e:
            print(f"[AppLauncher] App launch error for '{executable}': {e}")
            return None

    def _open_website(self, name_lower: str) -> str | None:
        """Try to open a website by mapped name with Chrome profile awareness."""
        # 1. Check Chrome profile launcher first
        try:
            from services.browser.chrome_profile_launcher import ChromeProfileLauncher, SITE_PROFILE_MAP
            for key, config in SITE_PROFILE_MAP.items():
                if key in name_lower or any(alias in name_lower for alias in config["aliases"]):
                    return ChromeProfileLauncher().launch_site_in_profile(key)
        except Exception as e:
            print(f"[AppLauncher] ChromeProfileLauncher check error: {e}")

        # 2. Check general WEBSITE_MAP
        url = WEBSITE_MAP.get(name_lower)

        # Fuzzy match
        if not url:
            for key, site_url in WEBSITE_MAP.items():
                if key in name_lower or name_lower in key:
                    url = site_url
                    break

        if not url:
            return None

        try:
            webbrowser.open(url)
            return f"Opening {name_lower.title()} in your browser."
        except Exception as e:
            print(f"[AppLauncher] Website open error: {e}")
            return None
