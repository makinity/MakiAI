"""
MakiAI — Computer Router
Detects computer control intents from voice/text commands and
routes them to the correct service (AppLauncher, FileManager,
SystemControl, MediaControl).

Called by the Orchestrator before falling through to Gemini.
"""

import re
from services.computer.app_launcher import AppLauncher
from services.computer.file_manager import FileManager
from services.computer.system_control import SystemControl
from services.media.media_control import MediaControl
from services.camera.camera_service import CameraService
from services.camera.screenshot_service import ScreenshotService


class ComputerRouter:
    """
    Intent router for all computer control commands.

    Checks input against keyword patterns and dispatches to
    the correct service method. Returns a response string or
    None if the command doesn't match any computer control intent.

    Usage:
        router = ComputerRouter()
        result = router.handle("open VS Code")
        result = router.handle("volume up")
        # Returns None if not a computer control command
    """

    def __init__(self):
        self.launcher = AppLauncher()
        self.files = FileManager()
        self.media = MediaControl()
        self.camera = CameraService()
        self.screenshot = ScreenshotService()

        # SystemControl uses pycaw — may fail on some setups
        try:
            self.system = SystemControl()
        except Exception as e:
            print(f"[ComputerRouter] SystemControl init failed: {e}")
            self.system = None

    def handle(self, text: str) -> str | None:
        """Try to handle the text as a computer control command."""
        lowered = text.lower().strip()

        # Strip common filler words that break pattern matching
        lowered = re.sub(r"^(just|please|hey maki|maki)[,\s]+", "", lowered).strip()
        lowered = re.sub(r"^(can you|could you|would you|i want you to|i need you to)\s+", "", lowered).strip()

        # Try each category in order
        result = (
            self._handle_open(lowered, text)
            or self._handle_volume(lowered)
            or self._handle_system(lowered)
            or self._handle_media(lowered)
            or self._handle_smart_search(lowered)   # ← before camera so "open last screenshot" wins
            or self._handle_camera(lowered)
            or self._handle_file_creation(lowered, text)
            or self._handle_files(lowered, text)
        )

        return result

    # ─── Open / Launch ────────────────────────────────────────────────────────

    def _handle_open(self, lowered: str, original: str) -> str | None:
        """Handle 'open X' and 'launch X' commands."""
        # Strip filler words at the start
        cleaned = re.sub(r"^(just|please|can you|could you|hey|maki|,)\s+", "", lowered).strip()
        cleaned = re.sub(r"^(just|please|can you|could you)\s+", "", cleaned).strip()

        # Check folder shortcuts first
        if re.search(r"photos?\s+folders?|pictures?\s+folders?|my\s+photos?|my\s+pictures?", cleaned):
            import subprocess
            subprocess.Popen(f'explorer "{self.camera.save_path}"')
            return "Opening your photos folder."
        if re.search(r"recordings?\s+folders?|videos?\s+folders?|my\s+recordings?|my\s+videos?", cleaned):
            import subprocess
            subprocess.Popen(f'explorer "{self.camera.video_path}"')
            return "Opening your recordings folder."
        if re.search(r"screenshots?\s+folders?|my\s+screenshots?", cleaned):
            import subprocess
            subprocess.Popen(f'explorer "{self.screenshot.save_path}"')
            return "Opening your screenshots folder."
        if re.search(r"downloads?\s+folders?|my\s+downloads?", cleaned):
            import subprocess, pathlib
            subprocess.Popen(f'explorer "{pathlib.Path.home() / "Downloads"}"')
            return "Opening your Downloads folder."
        if re.search(r"documents?\s+folders?|my\s+documents?", cleaned):
            import subprocess, pathlib
            subprocess.Popen(f'explorer "{pathlib.Path.home() / "Documents"}"')
            return "Opening your Documents folder."
        if re.search(r"desktop", cleaned):
            import subprocess, pathlib
            subprocess.Popen(f'explorer "{pathlib.Path.home() / "Desktop"}"')
            return "Opening your Desktop."

        patterns = [
            r"^open\s+(.+)$",
            r"^launch\s+(.+)$",
            r"^start\s+(.+)$",
            r"^run\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, cleaned)
            if match:
                target = match.group(1).strip()
                return self.launcher.open(target)
        return None

    # ─── Volume ──────────────────────────────────────────────────────────────

    def _handle_volume(self, lowered: str) -> str | None:
        """Handle volume control commands."""
        if not self.system:
            return None
        if re.search(r"\bvolume\s+up\b|\blouder\b|\bincrease\s+volume\b", lowered):
            # Check for custom step: "volume up 20"
            step_match = re.search(r"volume\s+up\s+(\d+)", lowered)
            step = int(step_match.group(1)) if step_match else 10
            return self.system.volume_up(step)

        if re.search(r"\bvolume\s+down\b|\bquieter\b|\bdecrease\s+volume\b|\blower\s+volume\b", lowered):
            step_match = re.search(r"volume\s+down\s+(\d+)", lowered)
            step = int(step_match.group(1)) if step_match else 10
            return self.system.volume_down(step)

        if re.search(r"\bmute\b|\bunmute\b|\btoggle\s+mute\b", lowered):
            return self.system.mute()

        # "set volume to 50" / "volume 70"
        vol_match = re.search(r"(?:set\s+)?volume\s+(?:to\s+)?(\d+)", lowered)
        if vol_match:
            return self.system.set_volume(int(vol_match.group(1)))

        return None

    # ─── System Power & Lock ─────────────────────────────────────────────────

    def _handle_system(self, lowered: str) -> str | None:
        """Handle shutdown, restart, sleep, lock commands."""
        if not self.system:
            return None
        if re.search(r"\bshutdown\b|\bshut\s+down\b|\bturn\s+off\b|\bpower\s+off\b", lowered):
            return self.system.shutdown()

        if re.search(r"\brestart\b|\breboot\b", lowered):
            return self.system.restart()

        if re.search(r"\bsleep\b|\bhibernate\b", lowered):
            return self.system.sleep()

        if re.search(r"\block\b|\block\s+(screen|pc|computer)\b", lowered):
            return self.system.lock()

        if re.search(r"\bcancel\s+shutdown\b|\babort\s+shutdown\b", lowered):
            return self.system.cancel_shutdown()

        # Brightness
        if re.search(r"\bbrightness\s+up\b|\bincrease\s+brightness\b", lowered):
            return self.system.brightness_up()

        if re.search(r"\bbrightness\s+down\b|\bdecrease\s+brightness\b|\blower\s+brightness\b", lowered):
            return self.system.brightness_down()

        bright_match = re.search(r"(?:set\s+)?brightness\s+(?:to\s+)?(\d+)", lowered)
        if bright_match:
            return self.system.set_brightness(int(bright_match.group(1)))

        return None

    # ─── Media ───────────────────────────────────────────────────────────────

    def _handle_media(self, lowered: str) -> str | None:
        """Handle media playback commands."""
        if re.search(r"\bplay\s+pause\b|\btoggle\s+play\b|\bpause\b|\bresume\s+music\b", lowered):
            return self.media.play_pause()

        if re.search(r"\bnext\s+(track|song)\b|\bskip\b|\bskip\s+(track|song)\b", lowered):
            return self.media.next_track()

        if re.search(r"\bprevious\s+(track|song)\b|\bprev\s+(track|song)\b|\bback\s+(track|song)\b", lowered):
            return self.media.previous_track()

        if re.search(r"\bstop\s+(music|playing|playback)\b", lowered):
            return self.media.stop()

        # "play X on Spotify"
        spotify_match = re.search(r"\bplay\s+(.+?)\s+on\s+spotify\b", lowered)
        if spotify_match:
            return self.media.play_on_spotify(spotify_match.group(1))

        if re.search(r"\bopen\s+spotify\b", lowered):
            return self.media.open_spotify()

        return None

    # ─── Camera & Screenshots ────────────────────────────────────────────────

    def _handle_camera(self, lowered: str) -> str | None:
        """Handle photo, video, screenshot, and folder commands."""
        # Open recordings / videos folder
        if re.search(r"\b(recordings?|videos?)\s+folders?\b|\bopen\s+(my\s+)?(recordings?|videos?)\b|\bwhere.*?(recordings?|videos?)\b|\bfind.*?(recordings?|videos?)\b", lowered):
            folder = self.camera.video_path
            import subprocess
            subprocess.Popen(f'explorer "{folder}"')
            return f"Opening your recordings folder."

        # Open photos folder
        if re.search(r"\b(photos?|pictures?)\s+folders?\b|\bopen\s+(my\s+)?(photos?|pictures?)\b|\bwhere.*?(photos?|pictures?)\b|\bfind.*?(photos?|pictures?)\b", lowered):
            folder = self.camera.save_path
            import subprocess
            subprocess.Popen(f'explorer "{folder}"')
            return f"Opening your photos folder."

        # Screenshot — ONLY if NOT asking to open/find/show an existing one
        if re.search(r"\bscreenshot\b|\bcapture\s+(the\s+)?screen\b|\bscreen\s+capture\b", lowered):
            # Skip if asking to open/find/show existing screenshot
            if re.search(r"\bopen\b|\bfind\b|\bshow\b|\blast\b|\blatest\b|\bprevious\b|\brecent\b|\bjust\b|\byou\s+took\b|\byou\s+take\b|\bthat\b", lowered):
                return None  # Let smart search handle it
            if re.search(r"\bwindow\b|\bactive\b", lowered):
                return self.screenshot.capture_window()
            return self.screenshot.capture_full()

        # Take photo — ONLY if NOT asking to open/find an existing one
        if re.search(r"\btake\s+(a\s+)?(photo|picture|pic|selfie)\b|\bcapture\s+(a\s+)?photo\b", lowered):
            if re.search(r"\bopen\b|\bfind\b|\bshow\b|\blast\b|\blatest\b", lowered):
                return None
            return self.camera.take_photo()

        # Start recording
        if re.search(r"\bstart\s+(recording|video)\b|\brecord\s+video\b|\bbegin\s+recording\b", lowered):
            return self.camera.start_recording()

        # Stop recording
        if re.search(r"\bstop\s+recording\b|\bend\s+recording\b|\bfinish\s+recording\b", lowered):
            return self.camera.stop_recording()

        return None

    # ─── File Creation ───────────────────────────────────────────────────────

    def _handle_file_creation(self, lowered: str, original: str) -> str | None:
        """
        Handle file creation commands.
        Examples:
          "create a hello world txt file in the test folder"
          "make a new file called notes.txt"
          "create file report.docx in school/activities"
        """
        if not re.search(r"\bcreate\b|\bmake\b|\bnew\s+file\b|\bwrite\s+(a\s+)?file\b", lowered):
            return None

        # Extract filename — look for "called X", "named X", or "X.ext"
        filename = None
        folder_hint = None

        # Match "called/named filename.ext"
        name_match = re.search(r'(?:called|named)\s+["\']?([^\s"\']+\.[a-z]{2,5})["\']?', lowered)
        if name_match:
            filename = name_match.group(1)

        # Match bare "filename.ext" pattern
        if not filename:
            ext_match = re.search(r'\b([\w\-]+\.(txt|docx|doc|pdf|md|csv|py|js|html|json))\b', lowered)
            if ext_match:
                filename = ext_match.group(1)

        # Match "hello world txt file" → hello_world.txt
        if not filename:
            type_match = re.search(r'(?:a\s+)?([\w\s]+?)\s+(txt|docx|md|csv|py|js|html)\s+file', lowered)
            if type_match:
                name_part = type_match.group(1).strip().replace(" ", "_")
                ext = type_match.group(2)
                filename = f"{name_part}.{ext}"

        if not filename:
            return None

        # Extract folder — look for "in/inside the X folder" or "in X"
        folder_match = re.search(r'(?:in|inside|into)\s+(?:the\s+)?["\']?([^\s"\']+(?:\s+folder)?)["\']?', lowered)
        if folder_match:
            folder_hint_raw = folder_match.group(1).replace(" folder", "").strip()
            # Search for this folder in MakiSync Storage
            found = self.files.find_folder(folder_hint_raw)
            if found:
                folder_hint = str(found)

        # Extract content — look for "contains/with content X"
        content = ""
        content_match = re.search(r'(?:contains?|with\s+content|that\s+says?)\s+["\']?(.+?)(?:["\']|$)', lowered)
        if content_match:
            content = content_match.group(1).strip()

        return self.files.create_file(filename, content, folder_hint or "")

    # ─── Smart MakiSync Search ────────────────────────────────────────────────

    def _handle_smart_search(self, lowered: str) -> str | None:
        """
        Handle smart file search commands using natural language dates and recency.
        Examples:
          "open the screenshot I took just now"
          "open my last photo"
          "find the recording from yesterday"
          "open screenshot from today"
          "show my photos from Monday"
          "open the last screenshot you take"
        """
        # Detect category
        category = None
        if re.search(r"\bscreenshots?\b", lowered):
            category = "Screenshots"
        elif re.search(r"\bphotos?\b|\bpictures?\b|\bcamera\b", lowered):
            category = "Photos"
        elif re.search(r"\brecordings?\b|\bvideos?\b", lowered):
            category = "Recordings"

        if not category:
            return None

        # Detect "open/show/find + last/latest/just/recent" → find latest
        if re.search(r"\b(open|show|find|get|display)\b.*\b(last|latest|recent|just|previous)\b|\b(last|latest|recent|just)\b.*\b(screenshot|photo|recording|picture)\b", lowered):
            return self.files.find_latest(category)

        # Detect "latest / last / just now" intent without open/show
        if re.search(r"\blast\b|\blatest\b|\bjust\s+now\b|\bmost\s+recent\b|\bjust\s+took\b|\bjust\s+captured\b|\byou\s+took\b|\byou\s+take\b|\byou\s+captured\b", lowered):
            return self.files.find_latest(category)

        # Detect date reference
        date_match = re.search(
            r"\b(today|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
            r"|\d{4}-\d{2}-\d{2}|just\s+now|right\s+now)\b",
            lowered
        )
        if date_match:
            date_str = date_match.group(1)
            return self.files.find_by_date(category, date_str)

        # "open my screenshots folder" style
        if re.search(r"\bfolder\b|\bopen\b", lowered):
            return self.files.open_maki_folder(category)

        return None

    # ─── Files ───────────────────────────────────────────────────────────────

    def _handle_files(self, lowered: str, original: str) -> str | None:
        """Handle file management commands."""
        # Organize folder
        org_match = re.search(
            r"(?:organize|clean\s+up|sort)\s+(?:my\s+)?(.+?)(?:\s+folder)?$",
            lowered
        )
        if org_match:
            folder = org_match.group(1).strip()
            return self.files.organize(folder)

        # Search files
        search_match = re.search(
            r"(?:search|find|look\s+for)\s+(?:file\s+)?(?:called\s+)?['\"]?(.+?)['\"]?$",
            lowered
        )
        if search_match:
            query = search_match.group(1).strip()
            return self.files.search(query)

        # Folder summary
        summary_match = re.search(
            r"(?:what'?s?\s+in|show|list)\s+(?:my\s+)?(.+?)(?:\s+folder)?$",
            lowered
        )
        if summary_match:
            folder = summary_match.group(1).strip()
            result = self.files.get_folder_summary(folder)
            if "not found" not in result:
                return result

        return None
