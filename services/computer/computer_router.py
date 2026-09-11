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
        self.ai_service = None

        # SystemControl uses pycaw — may fail on some setups
        try:
            self.system = SystemControl()
        except Exception as e:
            print(f"[ComputerRouter] SystemControl init failed: {e}")
            self.system = None

    def set_ai_service(self, ai_service) -> None:
        """Inject AI service for smart generative file writing."""
        self.ai_service = ai_service

    def handle(self, text: str) -> str | None:
        """Try to handle the text as a computer control command."""
        lowered = text.lower().strip()

        # Strip common filler words that break pattern matching
        lowered = re.sub(r"^(just|please|hey maki|maki)[,\s]+", "", lowered).strip()
        lowered = re.sub(r"^(can you|could you|would you|i want you to|i need you to)\s+", "", lowered).strip()

        # Try each category in order
        result = (
            self._handle_write_to_file(lowered, text)
            or self._handle_open(lowered, text)
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

    # ─── File Writing & Generative Document Creation ─────────────────────────

    def _handle_write_to_file(self, lowered: str, original: str) -> str | None:
        """
        Handle writing, appending, creating, or generating content into a file in MakiSync Storage.
        Handles:
          "Write a .txt file story about me inside C:\MakiSync Storage\test"
          "Write a story about me in C:\MakiSync Storage\test\story.txt"
          "can you write some example paragraphs there a story about maki"
          "create a txt file called notes.txt in test folder and write: hello"
          "add notes to the file"
        """
        import os
        from pathlib import Path
        from services.storage.maki_sync import MAKI_SYNC_ROOT, get_dated_folder

        # Check for file action verbs
        has_file_verb = bool(re.search(r"\b(write|create|make|generate|save|put|append|type|add)\b", lowered))
        if not has_file_verb:
            return None

        # Check for file indicators
        is_file_op = (
            bool(re.search(r"\b(\.txt|\.docx|\.doc|\.md|\.py|\.js|\.html|\.json|\.csv|txt|docx|word|pdf|markdown|python|file|document|folder|there)\b", lowered))
            or bool(re.search(r"[a-zA-Z]:[\\/]", original))
        )
        if not is_file_op:
            return None

        # 1. Extract explicit Windows path if present (e.g. C:\MakiSync Storage\test or C:\MakiSync Storage\test\notes.txt)
        explicit_path = None
        path_match = re.search(r'([a-zA-Z]:\\[^\r\n"\'<>]+|[a-zA-Z]:/[^\r\n"\'<>]+)', original)
        if path_match:
            raw_p = path_match.group(1).rstrip(".,;")
            explicit_path = Path(raw_p)

        target_file = None
        dest_folder = None
        filename = None

        # 2. Extract extension (.txt, .docx, .md, etc.)
        ext = ".txt"
        ext_match = re.search(r'\.(txt|docx|doc|pdf|md|csv|py|js|html|json|yaml|yml)\b', lowered)
        if ext_match:
            ext = f".{ext_match.group(1)}"
        elif re.search(r'\bword\b|\bdoc\b', lowered):
            ext = ".docx"
        elif re.search(r'\bmarkdown\b', lowered):
            ext = ".md"
        elif re.search(r'\bpython\b', lowered):
            ext = ".py"

        # 3. Handle explicit path
        if explicit_path:
            if explicit_path.suffix:
                target_file = explicit_path
                dest_folder = explicit_path.parent
                filename = explicit_path.name
            else:
                dest_folder = explicit_path
                dest_folder.mkdir(parents=True, exist_ok=True)

        # 4. Extract specific filename if named (e.g. called X, named X, or X.ext)
        if not filename:
            named_match = re.search(r'(?:called|named)\s+["\']?([^\s"\']+\.[a-z0-9]+)["\']?', lowered)
            if named_match:
                filename = named_match.group(1)
            else:
                bare_ext_match = re.search(r'\b([a-zA-Z0-9_\-]+\.(txt|docx|doc|pdf|md|csv|py|js|html|json))\b', lowered)
                if bare_ext_match:
                    filename = bare_ext_match.group(1)

        # 5. Extract destination folder if not explicit path
        if not dest_folder:
            folder_match = re.search(r'(?:in|inside|into)\s+(?:the\s+)?["\']?([^\s"\']+(?:\s+folder)?)["\']?', lowered)
            if folder_match:
                folder_hint = folder_match.group(1).replace(" folder", "").strip()
                if folder_hint and folder_hint not in ("that file", "the file", "my file", "there"):
                    found_f = self.files.find_folder(folder_hint)
                    if found_f:
                        dest_folder = found_f
                    else:
                        dest_folder = MAKI_SYNC_ROOT / folder_hint
                        dest_folder.mkdir(parents=True, exist_ok=True)

        # 6. If user references "there" or "that file" or "the file", use active last file
        if not target_file and not filename and re.search(r"\b(there|that\s+file|the\s+file|this\s+file)\b", lowered):
            last_f = self.files.get_last_file()
            if last_f and last_f.exists():
                target_file = last_f

        # 7. Construct target_file if not set
        if not target_file:
            if not dest_folder:
                dest_folder = get_dated_folder("Notes", "School")
            dest_folder.mkdir(parents=True, exist_ok=True)

            if not filename:
                # Generate slug from topic
                if "story" in lowered:
                    filename = f"story{ext}"
                elif "note" in lowered or "meeting" in lowered:
                    filename = f"notes{ext}"
                elif "code" in lowered or "script" in lowered:
                    filename = f"script{ext}"
                else:
                    filename = f"document{ext}"

            target_file = dest_folder / filename

        # 8. Check for explicit inline content vs generative content
        content = ""
        inline_match = re.search(r'(?:with\s+content|that\s+says?|write:)\s+["\']?(.+?)(?:["\']|$)', original, flags=re.IGNORECASE)
        if inline_match:
            content = inline_match.group(1).strip()
        else:
            # Generative AI content
            prompt_cleaned = re.sub(r"^(can you|could you|please|just|hey maki|maki)[,\s]+", "", original, flags=re.IGNORECASE).strip()
            if self.ai_service:
                system_instruction = (
                    f"You are MakiAI — personal assistant for Mark Vencent Juntilla. "
                    f"The user wants you to generate content to be written inside the file '{target_file.name}'. "
                    f"Generate the full, creative, high-quality content requested (story, essay, code, notes, paragraphs). "
                    f"Output ONLY the text to be placed inside the file. Do not include conversational greetings or conversational wrapper."
                )
                try:
                    content = self.ai_service.send(prompt_cleaned, system_instruction)
                except Exception as e:
                    print(f"[ComputerRouter] Generative file write error: {e}")
                    content = prompt_cleaned
            else:
                content = prompt_cleaned

        if not content:
            content = "Document generated by MakiAI."

        # 9. Write and open file
        target_file.parent.mkdir(parents=True, exist_ok=True)
        self.files.write_to_file(target_file, content, mode="append")
        self.files._open_file(target_file)

        return f"Done, sir. I've created and saved your document in {target_file.name} inside {target_file.parent.name} and opened it for you."

    # ─── File Creation ───────────────────────────────────────────────────────

    def _handle_file_creation(self, lowered: str, original: str) -> str | None:
        """Handled directly by _handle_write_to_file."""
        return None

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
