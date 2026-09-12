"""
MakiAI — Screen Vision & Contextual Awareness Service
Provides ultra-fast in-memory frame buffer capture (sub-50ms via mss),
smart hybrid window/full-screen cropping, and multi-modal LLM analysis
to debug errors, explain terminal crashes, and summarize documents on screen.
"""

import io
import re
import time
from typing import Optional, Dict
from PIL import Image

try:
    import mss
except ImportError:
    mss = None

from services.computer.window_manager import WindowManager


class ScreenVisionService:
    """
    Contextual Screen Awareness Service.
    Captures live frame buffers directly into memory and passes them to the AI
    for instant visual OCR, code debugging, and screen question answering.
    """

    def __init__(self):
        self.window_mgr = WindowManager()

    def capture_screen_buffer(
        self,
        app_target: Optional[str] = None,
        max_dim: int = 1600,
        quality: int = 85
    ) -> Optional[Image.Image]:
        """
        Grab a memory-direct frame buffer of the target window or screen.

        Args:
            app_target: Target app alias/name e.g. "terminal", "vscode", "chrome", "active".
            max_dim: Maximum width/height dimension for token optimization.
            quality: JPEG compression quality (80-85% optimal for OCR sharpness).

        Returns:
            PIL Image instance (in-memory).
        """
        img = None

        # 1. Hybrid Selector: Active Window Crop if specified or detected
        if app_target and app_target.strip():
            win = self.window_mgr.find_window(app_target.strip())
            if win and win.get("rect"):
                left, top, right, bottom = win["rect"]
                w, h = right - left, bottom - top
                if w > 50 and h > 50:
                    try:
                        if mss:
                            with mss.mss() as sct:
                                monitor_dict = {"left": left, "top": top, "width": w, "height": h}
                                sct_img = sct.grab(monitor_dict)
                                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                        else:
                            from PIL import ImageGrab
                            img = ImageGrab.grab(bbox=(left, top, right, bottom))
                    except Exception as e:
                        print(f"[ScreenVision] Window crop capture error: {e}")

        # 2. Default: Full Screen / Active Monitor Capture
        if img is None:
            try:
                if mss:
                    with mss.mss() as sct:
                        # Grab all monitors or primary monitor
                        monitors = self.window_mgr.get_monitors()
                        # If active window is on a specific monitor, capture that monitor
                        active_win = self.window_mgr.find_window("active")
                        target_mon = None
                        if active_win and active_win.get("rect"):
                            target_mon = self.window_mgr.get_monitor_for_rect(active_win["rect"])

                        if target_mon:
                            mon_dict = {
                                "left": target_mon["left"],
                                "top": target_mon["top"],
                                "width": target_mon["width"],
                                "height": target_mon["height"],
                            }
                            sct_img = sct.grab(mon_dict)
                        else:
                            # Primary display
                            sct_img = sct.grab(sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0])

                        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                else:
                    from PIL import ImageGrab
                    img = ImageGrab.grab()
            except Exception as e:
                print(f"[ScreenVision] Full screen capture error: {e}")

        if img is None:
            return None

        # Convert to RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Downscale if larger than max_dim to maintain low latency and token efficiency
        if max(img.width, img.height) > max_dim:
            ratio = max_dim / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        return img

    def analyze(self, query: str, ai_service) -> str:
        """
        Analyze the current screen / window based on user's query.

        Args:
            query: The user's voice/text question about what's on screen.
            ai_service: GeminiService instance with multimodal capability.

        Returns:
            Direct, spoken-ready analysis from MakiAI.
        """
        if not ai_service or not ai_service.is_ready:
            return "I need an active Gemini or Groq API key with vision support configured in settings to inspect your screen, sir."

        # Detect if query specifies an application window (hybrid selector)
        app_target = None
        lowered = query.lower()

        if re.search(r"\b(terminal|console|cmd|powershell|bash)\b", lowered):
            app_target = "code" if not self.window_mgr.find_window("powershell") else "powershell"
        elif re.search(r"\b(vscode|vs code|code|editor|ide)\b", lowered):
            app_target = "vscode"
        elif re.search(r"\b(browser|chrome|edge|webpage|website)\b", lowered):
            app_target = "chrome"
        elif re.search(r"\b(notepad|text file|notes)\b", lowered):
            app_target = "notepad"
        elif re.search(r"\b(this window|this app|active window|here)\b", lowered):
            app_target = "active"

        # Capture frame buffer
        img = self.capture_screen_buffer(app_target=app_target)
        if img is None:
            return "I was unable to capture your screen buffer, sir. Please try again."

        system_instruction = (
            "You are MakiAI, personal AI assistant for Mark Vencent Juntilla. Address the user as 'sir'.\n"
            "You are looking directly at what is on the user's computer screen.\n"
            "If the user asks to debug an error or crash: identify the error message, explain the root cause, and give the exact fix.\n"
            "If the user asks to summarize or explain: give a concise, intelligent, high-level summary.\n"
            "Keep the response concise, natural, and conversational for speech. No markdown formatting or bullet points."
        )

        return ai_service.send_with_image(query, img, system_instruction)
