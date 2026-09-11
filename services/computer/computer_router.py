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
        self.system = SystemControl()
        self.media = MediaControl()

    def handle(self, text: str) -> str | None:
        """
        Try to handle the text as a computer control command.

        Args:
            text: User's voice/text input (wake word already stripped).

        Returns:
            Response string if handled, None if not a computer command.
        """
        lowered = text.lower().strip()

        # Try each category in order
        result = (
            self._handle_open(lowered, text)
            or self._handle_volume(lowered)
            or self._handle_system(lowered)
            or self._handle_media(lowered)
            or self._handle_files(lowered, text)
        )

        return result

    # ─── Open / Launch ────────────────────────────────────────────────────────

    def _handle_open(self, lowered: str, original: str) -> str | None:
        """Handle 'open X' and 'launch X' commands."""
        patterns = [
            r"^open\s+(.+)$",
            r"^launch\s+(.+)$",
            r"^start\s+(.+)$",
            r"^run\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, lowered)
            if match:
                target = match.group(1).strip()
                return self.launcher.open(target)
        return None

    # ─── Volume ──────────────────────────────────────────────────────────────

    def _handle_volume(self, lowered: str) -> str | None:
        """Handle volume control commands."""
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
