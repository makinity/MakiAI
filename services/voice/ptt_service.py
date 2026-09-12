"""
MakiAI — Dedicated Push-to-Talk (PTT) Service
Provides low-latency, hardware-triggered voice recording via global hotkey
(e.g., Right Alt, Ctrl+Space, or F8).
Holding the key records direct audio stream buffers from the wireless lapel mic;
releasing it immediately dispatches the audio buffer to the STT engine.
"""

import io
import wave
import threading
import numpy as np
from typing import Optional, Callable
import sounddevice as sd
import speech_recognition as sr

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except Exception:
    KEYBOARD_AVAILABLE = False


class PushToTalkService:
    """
    Push-to-Talk service using global keyboard hooks and sounddevice buffer recording.
    """

    def __init__(
        self,
        hotkey: str = "right alt",
        on_ptt_start: Optional[Callable[[], None]] = None,
        on_ptt_end: Optional[Callable[[], None]] = None,
        on_result: Optional[Callable[[str], None]] = None,
        samplerate: int = 16000,
        channels: int = 1,
    ):
        """
        Args:
            hotkey: Global key trigger (e.g. "right alt", "ctrl+space", "f8").
            on_ptt_start: Callback when user presses & holds PTT hotkey.
            on_ptt_end: Callback when user releases PTT hotkey.
            on_result: Callback receiving final transcribed text.
            samplerate: 16000 Hz standard for voice recognition.
            channels: 1 (Mono).
        """
        self.hotkey = hotkey.lower().strip()
        self.on_ptt_start = on_ptt_start or (lambda: None)
        self.on_ptt_end = on_ptt_end or (lambda: None)
        self.on_result = on_result or (lambda text: None)
        self.samplerate = samplerate
        self.channels = channels

        self._recording = False
        self._audio_frames = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._recognizer = sr.Recognizer()

        self._active = False
        self.start_listener()

    def set_callbacks(
        self,
        on_ptt_start: Optional[Callable[[], None]] = None,
        on_ptt_end: Optional[Callable[[], None]] = None,
        on_result: Optional[Callable[[str], None]] = None,
    ) -> None:
        if on_ptt_start:
            self.on_ptt_start = on_ptt_start
        if on_ptt_end:
            self.on_ptt_end = on_ptt_end
        if on_result:
            self.on_result = on_result

    def start_listener(self) -> None:
        """Register low-level global hotkey hooks."""
        if self._active:
            return

        if KEYBOARD_AVAILABLE:
            try:
                # Handle single keys like 'right alt' or 'f8'
                keyboard.on_press_key(self.hotkey, self._on_key_down, suppress=False)
                keyboard.on_release_key(self.hotkey, self._on_key_up, suppress=False)
                self._active = True
                print(f"[PTTService] Global Push-to-Talk active on '{self.hotkey}'.")
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
            self._audio_frames = []

        print(f"[PTTService] PTT Engaged — Recording live stream...")
        self.on_ptt_start()

        # Start sounddevice input stream
        def _audio_callback(indata, frames, time_info, status):
            if self._recording:
                self._audio_frames.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="int16",
                callback=_audio_callback,
            )
            self._stream.start()
        except Exception as e:
            print(f"[PTTService] InputStream error: {e}")
            self._recording = False

    def _on_key_up(self, event) -> None:
        """Triggered on hotkey release."""
        with self._lock:
            if not self._recording:
                return
            self._recording = False

        print(f"[PTTService] PTT Released — Processing {len(self._audio_frames)} audio frames...")
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self.on_ptt_end()

        # Process recorded audio in background thread
        threading.Thread(target=self._transcribe_and_dispatch, daemon=True).start()

    def _transcribe_and_dispatch(self) -> None:
        """Convert in-memory numpy frames to WAV and transcribe via Google STT."""
        if not self._audio_frames:
            return

        try:
            audio_data = np.concatenate(self._audio_frames, axis=0)
            if len(audio_data) < self.samplerate * 0.3:  # Less than 300ms is too short
                print("[PTTService] Audio too brief — discarded.")
                return

            # Write WAV into memory buffer
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.samplerate)
                wf.writeframes(audio_data.tobytes())

            wav_buffer.seek(0)

            # Read with SpeechRecognition AudioFile
            with sr.AudioFile(wav_buffer) as source:
                audio = self._recognizer.record(source)

            # Transcribe
            text = self._recognizer.recognize_google(audio, language="en-US").strip()
            print(f"[PTTService] Transcribed: '{text}'")

            if text and self.on_result:
                self.on_result(text)

        except sr.UnknownValueError:
            print("[PTTService] Could not understand speech in PTT recording.")
        except sr.RequestError as e:
            print(f"[PTTService] STT API error: {e}")
        except Exception as e:
            print(f"[PTTService] Transcription error: {e}")
