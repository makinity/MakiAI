"""
MakiAI — Mobile WebRTC / WebSocket HD Phone Calling Service
Provides 100% free, low-latency, full-duplex live voice calling between mobile phones and MakiAI
without any third-party telephony carrier fees or regional restrictions.
"""

import os
import time
import io
import wave
import audioop
import base64
import json
import asyncio
import threading
from pathlib import Path
from typing import Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core.orchestrator import Orchestrator
from core.state_manager import StateManager, AppState
from services.voice.tts_service import TTSService
from services.voice.stt_service import STTService
from services.settings.settings_service import SettingsService


class PhoneCallService:
    """
    FastAPI + WebSocket Live Mobile Web Phone Service.
    Serves the Mobile Web Phone PWA and provides real-time streaming audio I/O.
    """

    def __init__(
        self,
        settings_service: SettingsService,
        orchestrator: Orchestrator,
        state_manager: StateManager,
        tts_service: TTSService,
        stt_service: Optional[STTService] = None,
        skill_router: Optional[Any] = None,
        port: int = 5050,
    ):
        self.settings = settings_service
        self.orchestrator = orchestrator
        self.state_manager = state_manager
        self.tts_service = tts_service
        self.stt_service = stt_service
        self.skill_router = skill_router
        self.port = self.settings.get_phone_bridge_port()
        self.pin = (self.settings.get_phone_bridge_pin() or "").strip()

        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

        # Build FastAPI Application
        self.app = FastAPI(title="MakiAI Mobile Phone Bridge", docs_url=None, redoc_url=None)
        self._setup_routes()

    def _setup_routes(self) -> None:
        phone_web_dir = Path(__file__).resolve().parent.parent.parent / "gui" / "phone_web"

        # Serve static assets
        if phone_web_dir.exists():
            css_dir = phone_web_dir / "css"
            js_dir = phone_web_dir / "js"
            if css_dir.exists():
                self.app.mount("/call/css", StaticFiles(directory=str(css_dir)), name="phone_css")
            if js_dir.exists():
                self.app.mount("/call/js", StaticFiles(directory=str(js_dir)), name="phone_js")

        @self.app.get("/call", response_class=HTMLResponse)
        @self.app.get("/phone", response_class=HTMLResponse)
        @self.app.get("/", response_class=HTMLResponse)
        async def serve_phone_ui():
            index_path = phone_web_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return HTMLResponse("<h1>MakiAI Mobile Phone interface not found</h1>", status_code=404)

        @self.app.get("/call/manifest.json")
        async def serve_manifest():
            manifest_path = phone_web_dir / "manifest.json"
            if manifest_path.exists():
                return FileResponse(str(manifest_path), media_type="application/manifest+json")
            return JSONResponse({"name": "MakiAI Mobile Phone"}, status_code=200)

        @self.app.get("/api/phone/info")
        async def get_phone_info():
            configured_pin = (self.settings.get_phone_bridge_pin() or "").strip()
            return {
                "ok": True,
                "bot_name": self.settings.get_app_name(),
                "pin_required": bool(configured_pin),
                "server_time": time.time(),
            }

        @self.app.websocket("/ws/phone-stream")
        async def phone_stream_endpoint(websocket: WebSocket, pin: Optional[str] = Query(default="")):
            # Validate optional security PIN
            configured_pin = (self.settings.get_phone_bridge_pin() or "").strip()
            if configured_pin and (pin or "").strip() != configured_pin:
                print(f"[PhoneBridge] Unauthorized connection attempt from {websocket.client.host}")
                await websocket.close(code=4001, reason="Invalid PIN")
                return

            await websocket.accept()
            print(f"[PhoneBridge] Mobile call connected from {websocket.client.host}:{websocket.client.port}")

            await self._handle_live_call_session(websocket)

    async def _handle_live_call_session(self, websocket: WebSocket) -> None:
        """Manages bidirectional audio streaming and VAD turn-taking for a phone call."""
        # Send initial welcome metadata
        await websocket.send_text(json.dumps({
            "type": "system_info",
            "bot_name": self.settings.get_app_name(),
        }))

        # VAD & Buffer state (16kHz 16-bit mono PCM)
        pcm_buffer = bytearray()
        speaking = False
        silence_start: Optional[float] = None
        last_speech_time = time.time()
        VAD_ENERGY_THRESHOLD = 350
        SILENCE_TIMEOUT_SECS = 0.85

        try:
            while True:
                message = await websocket.receive()

                # Handle binary audio frame from mobile mic
                if "bytes" in message and message["bytes"]:
                    chunk = message["bytes"]
                    pcm_buffer.extend(chunk)

                    # Compute RMS energy of chunk
                    rms = 0
                    if len(chunk) >= 2:
                        rms = audioop.rms(chunk, 2)

                    if rms > VAD_ENERGY_THRESHOLD:
                        if not speaking:
                            speaking = True
                            await websocket.send_text(json.dumps({"type": "state", "state": "listening"}))
                        silence_start = None
                        last_speech_time = time.time()
                    else:
                        if speaking:
                            if silence_start is None:
                                silence_start = time.time()
                            elif (time.time() - silence_start) >= SILENCE_TIMEOUT_SECS:
                                # User finished speaking their turn!
                                spoken_pcm = bytes(pcm_buffer)
                                pcm_buffer.clear()
                                speaking = False
                                silence_start = None

                                # Process voice turn in background task
                                asyncio.create_task(self._process_spoken_turn(websocket, spoken_pcm))

                # Handle JSON control / text command messages (e.g. quick chips)
                elif "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                        msg_type = data.get("type", "")
                        if msg_type == "text_command":
                            cmd_text = data.get("text", "").strip()
                            if cmd_text:
                                asyncio.create_task(self._process_text_turn(websocket, cmd_text))
                    except Exception as e:
                        print(f"[PhoneBridge] Error parsing JSON client message: {e}")

        except WebSocketDisconnect:
            print(f"[PhoneBridge] Mobile call ended by client ({websocket.client.host})")
        except Exception as e:
            print(f"[PhoneBridge] WebSocket session error: {e}")

    async def _process_spoken_turn(self, websocket: WebSocket, pcm_bytes: bytes) -> None:
        """Transcribe spoken PCM audio with Groq Whisper, execute command, and stream audio response."""
        if len(pcm_bytes) < 3200:  # Less than 0.1s
            return

        try:
            await websocket.send_text(json.dumps({"type": "state", "state": "thinking"}))

            # Encode PCM to WAV container in RAM
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm_bytes)
            wav_bytes = wav_io.getvalue()

            # Transcribe via Groq Whisper
            user_text = ""
            if self.stt_service and hasattr(self.stt_service, "_transcriber") and self.stt_service._transcriber:
                user_text, _ = self.stt_service._transcriber.transcribe_wav_bytes(wav_bytes)

            clean_text = (user_text or "").strip()
            if not clean_text or len(clean_text) < 2:
                await websocket.send_text(json.dumps({"type": "state", "state": "idle"}))
                return

            print(f"[PhoneBridge] Transcribed: '{clean_text}'")
            await websocket.send_text(json.dumps({
                "type": "user_transcript",
                "text": clean_text
            }))

            # Execute via Orchestrator
            await self._execute_and_reply(websocket, clean_text)

        except Exception as e:
            print(f"[PhoneBridge] Error processing spoken turn: {e}")
            await websocket.send_text(json.dumps({"type": "state", "state": "idle"}))

    async def _process_text_turn(self, websocket: WebSocket, text: str) -> None:
        """Handle quick command chip submission."""
        await websocket.send_text(json.dumps({
            "type": "user_transcript",
            "text": text
        }))
        await websocket.send_text(json.dumps({"type": "state", "state": "thinking"}))
        await self._execute_and_reply(websocket, text)

    async def _execute_and_reply(self, websocket: WebSocket, text: str) -> None:
        """Execute command and synthesize neural audio for mobile playback."""
        try:
            loop = asyncio.get_event_loop()
            response_text = await loop.run_in_executor(None, self.orchestrator.handle_command, text)

            if not response_text:
                response_text = "Task completed, sir."

            await websocket.send_text(json.dumps({
                "type": "assistant_transcript",
                "text": response_text
            }))

            await websocket.send_text(json.dumps({"type": "state", "state": "speaking"}))

            # Synthesize audio to WAV bytes using Edge-TTS
            audio_bytes = await self._synthesize_audio(response_text)

            if audio_bytes:
                b64_audio = base64.b64encode(audio_bytes).decode("ascii")
                await websocket.send_text(json.dumps({
                    "type": "audio_chunk",
                    "audio_base64": b64_audio,
                    "format": "mp3"
                }))
            else:
                await websocket.send_text(json.dumps({"type": "state", "state": "idle"}))

        except Exception as e:
            print(f"[PhoneBridge] Error generating reply: {e}")
            await websocket.send_text(json.dumps({"type": "state", "state": "idle"}))

    async def _synthesize_audio(self, text: str) -> Optional[bytes]:
        """Synthesize response text to audio bytes for streaming."""
        clean = (text or "").strip()
        if not clean:
            return None

        # Try ElevenLabs first if API key is present
        eleven_key = self.settings.get_elevenlabs_api_key()
        voice_id = self.settings.get_elevenlabs_voice_id()
        if eleven_key and voice_id:
            try:
                from elevenlabs.client import ElevenLabs
                client = ElevenLabs(api_key=eleven_key)
                audio_stream = client.generate(
                    text=clean,
                    voice=voice_id,
                    model="eleven_turbo_v2_5",
                )
                audio_bytes = b"".join(audio_stream)
                if audio_bytes:
                    return audio_bytes
            except Exception as e:
                print(f"[PhoneBridge] ElevenLabs synthesis failed, falling back to Edge-TTS: {e}")

        # Default fast Edge-TTS synthesis
        try:
            import edge_tts
            voice = self.settings.get_env("TTS_VOICE", "en-GB-RyanNeural")
            pitch = self.settings.get_env("TTS_PITCH", "-8Hz")
            rate = self.settings.get_env("TTS_RATE", "+2%")

            communicate = edge_tts.Communicate(clean, voice, pitch=pitch, rate=rate)
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])

            return bytes(audio_data) if audio_data else None
        except Exception as e:
            print(f"[PhoneBridge] Edge-TTS synthesis failed: {e}")
            return None

    # ─── Service Lifecycle ────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the FastAPI Uvicorn server in a background daemon thread."""
        if self._is_running:
            return

        self._is_running = True
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)

        def _run():
            try:
                print(f"[PhoneBridge] 📱 Mobile Web Phone live on http://0.0.0.0:{self.port}/call")
                self._server.run()
            except Exception as e:
                print(f"[PhoneBridge] Server error: {e}")
            finally:
                self._is_running = False

        self._thread = threading.Thread(target=_run, daemon=True, name="PhoneCallBridgeThread")
        self._thread.start()

    def stop(self) -> None:
        """Stop the FastAPI Uvicorn server."""
        self._is_running = False
        if self._server:
            self._server.should_exit = True
