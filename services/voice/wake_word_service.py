"""
MakiAI — Wake Word Service
Single-phrase mode: captures wake word + command in ONE listen call.
No second mic open needed — the command is extracted from the same audio.

Example: "Hey Maki what's the weather" → wakes AND captures "what's the weather"
If only wake word heard: fires on_wake with empty command, caller does second listen.
"""

import re
import threading
import speech_recognition as sr
from typing import Callable, Optional
from services.voice.audio_transcriber import AudioTranscriber


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

DIRECT_COMMAND_PATTERNS = [
    # System volume & audio
    r"^(?:set\s+(?:the\s+)?)?volume\s+(?:to\s+)?(?:\d+|up|down|max|half|zero)\b",
    r"^(?:turn\s+(?:up|down)\s+(?:the\s+)?volume|volume\s+(?:up|down)|louder|quieter|mute|unmute|silence)$",
    
    # App launch & close
    r"^(?:open|launch|start|run|close|kill)\s+(?:google\s+chrome|chrome|vs\s+code|vscode|spotify|discord|terminal|notepad|calculator|word|excel|zoom|[a-zA-Z0-9_\-]+)\b",
    
    # Window management, tiling & workspace
    r"^(?:organize|tile|auto-tile|autotile|maximize|minimize|restore|snap|move\s+window|drag\s+window|fit\s+windows?|arrange)\b",
    r"^(?:organize|clean\s+up|sort)\s+(?:my\s+)?(?:workspace|workflow|workshop|work\s+space|windows?|downloads?|desktop|files?|documents?)\b",
    
    # Media controls
    r"^(?:play|pause|resume|skip|next\s+song|previous\s+song|stop\s+music)\b",
    
    # Vision & Camera
    r"^(?:take\s+a\s+(?:photo|picture|screenshot)|look\s+at\s+my\s+screen|see\s+my\s+screen|what\s+is\s+on\s+my\s+screen|look\s+through\s+my\s+camera|who\s+is\s+in\s+front\s+of\s+me)\b",
    
    # Information & Knowledge Base
    r"^(?:good\s+morning|good\s+night)\b",
    r"^(?:can\s+you\s+)?(?:please\s+)?(?:what\s+is|what's|show|check|list|provide|give|tell\s+me|get)\s+(?:a\s+|the\s+|my\s+|our\s+)?(?:list\s+of\s+)?(?:schedule|deadlines?|reminders?|tasks?)\b",
    r"^(?:can\s+you\s+)?(?:please\s+)?(?:remind\s+me|set\s+(?:a\s+)?reminder|tell\s+me\s+later|alert\s+me|notify\s+me)\b",
    r"^(?:remember\s+that|forget\s+about)\b",
    r"^(?:can\s+you\s+)?(?:just\s+)?(?:remove|delete|cancel|clear|forget)\s+(?:it|this|about\s+the|the)\b",
    r"^(?:cancel|remove|delete)\s+(?:the\s+)?(?:zoom\s+meeting|meeting|schedule|event|reminder|deadline)\b",
    
    # Cloud & SaaS Operations (Composio)
    r"^(?:can\s+you\s+)?(?:please\s+)?(?:check|read|fetch|get|open|view)\s+(?:my\s+)?(?:gmail|emails?|inbox|unread\s+emails?)\b",
    r"^(?:can\s+you\s+)?(?:please\s+)?(?:send|draft|compose)\s+(?:an?\s+)?(?:email|mail)\b",
    
    # Pleasantries & Acknowledgments
    r"^(?:thank\s+you|thanks|thanks\s+a\s+lot|thank\s+you\s+very\s+much|good\s+job)[.,?!]?$",
    
    # Live Search & URL Reading
    r"^(?:search\s+(?:the\s+web\s+|google\s+|online\s+)?for|google|look\s+up|research)\s+[a-zA-Z0-9_\-\s]+",
    r"^(?:read|check|summarize)\s+(?:this\s+)?(?:link|url|website|page|article)\b",
    r"https?://[^\s]+",
    
    # Video Clipping & Viral Shorts (DeepClip)
    r"^(?:find\s+clips?|create\s+clips?|make\s+clips?|clip\s+this|clip\s+(?:the\s+)?video|extract\s+clips?|viral\s+shorts?)\b",
    r"^(?:clip|slice)\s+(?:the\s+)?(?:best\s+moments|highlights|viral\s+moments|latest\s+recording|my\s+video)\b",
    r"^(?:deep\s*clip|deepclip)\b",
    
    # Power
    r"^(?:shutdown|restart|lock\s+screen|hibernate)\b",
    
    # Kiro CLI
    r"^(?:t=kiro|open\s+kiro|launch\s+kiro)\b",
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
    """Check if phrase matches an unambiguous, actionable command structure."""
    lowered = text.lower().strip().rstrip(".!?,")
    if len(lowered) < 3:
        return False
    for pat in DIRECT_COMMAND_PATTERNS:
        if re.search(pat, lowered):
            return True
    return False


class WakeWordService:
    """
    Single-phrase wake word + direct command capture with acoustic echo gating.
    """

    def __init__(
        self,
        wake_word: str = "hey maki",
        on_wake: Callable[[], None] = None,
        on_wake_with_command: Callable[[str], None] = None,
        on_error: Callable[[str], None] = None,
        sensitivity: float = 0.6,
        access_key: str = "",
        tts_service: Optional[object] = None,
    ):
        self.wake_word = wake_word
        self.on_wake = on_wake or (lambda: None)
        self.on_wake_with_command = on_wake_with_command
        self.on_error = on_error or (lambda msg: print(f"[WakeWordService] {msg}"))
        self._tts_service = tts_service
        self._transcriber = AudioTranscriber()

        self._running = False
        self._thread: threading.Thread | None = None

    def set_tts_service(self, tts_service: object) -> None:
        self._tts_service = tts_service

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

                # Gate check: Discard audio captured while Maki is speaking or during reverb
                if self._tts_service and getattr(self._tts_service, "is_speaking_or_recent", lambda: False)(0.7):
                    continue

                # Transcribe outside the mic context using Groq Whisper / Google STT
                try:
                    wav_bytes = audio.get_wav_data()
                    text, provider = self._transcriber.transcribe_wav_bytes(wav_bytes)
                except Exception as e:
                    continue

                if not text:
                    continue

                # Secondary gate check right after transcription in case TTS started speaking during transcribe
                if self._tts_service and getattr(self._tts_service, "is_speaking_or_recent", lambda: False)(0.7):
                    continue

                print(f"[WakeWordService] Heard ({provider}): '{text}'")

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
