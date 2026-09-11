"""
MakiAI — Speech-to-Text Service
Uses Google STT via SpeechRecognition — same library as wake word detection.
No model download required. Works immediately.

Whisper can be re-enabled later once the model is fully cached.
Pattern based on MakiBot's proven listen.py implementation.
"""

import threading
import speech_recognition as sr
from dataclasses import dataclass
from typing import Callable


AMBIENT_NOISE_SECONDS = 0.3
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
    Speech-to-Text using Google STT via SpeechRecognition.
    No model download. Works out of the box.
    """

    def __init__(
        self,
        model_size: str = "tiny",          # unused — kept for API compat
        on_transcription_update: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ):
        self.on_transcription_update = on_transcription_update or (lambda t: None)
        self.on_error = on_error or (lambda msg: print(f"[STTService] Error: {msg}"))
        self._recording = False
        print("[STTService] Using Google STT — no model download needed.")

    def listen(self, on_result: Callable[[TranscriptionResult], None]) -> None:
        """
        Record and transcribe one spoken command.
        Non-blocking — runs in a background thread.

        Args:
            on_result: Called with TranscriptionResult when done.
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
        """Background thread: record audio and transcribe with Google STT."""
        self._recording = True
        self.on_transcription_update("Listening...")

        # Fresh recognizer per call — MakiBot pattern
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = False   # Fixed threshold — more reliable
        recognizer.energy_threshold = 200             # Low = picks up quiet speech
        recognizer.pause_threshold = 0.8
        recognizer.non_speaking_duration = 0.5
        recognizer.phrase_threshold = 0.1

        try:
            with sr.Microphone() as source:
                # No calibration here — wake word already calibrated the mic
                # Calibration was consuming the user's speech
                self.on_transcription_update("Speak now...")
                print("[STTService] Recording started...")

                audio = recognizer.listen(
                    source,
                    timeout=VOICE_TIMEOUT_SECONDS,
                    phrase_time_limit=PHRASE_LIMIT_SECONDS,
                )

            self.on_transcription_update("Transcribing...")
            text = recognizer.recognize_google(audio, language="en-US")
            text = text.strip()

            print(f"[STTService] Transcribed: '{text}'")
            self.on_transcription_update(text)

            self._recording = False
            on_result(TranscriptionResult(
                text=text,
                confidence=0.9,     # Google STT doesn't return confidence
                language="en",
                success=True,
            ))

        except sr.WaitTimeoutError:
            print("[STTService] No speech detected — timeout.")
            self._recording = False
            on_result(TranscriptionResult(
                text="", confidence=0.0, language="en",
                success=False, error="No speech detected."
            ))

        except sr.UnknownValueError:
            print("[STTService] Could not understand speech.")
            self._recording = False
            on_result(TranscriptionResult(
                text="", confidence=0.0, language="en",
                success=False, error="Could not understand speech."
            ))

        except sr.RequestError as e:
            print(f"[STTService] Google STT API error: {e}")
            self._recording = False
            on_result(TranscriptionResult(
                text="", confidence=0.0, language="en",
                success=False, error=f"STT API error: {e}"
            ))

        except Exception as e:
            print(f"[STTService] Unexpected error: {e}")
            self._recording = False
            on_result(TranscriptionResult(
                text="", confidence=0.0, language="en",
                success=False, error=str(e)
            ))
