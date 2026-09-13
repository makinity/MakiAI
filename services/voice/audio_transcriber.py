"""
MakiAI — Audio Transcriber (audio_transcriber.py)
Unified Speech-to-Text engine supporting:
  1. Groq Whisper Cloud (whisper-large-v3-turbo) with custom vocabulary prompting
  2. Google STT fallback (via SpeechRecognition)
  3. Phonetic/alias healing for domain-specific technical terms
"""

import os
import re
import io
import wave
import numpy as np
import speech_recognition as sr
from typing import Optional


# Natural conversational vocabulary prompt to bias Whisper without triggering repetition loops
VOCABULARY_PROMPT = (
    "MakiAI assistant for Mark. Topics: Kiro, MakiSync, TaskMaster, MunchBite, Next.js, "
    "Canva, Upwork, Zoom, PHT, VS Code, Supabase, Tailwind, Python, FastAPI, React."
)

# Common phonetic mishearings mapped to their intended terms
PHONETIC_REPLACEMENTS = [
    (re.compile(r"\b(key\s*row|kero|cure\s*row|hero)\b", re.IGNORECASE), "Kiro"),
    (re.compile(r"\b(macky|machi|make\s*he|maki\s*a\s*i)\b", re.IGNORECASE), "Maki"),
    (re.compile(r"\b(make\s*a\s*sync|monkey\s*sync|make\s*he\s*sync|maki\s*sink)\b", re.IGNORECASE), "MakiSync"),
    (re.compile(r"\b(canvas)\s+(poster|design|app)\b", re.IGNORECASE), r"Canva \2"),
    (re.compile(r"\b(task\s*master)\b", re.IGNORECASE), "TaskMaster"),
    (re.compile(r"\b(munch\s*bite)\b", re.IGNORECASE), "MunchBite"),
]


class AudioTranscriber:
    """
    High-performance, dual-tier voice transcriber with Groq Whisper, RMS silence gating, and Google STT.
    """

    def __init__(self, groq_api_key: str = ""):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self._groq_client = None
        self._recognizer = sr.Recognizer()

        self._init_groq()

    def _init_groq(self) -> None:
        """Initialize Groq client if key is valid."""
        if self.groq_api_key and self.groq_api_key not in ("", "your_groq_api_key_here"):
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_api_key)
                print("[AudioTranscriber] Groq Whisper (whisper-large-v3-turbo) initialized with vocabulary biasing.")
            except Exception as e:
                print(f"[AudioTranscriber] Groq init failed: {e}. Using Google STT.")
                self._groq_client = None

    def update_groq_key(self, api_key: str) -> None:
        """Hot-swap Groq API key."""
        self.groq_api_key = api_key
        self._init_groq()

    def is_audio_silent(self, wav_bytes: bytes, min_rms: float = 160.0) -> bool:
        """Check if audio contains genuine human voice or just background silence/hiss."""
        if not wav_bytes or len(wav_bytes) < 1000:
            return True
        try:
            # Parse 16-bit PCM samples from WAV
            wav_buffer = io.BytesIO(wav_bytes)
            with wave.open(wav_buffer, "rb") as wf:
                raw_frames = wf.readframes(wf.getnframes())
                samples = np.frombuffer(raw_frames, dtype=np.int16)
                if len(samples) < 800:
                    return True
                rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2)))
                # If RMS is below ambient silence threshold, drop audio
                return rms < min_rms
        except Exception:
            return False

    def is_hallucination_loop(self, text: str) -> bool:
        """Detect repetitive Whisper token hallucination loops."""
        if not text:
            return False
        words = text.lower().split()
        if len(words) >= 6:
            # Check for excessive repetition of any single word
            counts = {}
            for w in words:
                counts[w] = counts.get(w, 0) + 1
                if counts[w] >= 4:
                    return True
        return False

    def transcribe_wav_bytes(self, wav_bytes: bytes) -> tuple[str, str]:
        """
        Transcribe raw WAV audio bytes with RMS silence gating.

        Returns:
            (transcribed_text, provider_used)
        """
        if not wav_bytes or self.is_audio_silent(wav_bytes):
            return "", "silence"

        # Tier 1: Try Groq Whisper (Ultra-fast ~150ms, high accuracy, vocabulary biased)
        if self._groq_client:
            try:
                response = self._groq_client.audio.transcriptions.create(
                    file=("audio.wav", wav_bytes, "audio/wav"),
                    model="whisper-large-v3-turbo",
                    prompt=VOCABULARY_PROMPT,
                    response_format="text",
                    language="en",
                    temperature=0.0,
                )
                raw_text = str(response).strip()
                if self.is_hallucination_loop(raw_text):
                    print(f"[AudioTranscriber] Dropped Whisper hallucination loop: '{raw_text[:40]}...'")
                    return "", "hallucination_filtered"

                cleaned_text = self.heal_phonetics(raw_text)
                if cleaned_text:
                    return cleaned_text, "groq-whisper"
            except Exception as e:
                print(f"[AudioTranscriber] Groq Whisper error ({e}). Falling back to Google STT.")

        # Tier 2: Fallback to Google STT
        try:
            wav_buffer = io.BytesIO(wav_bytes)
            with sr.AudioFile(wav_buffer) as source:
                audio = self._recognizer.record(source)

            text = self._recognizer.recognize_google(audio, language="en-US").strip()
            cleaned_text = self.heal_phonetics(text)
            return cleaned_text, "google-stt"
        except sr.UnknownValueError:
            return "", "google-stt"
        except Exception as ex:
            print(f"[AudioTranscriber] Google STT fallback error: {ex}")
            return "", "error"

    def transcribe_numpy_frames(self, frames: list[np.ndarray], samplerate: int = 16000, channels: int = 1) -> tuple[str, str]:
        """Convert numpy audio buffer to WAV bytes and transcribe."""
        if not frames:
            return "", "none"

        audio_data = np.concatenate(frames, axis=0)
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(samplerate)
            wf.writeframes(audio_data.tobytes())

        return self.transcribe_wav_bytes(wav_buffer.getvalue())

    def heal_phonetics(self, text: str) -> str:
        """Apply phonetic replacement dictionary to heal common mishearings."""
        if not text:
            return ""
        result = text.strip()
        for pattern, replacement in PHONETIC_REPLACEMENTS:
            result = pattern.sub(replacement, result)
        return result
