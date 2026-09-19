"""
MakiAI — Speech-to-Text Service (stt_service.py)
Captures microphone audio and transcribes using Groq Whisper (whisper-large-v3-turbo)
with custom vocabulary biasing, falling back gracefully to Google STT.
"""

import threading
import speech_recognition as sr
from dataclasses import dataclass
from typing import Callable

from services.voice.audio_transcriber import AudioTranscriber


VOICE_TIMEOUT_SECONDS = 8
PHRASE_LIMIT_SECONDS = 10


@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    success: bool
    error: str = ""


class STTService:
    """
    Dual-tier Speech-to-Text service using Groq Whisper with Google STT fallback.
    """

    def __init__(
        self,
        model_size: str = "tiny",          # kept for API compat
        on_transcription_update: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self.on_transcription_update = on_transcription_update or (lambda t: None)
        self.on_error = on_error or (lambda msg: print(f"[STTService] Error: {msg}"))
        self._recording = False
        self._transcriber = AudioTranscriber()
        print("[STTService] Initialized with Groq Whisper & Google STT fallback.")

    def listen(self, on_result: Callable[[TranscriptionResult], None]) -> None:
        """
        Record and transcribe one spoken command.
        Non-blocking — runs in a background thread.
        """
        if self._recording:
            return

        thread = threading.Thread(
            target=self._record_and_transcribe,
            args=(on_result,),
            name="STTThread",
            daemon=True,
        )
        thread.start()

    def is_recording(self) -> bool:
        return self._recording

    def _record_and_transcribe(
        self, on_result: Callable[[TranscriptionResult], None]
    ) -> None:
        """Background thread: record audio from mic and transcribe."""
        self._recording = True
        self.on_transcription_update("Listening...")

        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = False
        recognizer.energy_threshold = 420
        recognizer.pause_threshold = 0.8
        recognizer.non_speaking_duration = 0.5
        recognizer.phrase_threshold = 0.1

        try:
            with sr.Microphone() as source:
                self.on_transcription_update("Speak now...")
                print("[STTService] Recording started...")

                audio = recognizer.listen(
                    source,
                    timeout=VOICE_TIMEOUT_SECONDS,
                    phrase_time_limit=PHRASE_LIMIT_SECONDS,
                )

            self.on_transcription_update("Transcribing...")
            wav_bytes = audio.get_wav_data()

            text, provider = self._transcriber.transcribe_wav_bytes(wav_bytes)

            if text:
                print(f"[STTService] Transcribed ({provider}): '{text}'")
                self.on_transcription_update(text)
                self._recording = False
                on_result(TranscriptionResult(
                    text=text,
                    confidence=0.98 if "whisper" in provider else 0.90,
                    language="en",
                    success=True,
                ))
            else:
                print("[STTService] No speech understood.")
                self._recording = False
                on_result(TranscriptionResult(
                    text="", confidence=0.0, language="en",
                    success=False, error="Could not understand speech."
                ))

        except sr.WaitTimeoutError:
            print("[STTService] No speech detected — timeout.")
            self._recording = False
            on_result(TranscriptionResult(
                text="", confidence=0.0, language="en",
                success=False, error="No speech detected."
            ))

        except Exception as e:
            print(f"[STTService] Unexpected error: {e}")
            self._recording = False
            on_result(TranscriptionResult(
                text="", confidence=0.0, language="en",
                success=False, error=str(e)
            ))
