"""
MakiAI — Physical Vision & Webcam Context Module (camera_tool.py)
Provides high-speed in-memory webcam frame capture, sensor auto-exposure warmup,
direct base64 JPEG encoding, and multimodal AI analysis to answer physical context
questions (user activity, posture, held objects, and people in the background).
"""

import io
import time
import base64
from typing import Optional, Tuple
from PIL import Image

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
    OPENCV_AVAILABLE = False


def capture_webcam_frame(
    camera_index: int = 0,
    max_width: int = 1280,
    quality: int = 85,
    warmup_seconds: float = 0.3,
) -> Tuple[Optional[Image.Image], Optional[str], Optional[str]]:
    """
    Capture a single optical frame from the primary laptop webcam into memory.

    Performs a brief sensor warmup (~0.3s) so auto-exposure and white balance
    settle cleanly, resizes to a max width of 1280px, and encodes directly
    into base64 JPEG format.

    Guarantees the camera device hardware handle is properly released in a
    finally block immediately after capture so the hardware lock and webcam LED turn off.

    Args:
        camera_index: Camera device index (0 = default webcam).
        max_width: Maximum width dimension for payload optimization.
        quality: JPEG compression quality (85% optimal for edge sharpness).
        warmup_seconds: Sensor exposure calibration duration (~0.3s).

    Returns:
        Tuple of (PIL Image, Base64 JPEG string, Error Message if any).
    """
    if not OPENCV_AVAILABLE:
        return None, None, "OpenCV (opencv-python) is not installed in the current environment."

    cap = None
    try:
        # Try device index 0, then 1 if 0 is unavailable or invalid
        for dev_idx in [camera_index, 1, 2]:
            try:
                print(f"[CameraTool] Attempting webcam connection on device index {dev_idx}...")
                cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap.release()
                    cap = cv2.VideoCapture(dev_idx)
                if cap and cap.isOpened():
                    print(f"[CameraTool] Webcam connected successfully on device index {dev_idx}.")
                    break
            except Exception as e:
                print(f"[CameraTool] Index {dev_idx} failed: {e}")
                if cap:
                    cap.release()
                cap = None

        if not cap or not cap.isOpened():
            return None, None, "I could not access your webcam, sir. Please check if another application is using it or if it is connected."

        # Sensor warmup & buffer flush (~0.35s) to allow auto-exposure / white-balance to calibrate
        warmup_frames = max(4, int(warmup_seconds / 0.05))
        for _ in range(warmup_frames):
            cap.read()
            time.sleep(0.04)

        ret, frame = cap.read()
        if not ret or frame is None:
            return None, None, "Failed to capture image frame from the webcam."

        print(f"[CameraTool] Frame captured successfully ({frame.shape[1]}x{frame.shape[0]}).")

        # Convert BGR (OpenCV) to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Downscale to max_width while preserving aspect ratio
        h, w = rgb_frame.shape[:2]
        if w > max_width:
            scale = max_width / float(w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            rgb_frame = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Convert to PIL Image
        pil_img = Image.fromarray(rgb_frame)

        # Direct in-memory Base64 JPEG encoding
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=quality)
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

        return pil_img, b64_str, None

    except Exception as e:
        print(f"[CameraTool] Webcam capture error: {e}")
        return None, None, f"An error occurred while accessing the webcam: {e}"

    finally:
        # Guarantee hardware release so camera LED turns off immediately
        if cap is not None:
            try:
                cap.release()
                print("[CameraTool] Webcam hardware handle released.")
            except Exception:
                pass
        if OPENCV_AVAILABLE:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass


def analyze_camera_feed(user_query: str, ai_service) -> str:
    """
    Capture webcam frame and execute multimodal vision inference to answer
    questions about physical context (user actions, held objects, background people).

    Args:
        user_query: The user's spoken or typed question.
        ai_service: GeminiService instance with multimodal vision capabilities.

    Returns:
        Direct, spoken-ready answer from MakiAI.
    """
    if not ai_service or not ai_service.is_ready:
        return "I need an active Gemini or Groq API key with vision support configured in settings to inspect your camera feed, sir."

    pil_img, b64_str, error_msg = capture_webcam_frame()
    if pil_img is None or error_msg:
        return error_msg or "I was unable to capture a frame from your webcam, sir. Please try again."

    system_instruction = (
        "You are MakiAI, personal AI assistant for Mark Vencent Juntilla. Address the user as 'sir'.\n"
        "You are looking directly through the user's laptop webcam in real-time.\n"
        "Pay special attention to:\n"
        "1. The user's current physical activity, posture, and facial expressions (e.g. typing, writing, drinking, eating, reading, smiling, working).\n"
        "2. Any physical objects held in the user's hands or sitting directly in front of them (e.g. coffee mug, water bottle, smartphone, notebook, pen, electronics, tools).\n"
        "3. The presence of other people, colleagues, or movement in the background room behind the user.\n"
        "Answer the user's specific question directly, accurately, and naturally based on what is visible in the camera frame.\n"
        "Keep the response concise, intelligent, and conversational for text-to-speech. Do not use markdown asterisks or bullet points."
    )

    try:
        return ai_service.send_with_image(user_query, pil_img, system_instruction)
    except Exception as e:
        print(f"[CameraTool] Multimodal inference error: {e}")
        return "I encountered an issue analyzing the webcam image, sir. Please try again."


class CameraTool:
    """Class wrapper for integration into MakiAI Computer subsystem."""

    def __init__(self):
        pass

    def capture_frame(self, max_width: int = 1280, quality: int = 85) -> Tuple[Optional[Image.Image], Optional[str], Optional[str]]:
        return capture_webcam_frame(max_width=max_width, quality=quality)

    def analyze(self, query: str, ai_service) -> str:
        return analyze_camera_feed(query, ai_service)
