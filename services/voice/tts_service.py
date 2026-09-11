"""
MakiAI — Text-to-Speech Service
Jarvis-like voice output using ElevenLabs API.
Falls back to Edge TTS (Microsoft Neural) when ElevenLabs quota is exceeded.

Flow:
  1. Try ElevenLabs API → generate audio → play via pygame
  2. On quota/error → fall back to Edge TTS → play via pygame
  3. Fire on_speaking_start before playback, on_speaking_end after

ElevenLabs free tier: 10,000 characters/month.
Edge TTS: free, Microsoft Neural voices, no quota.
"""

import os
import asyncio
import tempfile
import threading
from pathlib import Path
from typing import Callable

import pygame


class TTSService:
    """
    Text-to-Speech service for MakiAI.

    Primary:  ElevenLabs API — Jarvis-like voice quality.
    Fallback: edge-tts (Microsoft Neural) — free, always available.

    The on_speaking_start / on_speaking_end callbacks drive
    the GUI animation state (SPEAKING → IDLE).
    """

    def __init__(
        self,
        elevenlabs_api_key: str = "",
        voice_id: str = "",
        on_speaking_start: Callable[[], None] | None = None,
        on_speaking_end: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        use_fallback: bool = True,
    ):
        """
        Args:
            elevenlabs_api_key: ElevenLabs API key from .env
            voice_id:           ElevenLabs voice ID from .env
            on_speaking_start:  Called just before audio plays (→ SPEAKING state)
            on_speaking_end:    Called after audio finishes (→ IDLE state)
            on_error:           Called with error message string on failure
            use_fallback:       If True, falls back to Edge TTS on ElevenLabs failure
        """
        self.elevenlabs_api_key = elevenlabs_api_key
        self.voice_id = voice_id or "pNInz6obpgDQGcFmaJgB"  # Default: Adam (deep, clear)
        self.on_speaking_start = on_speaking_start or (lambda: None)
        self.on_speaking_end = on_speaking_end or (lambda: None)
        self.on_error = on_error or (lambda msg: print(f"[TTSService] Error: {msg}"))
        self.use_fallback = use_fallback

        self._speaking = False
        self._elevenlabs_disabled = False
        self._pygame_initialized = False
        self._init_pygame()

    # ─── Pygame Init ──────────────────────────────────────────────────────────

    def _init_pygame(self) -> None:
        """Initialize pygame mixer for audio playback."""
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._pygame_initialized = True
            print("[TTSService] pygame mixer initialized.")
        except Exception as e:
            print(f"[TTSService] pygame init failed: {e}")
            self._pygame_initialized = False

    # ─── Public API ──────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """
        Speak the given text aloud as a single continuous audio stream.
        Strips markdown formatting before speaking.
        Non-blocking — runs in background thread with zero pauses at periods.
        """
        if not text or not text.strip():
            return

        if self._speaking:
            return

        # Strip markdown so it isn't read aloud literally
        clean = self._strip_markdown(text)
        if not clean.strip():
            return

        thread = threading.Thread(
            target=self._speak_thread,
            args=(clean,),
            name="TTSThread",
            daemon=True,
        )
        thread.start()

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """
        Remove markdown formatting so TTS doesn't read symbols aloud.
        Strips: **bold**, *italic*, `code`, # headers, - bullets, numbered lists symbols.
        """
        import re
        # Bold and italic
        text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        # Code blocks and inline code
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Bullet points — replace with pause
        text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)
        # Numbered list markers — keep the text
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        # Horizontal rules
        text = re.sub(r'^[-_*]{3,}$', '', text, flags=re.MULTILINE)
        # Links [text](url) → text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Extra blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def update_credentials(self, api_key: str, voice_id: str) -> None:
        """
        Hot-swap ElevenLabs credentials without restarting.

        Args:
            api_key:  New ElevenLabs API key.
            voice_id: New voice ID.
        """
        self.elevenlabs_api_key = api_key
        self.voice_id = voice_id
        self._elevenlabs_disabled = False
        print("[TTSService] Credentials updated.")

    def is_speaking(self) -> bool:
        return self._speaking

    def _speak_thread(self, text: str) -> None:
        """
        Background thread: generate single continuous audio stream and play it.
        Guarantees natural prosody and zero stops at sentence periods.
        """
        self._speaking = True
        self.on_speaking_start()

        tmp_path = None
        success = False

        try:
            # ── Attempt 1: ElevenLabs (if key is set and quota not exceeded) ──
            if (
                not self._elevenlabs_disabled
                and self.elevenlabs_api_key
                and self.elevenlabs_api_key not in ("", "your_elevenlabs_api_key_here")
            ):
                tmp_path, success = self._generate_elevenlabs(text)

            # ── Attempt 2: Edge TTS fallback ──────────────────────────────────
            if not success and self.use_fallback:
                tmp_path, success = self._generate_edge_tts(text)

            # ── Play continuous audio ─────────────────────────────────────────
            if success and tmp_path:
                self._play_audio(tmp_path)
            else:
                print(f"\n[Maki speaks]: {text}\n")

        except Exception as e:
            self.on_error(f"TTS error: {e}")
        finally:
            if tmp_path and Path(tmp_path).exists():
                try:
                    Path(tmp_path).unlink()
                except Exception:
                    pass
            self._speaking = False
            self.on_speaking_end()

    # ─── ElevenLabs ──────────────────────────────────────────────────────────

    def _generate_elevenlabs(self, text: str) -> tuple[str | None, bool]:
        """
        Generate audio using ElevenLabs API.

        Returns:
            (tmp_file_path, success) tuple.
        """
        try:
            from elevenlabs.client import ElevenLabs
            from elevenlabs import VoiceSettings

            client = ElevenLabs(api_key=self.elevenlabs_api_key)

            audio = client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_turbo_v2",       # Fastest model, lowest latency
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True,
                ),
            )

            # Save to temp file
            tmp = tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            )
            for chunk in audio:
                if chunk:
                    tmp.write(chunk)
            tmp.close()

            print(f"[TTSService] ElevenLabs audio generated: {len(text)} chars")
            return tmp.name, True

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "limit" in error_str or "429" in error_str:
                self._elevenlabs_disabled = True
                print("[TTSService] ElevenLabs quota exceeded — switching to Edge TTS.")
            else:
                print(f"[TTSService] ElevenLabs error: {e}")
            return None, False

    # ─── Edge TTS Fallback ────────────────────────────────────────────────────

    def _generate_edge_tts(self, text: str) -> tuple[str | None, bool]:
        """
        Generate audio using Microsoft Edge TTS (free fallback).
        Uses a deep neural voice similar to Jarvis.

        Returns:
            (tmp_file_path, success) tuple.
        """
        try:
            import edge_tts

            # Best Jarvis-like voice available in Edge TTS
            voice = "en-US-GuyNeural"

            tmp = tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            )
            tmp_path = tmp.name
            tmp.close()

            # edge-tts is async — run in a new event loop
            async def _generate():
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate="+5%",     # Slightly faster — more Jarvis-like
                    pitch="-5Hz",   # Slightly lower pitch
                )
                await communicate.save(tmp_path)

            asyncio.run(_generate())
            print(f"[TTSService] Edge TTS audio generated.")
            return tmp_path, True

        except Exception as e:
            print(f"[TTSService] Edge TTS error: {e}")
            return None, False

    # ─── Audio Playback ───────────────────────────────────────────────────────

    def _play_audio(self, file_path: str) -> None:
        """
        Play an audio file using pygame mixer.
        Blocks until playback is complete.

        Args:
            file_path: Path to the .mp3 audio file.
        """
        if not self._pygame_initialized:
            print(f"[TTSService] pygame not available — skipping playback.")
            return

        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)

        except Exception as e:
            print(f"[TTSService] Playback error: {e}")
            # Try reinitializing pygame on failure
            self._init_pygame()
