"""
MakiAI — Camera Service
Photo capture and video recording via OpenCV.

Handles voice commands like:
  "take a photo"
  "take a picture"
  "start recording"
  "stop recording"
  "analyze what you see" (Gemini Vision)
"""

try:
    import cv2
except ImportError:
    cv2 = None
import os
import threading
from datetime import datetime
from pathlib import Path


class CameraService:
    """
    Webcam photo capture and video recording service.

    Uses OpenCV to access the default camera.
    Saves photos as .jpg and videos as .mp4 to configured paths.

    Usage:
        camera = CameraService(save_path="C:\\Users\\Mark\\Pictures\\MakiAI")
        result = camera.take_photo()
        camera.start_recording()
        camera.stop_recording()
    """

    def __init__(self, save_path: str = "", video_path: str = ""):
        """
        Args:
            save_path:  Override photo save path. Defaults to MakiSync Storage.
            video_path: Override video save path. Defaults to MakiSync Storage.
        """
        from services.storage.maki_sync import get_maki_path
        self._photos_root = Path(save_path) if save_path else get_maki_path("Photos")
        self._videos_root = Path(video_path) if video_path else get_maki_path("Recordings")

        self._photos_root.mkdir(parents=True, exist_ok=True)
        self._videos_root.mkdir(parents=True, exist_ok=True)

        self._recording = False
        self._record_thread: threading.Thread | None = None
        self._stop_recording_flag = False

    @property
    def save_path(self) -> Path:
        """Current dated photo folder."""
        from services.storage.maki_sync import get_dated_folder
        return get_dated_folder("Photos")

    @property
    def video_path(self) -> Path:
        """Current dated video folder."""
        from services.storage.maki_sync import get_dated_folder
        return get_dated_folder("Recordings")

    # ─── Photo ───────────────────────────────────────────────────────────────

    def take_photo(self) -> str:
        """
        Capture a single frame from the webcam, save as .jpg, and open immediately.

        Returns:
            Response string with file path, or error message.
        """
        cap = None
        try:
            # Try DirectShow device index 0, with standard fallback
            for dev_idx in [0, 1]:
                try:
                    cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap.release()
                        cap = cv2.VideoCapture(dev_idx)
                    if cap and cap.isOpened():
                        break
                except Exception:
                    if cap:
                        cap.release()
                    cap = None

            if not cap or not cap.isOpened():
                return "I couldn't access the camera. Make sure it's connected and not in use."

            # Allow camera exposure to warm up
            for _ in range(6):
                cap.read()
                import time
                time.sleep(0.04)

            ret, frame = cap.read()
            if not ret or frame is None:
                return "Failed to capture image from camera."

            # Save with timestamp filename in today's dated folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"photo_{timestamp}.jpg"
            filepath = self.save_path / filename

            cv2.imwrite(str(filepath), frame)
            print(f"[CameraService] Photo saved: {filepath}")

            # Auto-open the photo immediately and reveal its folder
            try:
                import subprocess
                os.startfile(str(filepath))
                subprocess.Popen(f'explorer /select,"{filepath}"')
            except Exception as ex:
                print(f"[CameraService] Auto-open failed: {ex}")

            return f"Photo captured and opened from MakiSync Storage. {filepath.parent.name}/{filepath.name}"

        except Exception as e:
            print(f"[CameraService] Photo error: {e}")
            return f"I couldn't take a photo: {e}"
        finally:
            if cap:
                cap.release()

    def capture_frame(self) -> tuple[bool, object]:
        """
        Capture a single frame without saving (for Gemini Vision).

        Returns:
            (success, frame) tuple. frame is a numpy array or None.
        """
        cap = None
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return False, None

            for _ in range(3):
                cap.read()

            ret, frame = cap.read()
            return ret, frame if ret else None

        except Exception as e:
            print(f"[CameraService] Frame capture error: {e}")
            return False, None
        finally:
            if cap:
                cap.release()

    def capture_frame_as_file(self) -> str | None:
        """
        Capture a frame and save to a temp file for Gemini Vision.

        Returns:
            Path to the saved image file, or None on failure.
        """
        import tempfile
        success, frame = self.capture_frame()
        if not success or frame is None:
            return None

        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            cv2.imwrite(tmp.name, frame)
            return tmp.name
        except Exception as e:
            print(f"[CameraService] Temp file error: {e}")
            return None

    # ─── Video Recording ─────────────────────────────────────────────────────

    def start_recording(self) -> str:
        """
        Start recording video from the webcam in a background thread.

        Returns:
            Response string.
        """
        if self._recording:
            return "I'm already recording. Say 'stop recording' to stop."

        self._recording = True
        self._stop_recording_flag = False

        self._record_thread = threading.Thread(
            target=self._record_loop,
            daemon=True,
            name="VideoRecordThread",
        )
        self._record_thread.start()
        return "Recording started. Say 'stop recording' when you're done."

    def stop_recording(self) -> str:
        """
        Stop an active recording.

        Returns:
            Response string with saved file path.
        """
        if not self._recording:
            return "I'm not currently recording."

        self._stop_recording_flag = True
        self._recording = False

        if self._record_thread:
            self._record_thread.join(timeout=3)

        return "Recording stopped and saved to your Videos folder."

    def is_recording(self) -> bool:
        return self._recording

    def _record_loop(self) -> None:
        """Background thread: record video until stop flag is set."""
        cap = None
        writer = None
        filepath = None

        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("[CameraService] Could not open camera for recording.")
                self._recording = False
                return

            # Get camera properties
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Set up video writer
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"video_{timestamp}.mp4"
            filepath = self.video_path / filename

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))

            print(f"[CameraService] Recording to: {filepath}")

            while not self._stop_recording_flag:
                ret, frame = cap.read()
                if not ret:
                    break
                writer.write(frame)

        except Exception as e:
            print(f"[CameraService] Recording error: {e}")
        finally:
            if writer:
                writer.release()
            if cap:
                cap.release()
            self._recording = False
            if filepath and filepath.exists():
                print(f"[CameraService] Video saved: {filepath}")
