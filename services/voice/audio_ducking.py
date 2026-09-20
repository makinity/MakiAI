"""
MakiAI — Audio Ducking Service
Programmatically scales master/app playback volume during TTS speech
using Windows Core Audio APIs (pycaw).
Prevents mic audio feedback and ensures MakiAI's voice is crystal clear over music/media.
"""

import threading
from typing import Optional
from ctypes import cast, POINTER

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    PYCAW_AVAILABLE = True
except Exception:
    PYCAW_AVAILABLE = False


class AudioDuckingService:
    """
    Manages optional Windows audio attenuation (ducking) during speech synthesis.
    Disabled by default to keep master PC volume untouched.
    """

    def __init__(self, duck_ratio: float = 0.30, enabled: Optional[bool] = None):
        """
        Args:
            duck_ratio: Fraction of current volume to keep while ducked (e.g., 0.30 = 30%).
            enabled:    Explicit boolean or reads AUDIO_DUCKING from .env (default: False).
        """
        import os
        if enabled is not None:
            self.enabled = bool(enabled)
        else:
            self.enabled = os.getenv("AUDIO_DUCKING", "false").lower() in ("true", "1", "yes")

        self.duck_ratio = max(0.05, min(0.9, duck_ratio))
        self._original_volume: Optional[float] = None
        self._is_ducked = False
        self._lock = threading.Lock()
        self._volume_interface = None
        if self.enabled:
            self._init_endpoint()

    def _init_endpoint(self) -> None:
        """Initialize default audio speaker endpoint interface."""
        if not PYCAW_AVAILABLE:
            return
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            self._volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            print(f"[AudioDucking] Pycaw speaker endpoint init warning: {e}")

    def duck(self) -> None:
        """Attenuate master speaker volume down during speech."""
        if not self.enabled:
            return

        with self._lock:
            if self._is_ducked:
                return

            if not self._volume_interface:
                self._init_endpoint()

            if self._volume_interface:
                try:
                    current_scalar = self._volume_interface.GetMasterVolumeLevelScalar()
                    self._original_volume = current_scalar
                    ducked_scalar = max(0.05, current_scalar * self.duck_ratio)
                    self._volume_interface.SetMasterVolumeLevelScalar(ducked_scalar, None)
                    self._is_ducked = True
                    print(f"[AudioDucking] Volume ducked: {int(current_scalar * 100)}% -> {int(ducked_scalar * 100)}%")
                except Exception as e:
                    print(f"[AudioDucking] Duck error: {e}")

    def unduck(self) -> None:
        """Restore master speaker volume back to pre-speech level."""
        if not self.enabled:
            return

        with self._lock:
            if not self._is_ducked or self._original_volume is None:
                return

            if self._volume_interface:
                try:
                    self._volume_interface.SetMasterVolumeLevelScalar(self._original_volume, None)
                    print(f"[AudioDucking] Volume restored: {int(self._original_volume * 100)}%")
                except Exception as e:
                    print(f"[AudioDucking] Unduck error: {e}")
                finally:
                    self._is_ducked = False
                    self._original_volume = None
