"""
MakiAI — Screenshot Service
Full screen and active window screenshots.

Handles voice commands like:
  "take a screenshot"
  "screenshot"
  "capture the screen"
  "screenshot the active window"
"""

import pyautogui
from PIL import Image
from datetime import datetime
from pathlib import Path


class ScreenshotService:
    """
    Screenshot capture service for MakiAI.

    Captures full screen or active window and saves as .png.

    Usage:
        ss = ScreenshotService(save_path="C:\\Users\\Mark\\Pictures\\MakiAI")
        result = ss.capture_full()
        result = ss.capture_window()
    """

    def __init__(self, save_path: str = ""):
        """
        Args:
            save_path: Override save path. Defaults to MakiSync Storage/MakiAI/Screenshots.
        """
        from services.storage.maki_sync import get_maki_path
        self._screenshots_root = Path(save_path) if save_path else get_maki_path("Screenshots")
        self._screenshots_root.mkdir(parents=True, exist_ok=True)

    @property
    def save_path(self) -> Path:
        """Current dated screenshots folder."""
        from services.storage.maki_sync import get_dated_folder
        return get_dated_folder("Screenshots")

    # ─── Full Screen ─────────────────────────────────────────────────────────

    def capture_full(self) -> str:
        """
        Capture the entire screen, save as .png, and open immediately.

        Returns:
            Response string with file path, or error message.
        """
        try:
            screenshot = pyautogui.screenshot()
            filepath = self._save(screenshot, "screenshot")
            print(f"[ScreenshotService] Full screenshot saved: {filepath}")

            # Auto-open screenshot immediately and reveal its folder
            try:
                import os, subprocess
                os.startfile(str(filepath))
                subprocess.Popen(f'explorer /select,"{filepath}"')
            except Exception as ex:
                print(f"[ScreenshotService] Auto-open failed: {ex}")

            return f"Screenshot saved and opened from MakiSync Storage. {filepath.parent.name}/{filepath.name}"

        except Exception as e:
            print(f"[ScreenshotService] Full screenshot error: {e}")
            return f"I couldn't take a screenshot: {e}"

    # ─── Active Window ────────────────────────────────────────────────────────

    def capture_window(self) -> str:
        """
        Capture the currently active (foreground) window, save as .png, and open immediately.
        Falls back to full screenshot if window detection fails.

        Returns:
            Response string with file path, or error message.
        """
        try:
            import pygetwindow as gw

            active = gw.getActiveWindow()
            if not active:
                return self.capture_full()

            # Get window bounds
            left = active.left
            top = active.top
            width = active.width
            height = active.height

            if width <= 0 or height <= 0:
                return self.capture_full()

            # Capture just the window region
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            title = active.title[:20].strip() or "window"
            # Sanitize title for filename
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
            filepath = self._save(screenshot, f"window_{safe_title}" if safe_title else "window")

            print(f"[ScreenshotService] Window screenshot saved: {filepath}")

            # Auto-open screenshot immediately and reveal its folder
            try:
                import os, subprocess
                os.startfile(str(filepath))
                subprocess.Popen(f'explorer /select,"{filepath}"')
            except Exception as ex:
                print(f"[ScreenshotService] Auto-open failed: {ex}")

            return f"Screenshot of '{active.title[:30]}' saved and opened from MakiSync Storage. {filepath.parent.name}/{filepath.name}"

        except ImportError:
            # pygetwindow not available — fall back to full screen
            return self.capture_full()
        except Exception as e:
            print(f"[ScreenshotService] Window screenshot error: {e}")
            return self.capture_full()

    # ─── Region ──────────────────────────────────────────────────────────────

    def capture_region(self, left: int, top: int, width: int, height: int) -> str:
        """
        Capture a specific screen region.

        Args:
            left, top:      Top-left corner coordinates.
            width, height:  Region dimensions.

        Returns:
            Response string with file path.
        """
        try:
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            filepath = self._save(screenshot, "region")
            return f"Region screenshot saved as {filepath.name}."
        except Exception as e:
            print(f"[ScreenshotService] Region screenshot error: {e}")
            return f"Couldn't capture that region: {e}"

    # ─── Internal ────────────────────────────────────────────────────────────

    def _save(self, image: Image.Image, prefix: str) -> Path:
        """
        Save a PIL Image with a timestamped filename.

        Args:
            image:  The PIL Image to save.
            prefix: Filename prefix (e.g. "screenshot", "window").

        Returns:
            Path to the saved file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.png"
        filepath = self.save_path / filename
        image.save(str(filepath))
        return filepath
