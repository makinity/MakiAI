"""
MakiAI — Wake Word Service
Single-phrase mode: captures wake word + command in ONE listen call.
No second mic open needed — the command is extracted from the same audio.

Example: "Hey Maki what's the weather" → wakes AND captures "what's the weather"
If only wake word heard: fires on_wake with empty command, caller does second listen.
"""

import threading
import speech_recognition as sr
from typing import Callable


AMBIENT_NOISE_SECONDS = 0.5
VOICE_TIMEOUT_SECONDS = 6
PHRASE_LIMIT_SECONDS  = 8

WAKE_VARIANTS = [
    "hey maki", "hi maki", "ok maki", "okay maki",
    "hey macky", "hi macky", "hey mackie", "hi mackie",
    "hey lucky", "hey marquee", "hey marky", "hey matty",
    "maki", "macky", "mackie", "lucky", "matty",
]


def _strip_wake_word(text: str) -> str:
    """Remove wake word from beginning of text, return the remainder."""
    lowered = text.lower().strip()
    for phrase in sorted(WAKE_VARIANTS, key=len, reverse=True):
        if lowered == phrase:
            return ""
        if lowered.startswith(phrase + " "):
            return text[len(phrase):].strip()
        if lowered.startswith(phrase + ","):
            return text[len(phrase)+1:].strip()
    return text


def _contains_wake_word(text: str) -> bool:
    lowered = text.lower().strip()
    for phrase in WAKE_VARIANTS:
        if lowered == phrase or lowered.startswith(phrase + " ") or phrase in lowered:
            return True
    return False


class WakeWordService:
    """
    Single-phrase wake word + command capture.
    Opens the mic ONCE per cycle, captures a full phrase,
    checks for wake word, extracts command, then fires callback.
    """

    def __init__(
        self,
        wake_word: str = "hey maki",
        on_wake: Callable[[], None] = None,
        on_wake_with_command: Callable[[str], None] = None,
        on_error: Callable[[str], None] = None,
        sensitivity: float = 0.6,
        access_key: str = "",
    ):
        self.wake_word = wake_word
        self.on_wake = on_wake or (lambda: None)
        self.on_wake_with_command = on_wake_with_command  # New: fires with command text
        self.on_error = on_error or (lambda msg: print(f"[WakeWordService] {msg}"))

        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop,
            name="WakeWordThread",
            daemon=True,
        )
        self._thread.start()
        print(f"[WakeWordService] Listening for: '{self.wake_word}'")
        return True

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def _listen_loop(self) -> None:
        print("[WakeWordService] Starting listen loop...")

        # One shared recognizer + microphone for the whole loop
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 1.2
        recognizer.non_speaking_duration = 0.8
        recognizer.phrase_threshold = 0.1
        recognizer.energy_threshold = 300

        while self._running:
            try:
                with sr.Microphone() as source:
                    # Calibrate once per open
                    recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_NOISE_SECONDS)

                    try:
                        audio = recognizer.listen(
                            source,
                            timeout=VOICE_TIMEOUT_SECONDS,
                            phrase_time_limit=PHRASE_LIMIT_SECONDS,
                        )
                    except sr.WaitTimeoutError:
                        continue

                # Transcribe outside the mic context
                try:
                    text = recognizer.recognize_google(audio, language="en-US")
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    print(f"[WakeWordService] API error: {e}")
                    continue

                print(f"[WakeWordService] Heard: '{text}'")

                if not _contains_wake_word(text):
                    continue

                # Extract command from same phrase
                command = _strip_wake_word(text)
                print(f"[WakeWordService] Wake detected. Command: '{command}'")

                if command and self.on_wake_with_command:
                    # Has command — pass directly, skip second STT
                    try:
                        self.on_wake_with_command(command)
                    except Exception as e:
                        print(f"[WakeWordService] on_wake_with_command error: {e}")
                else:
                    # No command — fire standard wake callback for second STT listen
                    try:
                        self.on_wake()
                    except Exception as e:
                        print(f"[WakeWordService] on_wake error: {e}")

            except OSError as e:
                print(f"[WakeWordService] Mic error: {e}")
                import time
                time.sleep(2)
            except Exception as e:
                if self._running:
                    print(f"[WakeWordService] Loop error: {e}")
