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


from services.ai.key_rotator import key_rotator, KeyRotator


# Natural conversational vocabulary prompt to bias Whisper without triggering repetition loops
VOCABULARY_PROMPT = (
    "MakiAI desktop assistant. Topics: Kiro, MakiSync, TaskMaster, MunchBite, Next.js, "
    "Canva, Upwork, Zoom, PHT, VS Code, Supabase, Tailwind, Python, FastAPI, React."
)

# Common phonetic mishearings mapped to their intended terms
PHONETIC_REPLACEMENTS = [
    (re.compile(r"\b(?:magazine|cable|max\s*sync|make\s*sync|make\s*a\s*sync|monkey\s*sync|maki\s*sink)\s+storage\b", re.IGNORECASE), "MakiSync Storage"),
    (re.compile(r"\b(?:magazine|max\s*sync|make\s*sync|make\s*a\s*sync|monkey\s*sync|maki\s*sink)\b(?=\s+(?:folder|files?|recordings?|photos?|screenshots?|docs?|assignments?|school|work|personal))", re.IGNORECASE), "MakiSync"),
    (re.compile(r"\b(key\s*row|kero|cure\s*row|curro|hero(?=\s+cli|\s+terminal|\s+code))\b", re.IGNORECASE), "Kiro"),
    (re.compile(r"\b(macky|machi|make\s*he|maki\s*a\s*i)\b", re.IGNORECASE), "Maki"),
    (re.compile(r"\b(make\s*a\s*sync|monkey\s*sync|make\s*he\s*sync|maki\s*sink)\b", re.IGNORECASE), "MakiSync"),
    (re.compile(r"\b(canvas)\s+(poster|design|app|site|website)\b", re.IGNORECASE), r"Canva \2"),
    (re.compile(r"\b(?:for|build|building|on|develop|developing)\s+tops\b", re.IGNORECASE), "for TaskMaster"),
    (re.compile(r"\b(task\s*master)\b", re.IGNORECASE), "TaskMaster"),
    (re.compile(r"\b(munch\s*bite)\b", re.IGNORECASE), "MunchBite"),
]



