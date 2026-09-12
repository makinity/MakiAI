"""
MakiAI — System Control
Controls Windows system functions by voice.

Handles commands like:
  "volume up / down / mute"
  "set volume to 50"
  "shutdown / restart / sleep / lock"
  "brightness up / down"
"""

import os
import subprocess
import ctypes
from ctypes import cast, POINTER
from typing import Optional


class SystemControl:
    """
    Windows system control service for MakiAI.

    Controls: volume, shutdown, restart, sleep, lock screen, brightness.
    Uses pycaw for precise volume control and ctypes/subprocess for system ops.

    Usage:
        sc = SystemControl()
        sc.set_volume(70)
        sc.volume_up()
        sc.shutdown()
        sc.lock()
    """

    def __init__(self):
        self._volume_interface = None
        self._init_volume()

    # ─── Volume ──────────────────────────────────────────────────────────────

    def _init_volume(self) -> None:
        """Initialize pycaw volume interface."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            self._volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            print("[SystemControl] Volume interface initialized.")
        except Exception as e:
            print(f"[SystemControl] Volume init failed: {e}")

    def get_volume(self) -> int:
        """Get current system volume as 0–100 integer."""
        if self._volume_interface:
            try:
                scalar = self._volume_interface.GetMasterVolumeLevelScalar()
                return int(scalar * 100)
            except Exception:
                pass
        return -1

    def set_volume(self, level: int) -> str:
        """
        Set system volume to a specific level and unmute.

        Args:
            level: 0–100 integer.

        Returns:
            Response string.
        """
        level = max(0, min(100, level))

        if self._volume_interface:
            try:
                # Automatically unmute if setting positive volume
                if level > 0:
                    try:
                        self._volume_interface.SetMute(0, None)
                    except Exception:
                        pass
                elif level == 0:
                    try:
                        self._volume_interface.SetMute(1, None)
                    except Exception:
                        pass

                self._volume_interface.SetMasterVolumeLevelScalar(
                    level / 100.0, None
                )
                return f"Volume set to {level}%."
            except Exception as e:
                print(f"[SystemControl] Set volume error: {e}")

        # Fallback: use nircmd if available
        return self._nircmd_volume(level)

    def volume_up(self, step: int = 10) -> str:
        """Increase volume by step amount and ensure unmuted."""
        current = self.get_volume()
        if current >= 0:
            return self.set_volume(current + step)
        # Fallback
        self.unmute()
        self._send_volume_key(0xAF)  # VK_VOLUME_UP
        return "Volume increased."

    def volume_down(self, step: int = 10) -> str:
        """Decrease volume by step amount."""
        current = self.get_volume()
        if current >= 0:
            return self.set_volume(current - step)
        # Fallback
        self._send_volume_key(0xAE)  # VK_VOLUME_DOWN
        return "Volume decreased."

    def unmute(self) -> str:
        """Explicitly unmute audio."""
        if self._volume_interface:
            try:
                self._volume_interface.SetMute(0, None)
                return "Unmuted."
            except Exception as e:
                print(f"[SystemControl] Unmute error: {e}")
        return "Audio unmuted."

    def mute(self, state: Optional[bool] = None) -> str:
        """Mute or toggle mute."""
        if self._volume_interface:
            try:
                is_muted = bool(self._volume_interface.GetMute())
                new_state = (not is_muted) if state is None else bool(state)
                self._volume_interface.SetMute(new_state, None)
                return "Muted." if new_state else "Unmuted."
            except Exception as e:
                print(f"[SystemControl] Mute error: {e}")

        self._send_volume_key(0xAD)  # VK_VOLUME_MUTE
        return "Toggled mute."

    def _send_volume_key(self, vk_code: int) -> None:
        """Send a virtual key press via ctypes."""
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        except Exception as e:
            print(f"[SystemControl] Key event error: {e}")

    def _nircmd_volume(self, level: int) -> str:
        """Fallback volume control using nircmd if available."""
        try:
            val = int(level / 100 * 65535)
            subprocess.run(["nircmd", "setsysvolume", str(val)], check=True)
            return f"Volume set to {level}%."
        except Exception:
            return f"Volume control unavailable. Please adjust manually."

    # ─── System Power ────────────────────────────────────────────────────────

    def shutdown(self, delay_seconds: int = 10) -> str:
        """
        Shut down the PC after a delay.

        Args:
            delay_seconds: Seconds before shutdown (default 10, gives time to cancel).

        Returns:
            Response string.
        """
        try:
            subprocess.run(
                ["shutdown", "/s", "/t", str(delay_seconds)],
                check=True
            )
            return f"Shutting down in {delay_seconds} seconds. Say 'cancel shutdown' to abort."
        except Exception as e:
            print(f"[SystemControl] Shutdown error: {e}")
            return "I couldn't initiate shutdown."

    def cancel_shutdown(self) -> str:
        """Cancel a pending shutdown."""
        try:
            subprocess.run(["shutdown", "/a"], check=True)
            return "Shutdown cancelled."
        except Exception as e:
            return "No pending shutdown to cancel."

    def restart(self, delay_seconds: int = 10) -> str:
        """Restart the PC after a delay."""
        try:
            subprocess.run(
                ["shutdown", "/r", "/t", str(delay_seconds)],
                check=True
            )
            return f"Restarting in {delay_seconds} seconds."
        except Exception as e:
            print(f"[SystemControl] Restart error: {e}")
            return "I couldn't initiate restart."

    def sleep(self) -> str:
        """Put the PC to sleep."""
        try:
            subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                check=True
            )
            return "Going to sleep."
        except Exception as e:
            print(f"[SystemControl] Sleep error: {e}")
            return "I couldn't put the PC to sleep."

    def lock(self) -> str:
        """Lock the Windows screen."""
        try:
            ctypes.windll.user32.LockWorkStation()
            return "Screen locked."
        except Exception as e:
            print(f"[SystemControl] Lock error: {e}")
            return "I couldn't lock the screen."

    # ─── Brightness ──────────────────────────────────────────────────────────

    def set_brightness(self, level: int) -> str:
        """
        Set screen brightness (laptop displays only).

        Args:
            level: 0–100 integer.

        Returns:
            Response string.
        """
        level = max(0, min(100, level))
        try:
            script = (
                f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1,{level})"
            )
            subprocess.run(
                ["powershell", "-Command", script],
                check=True,
                capture_output=True,
            )
            return f"Brightness set to {level}%."
        except Exception as e:
            print(f"[SystemControl] Brightness error: {e}")
            return "Brightness control is not available on this display."

    def brightness_up(self, step: int = 10) -> str:
        """Increase brightness by step."""
        try:
            current = self._get_brightness()
            return self.set_brightness(current + step)
        except Exception:
            return self.set_brightness(70)

    def brightness_down(self, step: int = 10) -> str:
        """Decrease brightness by step."""
        try:
            current = self._get_brightness()
            return self.set_brightness(current - step)
        except Exception:
            return self.set_brightness(40)

    def _get_brightness(self) -> int:
        """Get current screen brightness via WMI."""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
                capture_output=True, text=True, check=True
            )
            return int(result.stdout.strip())
        except Exception:
            return 50
