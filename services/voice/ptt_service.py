"""
MakiAI — Dedicated Push-to-Talk (PTT) Service (ptt_service.py)
Provides hardware-triggered voice recording via global hotkey (Right Alt) with:
  1. Continuous background pre-roll audio ring buffer (~300ms) to eliminate initial clipping
  2. Post-roll release padding (~120ms) to eliminate trailing clipping
  3. Ultra-fast Groq Whisper (whisper-large-v3-turbo) transcription with domain vocabulary biasing
  4. Google STT fallback for offline/limit resilience
"""

import io
import time
import collections
import threading
from typing import Optional, Callable
import numpy as np
import sounddevice as sd

from services.voice.audio_transcriber import AudioTranscriber

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except Exception:
    KEYBOARD_AVAILABLE = False


class PushToTalkService:
    """
    Hardware-triggered Push-to-Talk service with rolling pre-roll buffer and Whisper STT.
    """

    def __init__(
        self,
        hotkey: str = "right alt",
        on_ptt_start: Optional[Callable[[], None]] = None,
        on_ptt_end: Optional[Callable[[], None]] = None,
        on_result: Optional[Callable[[str], None]] = None,
        on_empty: Optional[Callable[[], None]] = None,
        samplerate: int = 16000,
        channels: int = 1,
    ):
        self.hotkey = hotkey.lower().strip()
        self.on_ptt_start = on_ptt_start or (lambda: None)
        self.on_ptt_end = on_ptt_end or (lambda: None)
        self.on_result = on_result or (lambda text: None)
        self.on_empty = on_empty or (lambda: None)
        self.samplerate = samplerate
        self.channels = channels

        self._recording = False
        self._audio_frames: list[np.ndarray] = []
        self._pre_roll_buffer = collections.deque(maxlen=12)  # ~300ms rolling ring buffer
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._transcriber = AudioTranscriber()

        self._active = False
        self._start_audio_stream()
        self.start_listener()

    def set_callbacks(
        self,
        on_ptt_start: Optional[Callable[[], None]] = None,
        on_ptt_end: Optional[Callable[[], None]] = None,
        on_result: Optional[Callable[[str], None]] = None,
        on_empty: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_ptt_start:
            self.on_ptt_start = on_ptt_start
        if on_ptt_end:
            self.on_ptt_end = on_ptt_end
        if on_result:
            self.on_result = on_result
        if on_empty:
            self.on_empty = on_empty

    def _start_audio_stream(self) -> None:
        """Keep a background input stream active to feed the pre-roll ring buffer."""
        def _callback(indata, frames, time_info, status):
            chunk = indata.copy()
            with self._lock:
                if self._recording:
                    self._audio_frames.append(chunk)
                else:
                    self._pre_roll_buffer.append(chunk)

        try:
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="int16",
                callback=_callback,
                blocksize=int(self.samplerate * 0.025),  # 25ms blocks
            )
            self._stream.start()
        except Exception as e:
            print(f"[PTTService] Background audio stream error: {e}")

    def start_listener(self) -> None:
        """Register low-level global hotkey hooks."""
        if self._active:
            return

        if KEYBOARD_AVAILABLE:
            try:
                keyboard.on_press_key(self.hotkey, self._on_key_down, suppress=False)
                keyboard.on_release_key(self.hotkey, self._on_key_up, suppress=False)
                self._active = True
                print(f"[PTTService] Global Push-to-Talk active on '{self.hotkey}' (Pre-roll buffer active).")
            except Exception as e:
                print(f"[PTTService] keyboard hook error on '{self.hotkey}': {e}. Trying fallback.")
                self._init_pynput_fallback()
        else:
            self._init_pynput_fallback()

    def _init_pynput_fallback(self) -> None:
        """Fallback to pynput if keyboard module encounters hook restriction."""
        try:
            from pynput import keyboard as pk

            def _on_press(key):
                key_name = str(key).lower().replace("key.", "")
                if self.hotkey in key_name:
                    self._on_key_down(None)

            def _on_release(key):
                key_name = str(key).lower().replace("key.", "")
                if self.hotkey in key_name:
                    self._on_key_up(None)

            listener = pk.Listener(on_press=_on_press, on_release=_on_release)
            listener.daemon = True
            listener.start()
            self._active = True
            print(f"[PTTService] pynput fallback active on '{self.hotkey}'.")
        except Exception as err:
            print(f"[PTTService] pynput fallback failed: {err}")

    # ─── Event Handlers ───────────────────────────────────────────────────────

    def _on_key_down(self, event) -> None:
        """Triggered on hotkey press."""
        with self._lock:
            if self._recording:
                return
            self._recording = True
            # Prepend pre-roll buffer so the very first word is preserved
            self._audio_frames = list(self._pre_roll_buffer)
            self._pre_roll_buffer.clear()

        print(f"[PTTService] PTT Engaged — Recording live stream...")
        self.on_ptt_start()

    def _on_key_up(self, event) -> None:
        """Triggered on hotkey release."""
        with self._lock:
            if not self._recording:
                return

        # Post-roll padding (~120ms) to ensure trailing word is captured
        time.sleep(0.12)

        with self._lock:
            self._recording = False
            frames_to_process = list(self._audio_frames)
            self._audio_frames = []

        print(f"[PTTService] PTT Released — Processing {len(frames_to_process)} audio frames...")
        self.on_ptt_end()

        # Process recorded audio in background thread
        threading.Thread(target=self._process_audio_frames, args=(frames_to_process,), daemon=True).start()

    def _process_audio_frames(self, frames: list[np.ndarray]) -> None:
        """Transcribe audio frames using Groq Whisper with Google STT fallback."""
        if not frames:
            self.on_empty()
            return

        try:
            total_samples = sum(len(f) for f in frames)
            if total_samples < self.samplerate * 0.25:  # Less than 250ms is too brief
                print("[PTTService] Audio too brief — discarded.")
                self.on_empty()
                return

            text, provider = self._transcriber.transcribe_numpy_frames(frames, self.samplerate, self.channels)

            if text:
                print(f"[PTTService] Transcribed ({provider}): '{text}'")
                if self.on_result:
                    self.on_result(text)
            else:
                print("[PTTService] Could not understand speech in PTT recording.")
                self.on_empty()

        except Exception as e:
            print(f"[PTTService] Audio processing error: {e}")
            self.on_empty()
