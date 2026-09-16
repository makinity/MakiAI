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
from services.computer.system_health import SystemHealthMonitor
from services.computer.window_manager import WindowManager
from services.computer.screen_vision import ScreenVisionService
from services.computer.camera_tool import CameraTool
from services.browser.chrome_profile_launcher import ChromeProfileLauncher
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
        self.window_mgr = WindowManager()
        self.screen_vision = ScreenVisionService()
        self.camera_tool = CameraTool()
        self.health = SystemHealthMonitor()
        self.chrome_profiles = ChromeProfileLauncher()
        self.ai_service = None

        # SystemControl uses pycaw — may fail on some setups
        try:
            self.system = SystemControl()
        except Exception as e:
            print(f"[ComputerRouter] SystemControl init failed: {e}")
            self.system = None

    def set_ai_service(self, ai_service) -> None:
        """Inject AI service for smart generative file writing and vision."""
        self.ai_service = ai_service

    def handle(self, text: str) -> str | None:
        """Try to handle the text as a computer control command."""
        lowered = text.lower().strip()

        # Strip common filler words that break pattern matching
        lowered = re.sub(r"^(just|please|hey maki|maki)[,\s]+", "", lowered).strip()
        lowered = re.sub(r"^(can you|could you|would you|i want you to|i need you to)\s+", "", lowered).strip()

        # Try each category in order
        result = (
            self._handle_close(lowered, text)
            or self._handle_media(lowered)          # ← Before _handle_browser_profile_site so "open youtube and play..." wins
            or self._handle_browser_profile_site(lowered, text)
            or self._handle_system_health(lowered)
            or self._handle_physical_camera_vision(lowered, text)
            or self._handle_screen_vision(lowered, text)
            or self._handle_window_move(lowered, text)
            or self._handle_auto_tile(lowered, text)
            or self._handle_write_to_file(lowered, text)
            or self._handle_smart_search(lowered)   # ← Before _handle_open so "open last photo/screenshot" wins
            or self._handle_open(lowered, text)
            or self._handle_volume(lowered)
            or self._handle_system(lowered)
            or self._handle_camera(lowered)
            or self._handle_file_creation(lowered, text)
            or self._handle_files(lowered, text)
        )

        return result

    # ─── Close / Kill Application & Window Management ────────────────────────

    def _handle_close(self, lowered: str, original: str) -> str | None:
        """
        Handle closing desktop applications and browser windows.
        Examples:
          - "close YouTube" / "can you close YouTube for me"
          - "close Chrome" / "close VS Code"
          - "kill notepad" / "exit discord"
          - "close this window" / "close the active window"
        """
        # Close / kill verbs: close, kill, exit, terminate, shut down
        cleaned_cmd = re.sub(r"[?!.,]+$", "", lowered.strip()).strip()
        close_match = re.search(r"^(?:please\s+|can\s+you\s+(?:please\s+|just\s+)?|could\s+you\s+(?:please\s+|just\s+)?|just\s+)?(?:close|kill|terminate|exit)\s+(?:the\s+)?(.+?)(?:\s+for\s+me|\s+please)?$", cleaned_cmd)
        if not close_match:
            return None

        target = close_match.group(1).strip()
        # Clean target query
        target = re.sub(r"^(the\s+app|the\s+window|this\s+app|this\s+window|app|window)\s*", "", target).strip()
        target = re.sub(r"\s+(for\s+me|please)$", "", target).strip()
        if target in ("browser", "the browser", "my browser", "google browser", "chrome browser"):
            target = "chrome"
        elif not target or target in ("this", "it", "active", "current"):
            target = "active"

        return self.window_mgr.close_window(target)

    # ─── Chrome Multi-Profile Site Launcher ──────────────────────────────────

    def _handle_browser_profile_site(self, lowered: str, original: str) -> str | None:
        """
        Match specific web platforms to their dedicated Chrome profiles.
        Examples:
          - "open facebook" / "launch fb" / "open my facebook"
          - "open github" / "go to canva" / "open gemini"
          - "launch google flow" / "check linkedin" / "open tiktok" / "open youtube"
        """
        if hasattr(self, "chrome_profiles") and self.chrome_profiles:
            return self.chrome_profiles.match_and_launch(lowered)
        return None

    # ─── System Health & Hardware Monitoring ─────────────────────────────────

    def _handle_system_health(self, lowered: str) -> str | None:
        """
        Handle hardware introspection and vitals queries.
        Examples:
          - "what are my system vitals"
          - "how is my battery"
          - "what is my cpu and ram usage"
          - "check system health"
        """
        if not hasattr(self, "health") or not self.health:
            return None

        # Battery specific
        if re.search(r"\b(battery\s+(?:status|percentage|level|health)|how\s+is\s+(?:my\s+)?battery|is\s+my\s+laptop\s+charging|battery\s+life)\b", lowered):
            bat = self.health.get_battery()
            if not bat.get("available"):
                return "Your system is operating on direct AC power with no battery sensor detected, sir."
            plug_txt = "plugged in" if bat["plugged"] else "unplugged and running on battery"
            return f"Sir, your battery is at {bat['percent']}% and currently {plug_txt} ({bat['time_str']})."

        # CPU / RAM specific
        if re.search(r"\b(cpu\s+usage|ram\s+usage|memory\s+usage|cpu\s+and\s+ram|processor\s+load)\b", lowered):
            perf = self.health.get_cpu_ram()
            return f"CPU utilization is at {perf['cpu_percent']}%, and RAM usage is at {perf['ram_percent']}% ({perf['ram_used_gb']} GB used out of {perf['ram_total_gb']} GB), sir."

        # Overall vitals / health
        if re.search(r"\b(system\s+vitals?|system\s+health|hardware\s+status|diagnostics|pc\s+health|system\s+status)\b", lowered):
            return self.health.get_vitals_summary()

        return None

    # ─── Physical Webcam Vision & Object/Activity Awareness ──────────────────

    def _handle_physical_camera_vision(self, lowered: str, original: str) -> str | None:
        """
        Handle physical optical vision requests via webcam.
        Examples:
          - "what am i doing" / "tell me what i'm doing"
          - "what am i holding" / "what is in my hand" / "what object is in my hand"
          - "look at me and tell me..." / "look at me" / "check the camera"
          - "is there anyone behind me" / "check the background for people" / "who is behind me"
          - "what am i wearing" / "what is this in my hand"
        """
        is_camera_vision = bool(
            re.search(r"\b(?:what\s+am\s+i|(?:do\s+you\s+|can\s+you\s+|you\s+)?know\s+what\s+i\s+(?:am|have)|(?:can\s+you\s+)?see\s+what\s+i\s+am|guess\s+what\s+i\s+(?:am|have))\s+(?:doing|holding|wearing|carrying|holding\s+up)\b", lowered)
            or re.search(r"\b(?:you\s+know|do\s+you\s+know|guess|can\s+you\s+see|tell\s+me)\s+what\s+(?:i\s+am|i\'m|am\s+i)\s+(?:holding|doing|wearing|holding\s+up)\b", lowered)
            or re.search(r"\b(what\s+am\s+i\s+(?:doing|holding|wearing|carrying|holding\s+up))\b", lowered)
            or re.search(r"\b(what(?:'s|\s+is)\s+(?:this|that|the\s+object)\s+in\s+my\s+hand)\b", lowered)
            or re.search(r"\b(what\s+object\s+is\s+in\s+my\s+hand|what\s+is\s+in\s+my\s+hands?|what\s+do\s+i\s+have\s+in\s+my\s+hands?)\b", lowered)
            or re.search(r"\b(look\s+at\s+me|take\s+a\s+look\s+at\s+me|see\s+me|can\s+you\s+see\s+me)\b", lowered)
            or re.search(r"\b(look\s+through\s+(?:the\s+)?(?:camera|webcam)|check\s+(?:the\s+)?webcam)\b", lowered)
            or re.search(r"\b(is\s+(?:there\s+)?anyone\s+behind\s+me|who\s+is\s+behind\s+me|someone\s+behind\s+me)\b", lowered)
            or re.search(r"\b(check\s+the\s+background(?:\s+for\s+people)?|is\s+anyone\s+in\s+the\s+background|who\s+is\s+in\s+the\s+background)\b", lowered)
            or re.search(r"\b(describe\s+what\s+i\s+am\s+doing|tell\s+me\s+what\s+i\s+am\s+doing)\b", lowered)
            or re.search(r"\b(what\s+do\s+you\s+see\s+in\s+front\s+of\s+the\s+camera)\b", lowered)
        )
        if not is_camera_vision:
            return None

        return self.camera_tool.analyze(original, self.ai_service)

    # ─── Contextual Screen Awareness & Vision ────────────────────────────────

    def _handle_screen_vision(self, lowered: str, original: str) -> str | None:
        """
        Handle live contextual screen awareness and visual OCR/debugging requests.
        Examples:
          - "look at my screen and summarize this"
          - "what is causing this error / crash"
          - "debug this terminal error"
          - "what is on my screen"
          - "can you read what is on my screen"
          - "look at this code and explain what is wrong"
        """
        is_vision_query = bool(
            re.search(r"\b(look\s+at\s+my\s+screen|look\s+at\s+the\s+screen|look\s+at\s+this|see\s+my\s+screen)\b", lowered)
            or re.search(r"\b(what'?s\s+on\s+my\s+screen|what\s+is\s+on\s+my\s+screen|what\s+do\s+you\s+see\s+on\s+my\s+screen)\b", lowered)
            or re.search(r"\b(debug\s+this\s+(?:error|crash|code|issue|bug)|fix\s+this\s+crash|why\s+is\s+this\s+crashing)\b", lowered)
            or re.search(r"\b(what\s+is\s+causing\s+this\s+(?:error|crash|issue|bug|problem)|what\s+caused\s+this)\b", lowered)
            or re.search(r"\b(summarize\s+this\s+(?:document|page|screen|article|code)\s+on\s+my\s+screen)\b", lowered)
            or re.search(r"\b(read\s+(?:my\s+screen|the\s+screen|this\s+window|this\s+text\s+on\s+screen))\b", lowered)
        )
        if not is_vision_query:
            return None

        return self.screen_vision.analyze(original, self.ai_service)

    # ─── Window Management & Inter-Monitor Relocation ────────────────────────

    def _handle_window_move(self, lowered: str, original: str) -> str | None:
        """
        Handle inter-monitor window relocation and visual dragging commands.
        Examples:
          - "move Chrome to my second monitor"
          - "drag this window to monitor 2"
          - "relocate VS Code to the main screen"
          - "move notepad to the other monitor"
          - "put this app on the left display"
        """
        # Verbs: move, drag, transfer, relocate, shift, put, switch, send
        move_verbs = r"\b(move|drag|transfer|relocate|shift|put|switch|send)\b"
        monitor_terms = r"\b(monitor|screen|display|other\s+monitor|second\s+monitor|main\s+monitor|primary\s+monitor|secondary\s+monitor|left\s+monitor|right\s+monitor|left\s+screen|right\s+screen)\b"

        if not (re.search(move_verbs, lowered) and re.search(monitor_terms, lowered)):
            # Also catch "move to monitor 2", "move this window over"
            if not re.search(r"\b(move|drag|transfer)\s+(?:this\s+)?(?:window|app|application)?\s+to\s+(?:monitor|screen|display)\s*([0-9]|one|two)?\b", lowered):
                return None

        # Extract target monitor
        target_mon = "other"
        if re.search(r"\b(second|secondary|monitor\s*2|screen\s*2|display\s*2|monitor\s+two|screen\s+two)\b", lowered):
            target_mon = "2"
        elif re.search(r"\b(main|primary|monitor\s*1|screen\s*1|display\s*1|monitor\s+one|screen\s+one)\b", lowered):
            target_mon = "1"
        elif re.search(r"\b(left)\b", lowered):
            target_mon = "left"
        elif re.search(r"\b(right)\b", lowered):
            target_mon = "right"

        # Extract app name
        # Matches "move [app] to [monitor...]" or "drag [app] to [screen...]"
        app_match = re.search(r"(?:move|drag|transfer|relocate|shift|put|send)\s+(?:the\s+)?(.*?)\s+(?:to|into|onto)\s+(?:my\s+)?(?:the\s+)?(second|secondary|main|primary|other|left|right|monitor|screen|display)", lowered)

        app_query = "active"
        if app_match:
            candidate = app_match.group(1).strip()
            # Clean candidate
            candidate = re.sub(r"^(this\s+window|this\s+app|the\s+window|the\s+app|window|app)$", "active", candidate).strip()
            if candidate and candidate not in ("this", "the", "it"):
                app_query = candidate

        return self.window_mgr.move_window_to_monitor(app_query=app_query, target_monitor=target_mon, visual_drag=True)

    def _handle_auto_tile(self, lowered: str, original: str) -> str | None:
        """
        Handle dynamic auto-tiling, multi-monitor workspace fitting, and window grid splitting.
        Examples:
          - "tile my windows"
          - "maximize screens across my 2 monitors"
          - "fit all 3 windows across my monitors"
          - "organize my workspace"
          - "tile windows side by side"
          - "tile chrome and vscode"
        """
        is_tile_cmd = bool(
            re.search(r"\b(tile|auto-tile|autotile)\b", lowered)
            or (re.search(r"\b(organize|snap|arrange|fit|grid|maximize)\b", lowered) and re.search(r"\b(windows?|workspace|workflow|workshop|work\s+space|screens?|displays?|monitors?|apps?)\b", lowered))
            or re.search(r"\b(across\s+(?:my\s+)?(?:2\s+|both\s+)?monitors?|across\s+(?:my\s+)?screens?)\b", lowered)
        )
        if not is_tile_cmd:
            return None

        # Determine target monitor
        target_mon = "auto"
        if re.search(r"\b(second|secondary|monitor\s*2|screen\s*2|display\s*2|monitor\s+two|screen\s+two)\b", lowered) and not re.search(r"\b(across|both|2\s+monitors|all)\b", lowered):
            target_mon = "2"
        elif re.search(r"\b(main|primary|monitor\s*1|screen\s*1|display\s*1|monitor\s+one|screen\s+one)\b", lowered) and not re.search(r"\b(across|both|2\s+monitors|all)\b", lowered):
            target_mon = "1"
        elif re.search(r"\b(left)\b", lowered) and not re.search(r"\b(across|both|2\s+monitors|all)\b", lowered):
            target_mon = "left"
        elif re.search(r"\b(right)\b", lowered) and not re.search(r"\b(across|both|2\s+monitors|all)\b", lowered):
            target_mon = "right"

        # Determine layout preference
        layout = "auto"
        if re.search(r"\b(split|side\s+by\s+side|50/50|50\s+50|2\s+col|two\s+columns?)\b", lowered):
            layout = "split"
        elif re.search(r"\b(quadrant|quadrants|2x2|2\s+by\s+2|four\s+quadrants?|grid)\b", lowered):
            layout = "quadrant"
        elif re.search(r"\b(3\s+col|three\s+columns?|columns)\b", lowered):
            layout = "columns"

        # Check for specific priority apps (e.g., "tile chrome and vscode", "tile notepad, chrome, and vs code")
        priority_apps = None
        and_match = re.search(r"\btile\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)\s+and\s+([a-zA-Z0-9_\-\s]+?)(?:\s+on|\s+in|\s+into|\s+side|$)", lowered)
        if and_match:
            app1 = and_match.group(1).replace("my", "").replace("the", "").strip()
            app2 = and_match.group(2).replace("my", "").replace("the", "").strip()
            # Verify they are not general layout keywords
            if app1 not in ("windows", "window", "apps", "workspace") and app2 not in ("windows", "window", "apps", "workspace"):
                priority_apps = [app1, app2]

        return self.window_mgr.auto_tile(target_monitor=target_mon, layout=layout, priority_apps=priority_apps)

    # ─── Open / Launch ────────────────────────────────────────────────────────

    def _handle_open(self, lowered: str, original: str) -> str | None:
        """Handle 'open X', 'launch X', explicit paths, and file opening."""
        # 1. Check for explicit absolute path anywhere in the command
        path_match = re.search(r'([a-zA-Z]:\\[^\r\n"\'<>]+|[a-zA-Z]:/[^\r\n"\'<>]+)', original)
        if path_match:
            raw_path = path_match.group(1).rstrip(".,;")
            found_direct = self.files.find_file(raw_path)
            if found_direct:
                self.files._open_file(found_direct)
                return f"Opening {found_direct.name} from {found_direct.parent.name} for you, sir."

        # Strip filler words at the start
        cleaned = re.sub(r"^(just|please|can you|could you|hey|maki|,)\s+", "", lowered).strip()
        cleaned = re.sub(r"^(just|please|can you|could you)\s+", "", cleaned).strip()

        # 2. Check folder shortcuts
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
        if re.search(r"knowledge\s+(base|space)\s+folders?|my\s+knowledge\s+base", cleaned):
            from services.settings.settings_service import SettingsService
            import subprocess
            kb_dir = SettingsService().get_kb_path()
            subprocess.Popen(f'explorer "{kb_dir}"')
            return "Opening your Knowledge Base folder."

        # 3. Ignore assistant info queries (schedules, reminders, deadlines, meetings)
        if re.search(r"\b(schedules?|reminders?|deadlines?|meetings?|calendar|appointments?|what\s+to\s+do)\b", cleaned, flags=re.IGNORECASE):
            return None

        # 4. Match 'open / launch / view / show + target'
        patterns = [
            r"^(?:open|launch|start|run|view|show)\s+(?:the\s+file\s+(?:called\s+|named\s+)?|the\s+document\s+|the\s+)?(.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, cleaned)
            if match:
                target = match.group(1).strip().rstrip(".,;!?")

                # A. If target is a well-known app or website, launch it first!
                if self.launcher.is_known(target):
                    return self.launcher.open(target)

                # B. Check if explicitly asking for a file/document or has file extension
                has_file_ext = bool(re.search(r'\.(pdf|docx|doc|txt|md|xlsx|pptx|py|js|html|css|json|csv)\b', target, flags=re.IGNORECASE))
                explicit_file_query = bool(re.search(r'\b(file|document|doc|pdf|notes|paper|report|guide)\b', cleaned, flags=re.IGNORECASE))

                if has_file_ext or explicit_file_query:
                    found_file = self.files.find_file(target)
                    if found_file:
                        self.files._open_file(found_file)
                        return f"Opening {found_file.name} from {found_file.parent.name} for you, sir."

                # C. Try general app launcher (handles system binaries, URLs, Chrome profiles)
                launch_result = self.launcher.open(target)
                if "couldn't find" not in launch_result:
                    return launch_result

                # D. Fall back to finding a file across Knowledge Base & Storage
                found_file = self.files.find_file(target)
                if found_file:
                    self.files._open_file(found_file)
                    return f"Opening {found_file.name} from {found_file.parent.name} for you, sir."

                return launch_result

        return None

    # ─── Volume ──────────────────────────────────────────────────────────────

    def _handle_volume(self, lowered: str) -> str | None:
        """Handle volume control commands."""
        if not self.system:
            return None

        # 1. Max / Full Volume
        if (
            re.search(r"\b(?:set|turn|put|make|crank|raise|push)?\s*(?:up\s+)?(?:the\s+)?volume\s+(?:to\s+|at\s+)?(?:max|maximum|full|100%?|highest|top|the\s+max|the\s+maximum)\b", lowered)
            or re.search(r"\b(?:full|max|maximum|highest|top)\s+volume\b", lowered)
            or re.search(r"\b(?:100\s*(?:percent|%)|all\s+the\s+way\s+up)\s*(?:volume)?\b", lowered)
            or re.search(r"\b(?:crank\s+up\s+the\s+volume|crank\s+it\s+up)\b", lowered)
        ):
            return self.system.set_volume(100)

        # 2. Min / Zero / 0%
        if (
            re.search(r"\b(?:set|turn|put|make|lower)?\s*(?:down\s+)?(?:the\s+)?volume\s+(?:to\s+|at\s+)?(?:min|minimum|zero|0%?|lowest|the\s+min|the\s+minimum)\b", lowered)
            or re.search(r"\b(?:min|minimum|zero|lowest|no)\s+volume\b", lowered)
            or re.search(r"\b(?:0\s*(?:percent|%)|all\s+the\s+way\s+down)\s*(?:volume)?\b", lowered)
        ):
            return self.system.set_volume(0)

        if re.search(r"\b(mute|unmute|toggle\s+mute|silence)\b", lowered):
            return self.system.mute()

        # 3. Numeric specific: "set volume to 50", "volume 70%", "turn volume to 80", "put volume at 30"
        vol_match = re.search(r"(?:set|turn|put|make)?\s*(?:the\s+)?volume\s+(?:to|at)?\s*(\d+)(?:%|\s*percent)?", lowered)
        if vol_match:
            try:
                val = int(vol_match.group(1))
                return self.system.set_volume(val)
            except (ValueError, TypeError):
                pass

        # 4. Volume Up / Louder
        if re.search(r"\b(volume\s+up|louder|increase\s+volume|raise\s+(?:the\s+)?volume|boost\s+(?:the\s+)?volume|up\s+the\s+volume|turn\s+(?:the\s+)?volume\s+up|turn\s+up\s+(?:the\s+)?volume|pump\s+up\s+(?:the\s+)?volume|make\s+it\s+louder)\b", lowered):
            step_match = re.search(r"(?:volume\s+up|increase\s+volume\s+by|up\s+the\s+volume\s+by|raise\s+volume\s+by)\s+(\d+)", lowered)
            step = int(step_match.group(1)) if step_match else 10
            return self.system.volume_up(step)

        # 5. Volume Down / Quieter
        if re.search(r"\b(volume\s+down|quieter|softer|decrease\s+volume|lower\s+(?:the\s+)?volume|down\s+the\s+volume|turn\s+(?:the\s+)?volume\s+down|turn\s+down\s+(?:the\s+)?volume|make\s+it\s+quieter|make\s+it\s+softer)\b", lowered):
            step_match = re.search(r"(?:volume\s+down|decrease\s+volume\s+by|lower\s+the\s+volume\s+by)\s+(\d+)", lowered)
            step = int(step_match.group(1)) if step_match else 10
            return self.system.volume_down(step)

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
        """Handle media playback commands for Spotify, YouTube, and system media controls."""
        import urllib.parse

        # 0. Close / Stop YouTube explicitly
        if re.search(r"\b(?:close|stop|exit|kill|shut(?:\s+down)?)\s+(?:the\s+)?youtube(?:\s+(?:tab|window|browser|app))?\b", lowered):
            return self.window_mgr.close_window("youtube")

        # 1. Play / Pause / Resume controls
        if re.search(r"\b(play\s+pause|toggle\s+play|pause|resume(?:\s+(?:music|playback|song|video|audio))?|continue\s+(?:playback|music|song)|unpause)\b", lowered):
            return self.media.play_pause()

        # 2. Next / Skip
        if re.search(r"\b(next\s+(?:track|song|video)|skip|skip\s+(?:track|song|video))\b", lowered):
            return self.media.next_track()

        # 3. Previous / Back
        if re.search(r"\b(previous\s+(?:track|song)|prev\s+(?:track|song)|back\s+(?:track|song))\b", lowered):
            return self.media.previous_track()

        # 4. Stop playback
        if re.search(r"\bstop\s+(music|playing|playback|video)\b", lowered):
            return self.media.stop()

        # 5. Follow-up "now play it", "play it", "go", "open that in browser and play it" (only if no new search term specified)
        if (
            re.match(r"^(?:okay\s*,?\s*)?(?:so\s+)?(?:now\s+)?(?:play\s+it|play\s+that|start\s+it|go|let'?s\s+go)[.,?!]?$", lowered.strip())
            or re.match(r"^(?:so\s+)?open\s+(?:that|it|this)\s+(?:directly\s+)?in\s+(?:the\s+)?browser(?:\s+and\s+play\s+it)?[.,?!]?$", lowered.strip())
        ):
            try:
                from services.browser.chrome_profile_launcher import ChromeProfileLauncher
                random_yt_url = "https://www.youtube.com/results?search_query=popular+music+videos+mix"
                ChromeProfileLauncher().launch_site_in_profile("youtube", url_override=random_yt_url)
                return "Opening YouTube and playing the media for you in your browser, sir."
            except Exception:
                pass

        # 6. "play X on Spotify"
        spotify_match = re.search(r"\bplay\s+(.+?)\s+on\s+spotify\b", lowered)
        if spotify_match:
            return self.media.play_on_spotify(spotify_match.group(1))

        if re.search(r"\bopen\s+spotify\b", lowered):
            return self.media.open_spotify()

        # 7. Compound "open youtube for me and play X" or "open browser and play X"
        if re.search(r"\bopen\s+(?:youtube|my\s+browser|the\s+browser|browser)?\s*(?:for\s+me\s+)?(?:and\s+)?(?:search\s+(?:for\s+)?|play|stream)\b", lowered):
            after_play = re.search(r"\b(?:play|search\s+(?:for\s+)?|stream)\s+(.+?)(?:\s+for\s+me|\s+in\s+browser|\s+on\s+browser|\s+and\s+play\s+it)?$", lowered)
            q_raw = after_play.group(1).strip() if after_play else ""
            # Strip trailing comments like "just random", "randomly", "for me"
            q_candidate = re.sub(r"\b(?:just\s+random|randomly|for\s+me|please)\b", "", q_raw, flags=re.IGNORECASE).strip()
            q_candidate = re.sub(r"^(?:youtube\s+(?:for\s+me\s+)?(?:and\s+)?|browser\s+(?:and\s+)?)\s*", "", q_candidate).strip()
            q_candidate = re.sub(r"[?!.,]+", " ", q_candidate).strip()
            q_candidate = re.sub(r"\s+", " ", q_candidate).strip()
            if not q_candidate or q_candidate.lower() in ("random", "random music", "random video", "it", "this", "that"):
                q_candidate = "popular music videos mix"
            try:
                from services.browser.chrome_profile_launcher import ChromeProfileLauncher
                encoded_q = urllib.parse.quote_plus(q_candidate)
                yt_url = f"https://www.youtube.com/results?search_query={encoded_q}"
                ChromeProfileLauncher().launch_site_in_profile("youtube", url_override=yt_url)
                return f"Opening YouTube and playing '{q_candidate}' for you, sir."
            except Exception as e:
                print(f"[ComputerRouter] Open and play error: {e}")

        # 8. "search for X and play it" (e.g. "search for Bruno Mars popular music song and play it")
        search_and_play = re.search(r"(?:i\s+mean\s+)?(?:search\s+(?:for\s+)?|look\s+up\s+|find\s+)(.+?)\s+(?:and\s+play\s+(?:it|that|this)|and\s+play)\b", lowered)
        if search_and_play:
            q_candidate = search_and_play.group(1).strip()
            try:
                from services.browser.chrome_profile_launcher import ChromeProfileLauncher
                encoded_q = urllib.parse.quote_plus(q_candidate)
                yt_url = f"https://www.youtube.com/results?search_query={encoded_q}"
                ChromeProfileLauncher().launch_site_in_profile("youtube", url_override=yt_url)
                return f"Searching and playing '{q_candidate}' on YouTube for you, sir."
            except Exception as e:
                print(f"[ComputerRouter] Search and play error: {e}")

        # 9. "play random videos / music on youtube" or "random music video"
        if re.search(r"\b(?:play\s+)?random\s+(?:music|videos?|songs?|tracks?|music\s+videos?)(?:\s+on\s+youtube)?\b", lowered):
            try:
                from services.browser.chrome_profile_launcher import ChromeProfileLauncher
                random_yt_url = "https://www.youtube.com/results?search_query=popular+music+videos+mix"
                ChromeProfileLauncher().launch_site_in_profile("youtube", url_override=random_yt_url)
                return "Opening YouTube and playing a music video mix for you, sir."
            except Exception as e:
                print(f"[ComputerRouter] YouTube random launch error: {e}")

        # 10. "play X on YouTube" or "can you play X on YouTube"
        yt_match = re.search(r"^(?:can\s+you\s+)?(?:please\s+)?play\s+(.+?)(?:\s+on\s+youtube|\s+on\s+yt|\s+in\s+youtube)$", lowered.strip())
        if yt_match:
            query = yt_match.group(1).strip()
            query = re.sub(r"\s+for\s+me$", "", query).strip()
            try:
                from services.browser.chrome_profile_launcher import ChromeProfileLauncher
                encoded_q = urllib.parse.quote_plus(query)
                yt_url = f"https://www.youtube.com/results?search_query={encoded_q}"
                ChromeProfileLauncher().launch_site_in_profile("youtube", url_override=yt_url)
                return f"Playing {query} on YouTube in your personal profile, sir."
            except Exception as e:
                print(f"[ComputerRouter] YouTube launch error: {e}")

        # 11. Direct "play <title/artist>" (e.g. "play bohemian rhapsody", "play lofi")
        direct_play_match = re.search(r"^(?:can\s+you\s+)?(?:please\s+)?play\s+(.+?)(?:\s+for\s+me)?$", lowered.strip())
        if direct_play_match:
            candidate = direct_play_match.group(1).strip()
            # Ignore non-media words like "a game", "in ros", "with me", "role"
            if not any(k in candidate for k in ("game", "ros", "rules", "with", "around", "a role")):
                try:
                    from services.browser.chrome_profile_launcher import ChromeProfileLauncher
                    encoded_q = urllib.parse.quote_plus(candidate)
                    yt_url = f"https://www.youtube.com/results?search_query={encoded_q}"
                    ChromeProfileLauncher().launch_site_in_profile("youtube", url_override=yt_url)
                    return f"Playing '{candidate}' on YouTube for you, sir."
                except Exception as e:
                    print(f"[ComputerRouter] Direct play error: {e}")

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
          "open the captured image in the magazine storage"
          "open my last photo"
          "find the recording from yesterday"
          "open screenshot from today"
          "show my photos from Monday"
          "open the last screenshot you take"
        """
        # Normalize common Whisper misrecognitions ("magazine storage" / "max sync" -> "makisync storage")
        norm = re.sub(r"\b(?:magazine|max\s+sync|make\s+sync|maki\s+sync|cable)\s+storage\b", "makisync storage", lowered)

        # Detect category
        category = None
        if re.search(r"\bscreenshots?\b|\bcaptured?\s*(?:image|photo|picture|screen)?\b|\bcapture\b|\bscreen\s+capture\b", norm):
            category = "Screenshots"
        elif re.search(r"\bphotos?\b|\bpictures?\b|\bcamera\b", norm):
            category = "Photos"
        elif re.search(r"\brecordings?\b|\bvideos?\b", norm):
            category = "Recordings"
        elif re.search(r"\b(images?|captured?\s+image)\b", norm):
            category = "Screenshots"

        if not category:
            return None

        # Detect "open/show/find + last/latest/just/recent/captured" → find latest
        if (
            re.search(r"\b(open|show|find|get|display|view)\b.*\b(last|latest|recent|just|previous|captured?|image|photo|picture|screenshot|screen|recording|video|took|taken|saved|storage|makisync)\b", norm)
            or re.search(r"\b(last|latest|recent|just|previous)\b.*\b(screenshot|photo|recording|picture|video|image|camera)\b", norm)
            or re.search(r"\blast\b|\blatest\b|\bjust\s+now\b|\bmost\s+recent\b|\bjust\s+took\b|\bjust\s+captured\b|\byou\s+took\b|\byou\s+take\b|\byou\s+captured?\b|\byou\s+save\b|\byou\s+saved\b", norm)
            or re.search(r"\bcaptured?\s+(?:image|photo|picture|screen)\b", norm)
        ):
            return self.files.find_latest(category)


        # Detect date reference
        date_match = re.search(
            r"\b(today|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
            r"|\d{4}-\d{2}-\d{2}|just\s+now|right\s+now)\b",
            norm
        )
        if date_match:
            date_str = date_match.group(1)
            return self.files.find_by_date(category, date_str)

        # "open my screenshots folder" style
        if re.search(r"\bfolder\b|\bopen\b", norm):
            return self.files.open_maki_folder(category)

        return None

    # ─── Files ───────────────────────────────────────────────────────────────

    def _handle_files(self, lowered: str, original: str) -> str | None:
        """Handle file management commands."""
        # Organize folder
        org_match = re.search(
            r"(?:organize|clean\s+up|sort)\s+(?:my\s+)?(.+?)(?:\s+folder)?$",
            lowered.rstrip(".!?,")
        )
        if org_match:
            folder = org_match.group(1).strip().rstrip(".!?,")
            if folder in ("windows", "workspace", "workflow", "workshop", "work space", "screens", "apps", "tabs"):
                return self._handle_tile(lowered)
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