class AudioTranscriber:
    """
    High-performance, multi-key voice transcriber with Groq Whisper, RMS silence gating, and Google STT.
    """

    def __init__(self, groq_api_key: str = ""):
        self._groq_clients: dict = {}
        self._recognizer = sr.Recognizer()
        self._init_groq()

    def _get_groq_client(self, api_key: Optional[str] = None):
        key = api_key or key_rotator.get_active_key("groq")
        if not key:
            return None, None
        if key not in self._groq_clients:
            try:
                from groq import Groq
                self._groq_clients[key] = Groq(api_key=key)
            except Exception as e:
                print(f"[AudioTranscriber] Groq client creation failed for {KeyRotator._mask_key(key)}: {e}")
                return None, None
        return self._groq_clients[key], key

    def _init_groq(self) -> None:
        """Initialize Groq client pool."""
        client, key = self._get_groq_client()
        if client:
            print(f"[AudioTranscriber] Groq Whisper (whisper-large-v3-turbo) initialized with KeyRotator ({KeyRotator._mask_key(key)}).")
        else:
            print("[AudioTranscriber] No Groq keys available. Running Google STT fallback.")

    def update_groq_key(self, api_key: str) -> None:
        """Hot-swap Groq API key."""
        os.environ["GROQ_API_KEY"] = api_key
        key_rotator.reload_keys_from_env()
        self._init_groq()

    def is_audio_silent(self, wav_bytes: bytes, min_rms: float = 340.0) -> bool:
        """Check if audio contains genuine human voice or just background silence/hiss."""
        if not wav_bytes or len(wav_bytes) < 1600:
            return True
        try:
            # Parse 16-bit PCM samples from WAV
            wav_buffer = io.BytesIO(wav_bytes)
            with wave.open(wav_buffer, "rb") as wf:
                raw_frames = wf.readframes(wf.getnframes())
                samples = np.frombuffer(raw_frames, dtype=np.int16)
                if len(samples) < 1200:
                    return True
                rms = float(np.sqrt(np.mean(samples.astype(np.float64)**2)))
                # If RMS is below ambient silence threshold, drop audio
                return rms < min_rms
        except Exception:
            return False

    def is_hallucination_loop(self, text: str) -> bool:
        """Detect phantom Whisper hallucinations, subtitle artifacts, and repetition loops."""
        if not text:
            return True

        clean = text.strip().lower()

        # 1. Reject very short or punctuation-only strings
        clean_words = re.findall(r"\b[a-z0-9']+\b", clean)
        if len(clean_words) == 0:
            return True

        # Reject single isolated filler tokens on background noise
        if len(clean_words) == 1 and clean_words[0] in {
            "you", "the", "a", "i", "so", "yeah", "yes", "no", "uh", "um", "oh",
            "bye", "hi", "ok", "hey", "foreign", "music", "thanks", "thank",
            "apoio", "megatron", "shopee", "google", "zoom", "youtube", "facebook"
        }:
            return True

        # Reject isolated silence politeness hallucinations (e.g. "Thank you.", "Thank you very much.")
        clean_no_punc = re.sub(r"[^\w\s]", "", clean).strip()
        if clean_no_punc in {
            "thank you", "thank you very much", "thanks", "thanks a lot",
            "you're welcome", "your welcome", "bye bye", "goodbye", "hello",
            "subtitles by", "watching", "amara org"
        }:
            return True

        # 2. Known Whisper silence/noise hallucination blacklist
        hallucination_patterns = [
            "subtitles by", "amara.org", "thank you for watching", "thanks for watching",
            "please subscribe", "like and subscribe", "translated by", "closed captions",
            "english subtitles", "watching", "makispace", "apoio", "tim ste", "megatron",
            "tos facebook", "[music]", "(music)", "[applause]", "[laughter]", "[silence]",
            "captioned by", "transcribed by", "all rights reserved", "subscribe for more",
            "taskmaster, munchbite", "munchbite, kiro", "taskmaster, munchbite, kiro"
        ]
        for pat in hallucination_patterns:
            if pat in clean:
                return True

        # 3. Check for excessive token repetition (e.g. "word word word word")
        if len(clean_words) >= 4:
            counts = {}
            for w in clean_words:
                counts[w] = counts.get(w, 0) + 1
                if counts[w] >= 3 and (counts[w] / len(clean_words)) > 0.4:
                    return True

        return False

    def transcribe_wav_bytes(self, wav_bytes: bytes) -> tuple[str, str]:
        """
        Transcribe raw WAV audio bytes with multi-key Groq Whisper rotation.

        Returns:
            (transcribed_text, provider_used)
        """
        if not wav_bytes or self.is_audio_silent(wav_bytes):
            return "", "silence"

        # Tier 1: Try Groq Whisper with KeyRotator
        max_attempts = max(1, len(key_rotator._pools.get("groq", [])))
        for _ in range(max_attempts):
            client, active_key = self._get_groq_client()
            if not client:
                break

            try:
                response = client.audio.transcriptions.create(
                    file=("audio.wav", wav_bytes, "audio/wav"),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                    language="en",
                    temperature=0.0,
                )
                raw_text = str(response).strip()
                if self.is_hallucination_loop(raw_text):
                    print(f"[AudioTranscriber] Dropped Whisper hallucination: '{raw_text[:50]}'")
                    return "", "hallucination_filtered"

                cleaned_text = self.heal_phonetics(raw_text)
                if cleaned_text and not self.is_hallucination_loop(cleaned_text):
                    key_rotator.report_success("groq", active_key)
                    return cleaned_text, "groq-whisper"
            except Exception as e:
                err_str = str(e).lower()
                print(f"[AudioTranscriber] Groq Whisper error on key {KeyRotator._mask_key(active_key)}: {e}")
                if "429" in err_str or "rate limit" in err_str or "quota" in err_str or "resource" in err_str:
                    key_rotator.report_rate_limit("groq", active_key, str(e))
                    continue # Retry on next key in pool
                break

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
