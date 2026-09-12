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
    "hey maki", "hi maki", "hello maki", "ok maki", "okay maki", "yo maki",
    "hey macky", "hi macky", "hello macky", "hey mackie", "hi mackie",
    "hey marky", "hi marky", "hello marky", "hey marquee", "hi marquee",
    "hey lucky", "hi lucky", "hey monkey", "hi monkey", "hey mark", "hi mark",
    "maki", "macky", "mackie", "marky", "lucky", "matty",
]


DIRECT_COMMAND_STARTERS = [
    "volume", "set volume", "set the volume", "up the volume", "down the volume",
    "turn up", "turn down", "mute", "unmute", "silence", "louder", "quieter",
    "open", "launch", "start", "run", "close", "kill",
    "tile", "auto-tile", "autotile", "maximize", "move window", "drag window", "snap",
    "what am i", "what is", "what are", "what's", "look at", "see my",
    "is there anyone", "who is", "check the", "tell me", "how is my",
    "take a photo", "take a picture", "take a screenshot", "start recording", "stop recording",
    "good morning", "good night", "play", "pause", "skip",
    "shutdown", "restart", "lock screen", "sleep", "hibernate", "how are you", "hello", "hi"
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


def _is_direct_command(text: str) -> bool:
    """Check if phrase starts with an unambiguous computer control action or question."""
    lowered = text.lower().strip()
    for starter in DIRECT_COMMAND_STARTERS:
        if lowered == starter or lowered.startswith(starter + " ") or lowered.startswith(starter + ","):
            return True
    return False


class WakeWordService:
    """
    Single-phrase wake word + direct command capture.
    Opens the mic per cycle, captures a full phrase,
    checks for wake word or direct commands, extracts intent, and fires callbacks.
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
        self.on_wake_with_command = on_wake_with_command  # Fires with command text
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
        print(f"[WakeWordService] Listening for: '{self.wake_word}' & direct commands...")
        return True

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def _listen_loop(self) -> None:
        print("[WakeWordService] Starting listen loop...")

        # One shared recognizer for the loop
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 1.0
        recognizer.non_speaking_duration = 0.6
        recognizer.phrase_threshold = 0.1
        recognizer.energy_threshold = 300

        while self._running:
            try:
                with sr.Microphone() as source:
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

                has_wake = _contains_wake_word(text)
                is_direct = _is_direct_command(text)

                if not has_wake and not is_direct:
                    continue

                if has_wake:
                    command = _strip_wake_word(text)
                else:
                    command = text.strip()

                print(f"[WakeWordService] Trigger detected. Command: '{command}'")

                if command and self.on_wake_with_command:
                    try:
                        self.on_wake_with_command(command)
                    except Exception as e:
                        print(f"[WakeWordService] on_wake_with_command error: {e}")
                else:
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
