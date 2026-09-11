"""
MakiAI — Media Control
Controls media playback and Spotify via voice.

Handles commands like:
  "play / pause"
  "next track / previous track"
  "open Spotify"
  "volume up / down"
"""

import subprocess
import webbrowser
import ctypes


# Virtual key codes for media keys
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP       = 0xB2


class MediaControl:
    """
    Media playback control service for MakiAI.

    Controls system-level media keys (works with Spotify, YouTube,
    Windows Media Player, and any media app that listens to media keys).

    Usage:
        mc = MediaControl()
        mc.play_pause()
        mc.next_track()
        mc.open_spotify()
    """

    # ─── Playback ────────────────────────────────────────────────────────────

    def play_pause(self) -> str:
        """Toggle play/pause for the active media player."""
        self._press_media_key(VK_MEDIA_PLAY_PAUSE)
        return "Play/pause toggled."

    def next_track(self) -> str:
        """Skip to the next track."""
        self._press_media_key(VK_MEDIA_NEXT_TRACK)
        return "Skipping to next track."

    def previous_track(self) -> str:
        """Go back to the previous track."""
        self._press_media_key(VK_MEDIA_PREV_TRACK)
        return "Going to previous track."

    def stop(self) -> str:
        """Stop media playback."""
        self._press_media_key(VK_MEDIA_STOP)
        return "Playback stopped."

    # ─── Spotify ─────────────────────────────────────────────────────────────

    def open_spotify(self, desktop: bool = True) -> str:
        """
        Open Spotify — tries desktop app first, falls back to browser.

        Args:
            desktop: If True, tries to open the desktop app first.
        """
        if desktop:
            try:
                subprocess.Popen(
                    "spotify.exe",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return "Opening Spotify."
            except Exception:
                pass

        # Fallback to web player
        webbrowser.open("https://open.spotify.com")
        return "Opening Spotify in your browser."

    def play_on_spotify(self, query: str) -> str:
        """
        Open a Spotify search for a song/artist/playlist.

        Args:
            query: Search query string.

        Returns:
            Response string.
        """
        try:
            import urllib.parse
            encoded = urllib.parse.quote(query)
            url = f"https://open.spotify.com/search/{encoded}"
            webbrowser.open(url)
            return f"Searching Spotify for '{query}'."
        except Exception as e:
            print(f"[MediaControl] Spotify search error: {e}")
            return "Couldn't search Spotify right now."

    # ─── Internal ────────────────────────────────────────────────────────────

    def _press_media_key(self, vk_code: int) -> None:
        """
        Send a media key press using Windows virtual key codes.

        Args:
            vk_code: Windows virtual key code for the media action.
        """
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        except Exception as e:
            print(f"[MediaControl] Key press error: {e}")
