"""
MakiAI — Mobile WebRTC / WebSocket HD Phone & Video Calling Service
Provides 100% free, low-latency, full-duplex live voice & video calling between mobile phones and MakiAI.
Supports:
  1. Voice Orb (Duplex Audio)
  2. Laptop Screen Share (PC Desktop ➔ Phone in real time)
  3. Laptop Webcam Feed (Built-in Camera ➔ Phone in real time)
  4. Phone Camera Vision (Phone Camera ➔ Gemini Vision multimodal analysis)
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

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageGrab
except ImportError:
    Image = None
    ImageGrab = None

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core.orchestrator import Orchestrator
from core.state_manager import StateManager
from services.voice.tts_service import TTSService
from services.voice.stt_service import STTService
from services.settings.settings_service import SettingsService


class PhoneCallService:
    """
    FastAPI + WebSocket Live Mobile Web Phone & Video Calling Service.
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

        self.active_video_mode = "orb"
        self.latest_phone_camera_bytes: Optional[bytes] = None

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
        """Manages bidirectional audio streaming, video channels, and VAD turn-taking."""
        await websocket.send_text(json.dumps({
            "type": "system_info",
            "bot_name": self.settings.get_app_name(),
        }))

        # VAD state
        pcm_buffer = bytearray()
        speaking = False
        silence_start: Optional[float] = None
        VAD_ENERGY_THRESHOLD = 350
        SILENCE_TIMEOUT_SECS = 0.85

        # Video streaming task tracker
        video_stream_task: Optional[asyncio.Task] = None

        async def _start_video_loop(mode: str):
            nonlocal video_stream_task
            if video_stream_task and not video_stream_task.done():
                video_stream_task.cancel()
            self.active_video_mode = mode
            if mode == "screen":
                video_stream_task = asyncio.create_task(self._screen_stream_loop(websocket))
            elif mode == "webcam":
                video_stream_task = asyncio.create_task(self._webcam_stream_loop(websocket))

        try:
            while True:
                message = await websocket.receive()

                # Handle binary audio frame from mobile mic
                if "bytes" in message and message["bytes"]:
                    chunk = message["bytes"]
                    pcm_buffer.extend(chunk)

                    rms = 0
                    if len(chunk) >= 2:
                        rms = audioop.rms(chunk, 2)

                    if rms > VAD_ENERGY_THRESHOLD:
                        if not speaking:
                            speaking = True
                            await websocket.send_text(json.dumps({"type": "state", "state": "listening"}))
                        silence_start = None
                    else:
                        if speaking:
                            if silence_start is None:
                                silence_start = time.time()
                            elif (time.time() - silence_start) >= SILENCE_TIMEOUT_SECS:
                                spoken_pcm = bytes(pcm_buffer)
                                pcm_buffer.clear()
                                speaking = False
                                silence_start = None
                                asyncio.create_task(self._process_spoken_turn(websocket, spoken_pcm))

                # Handle JSON messages
                elif "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                        msg_type = data.get("type", "")

                        if msg_type == "text_command":
                            cmd_text = data.get("text", "").strip()
                            if cmd_text:
                                asyncio.create_task(self._process_text_turn(websocket, cmd_text))

                        elif msg_type == "set_video_mode":
                            req_mode = data.get("mode", "orb")
                            await _start_video_loop(req_mode)

                        elif msg_type == "camera_frame":
                            b64_img = data.get("image_base64", "")
                            if b64_img:
                                self.latest_phone_camera_bytes = base64.b64decode(b64_img)

                    except Exception as e:
                        print(f"[PhoneBridge] Error parsing JSON message: {e}")

        except WebSocketDisconnect:
            print(f"[PhoneBridge] Mobile call ended by client ({websocket.client.host})")
        except Exception as e:
            print(f"[PhoneBridge] WebSocket session error: {e}")
        finally:
            if video_stream_task and not video_stream_task.done():
                video_stream_task.cancel()
            self.active_video_mode = "orb"

    # ─── Video Streaming Loops ────────────────────────────────────────────────

    async def _screen_stream_loop(self, websocket: WebSocket) -> None:
        """Stream laptop dual/single screen desktop frames to phone at 10-12 FPS."""
        print("[PhoneBridge] 💻 PC Screen Share stream started")
        try:
            while self.active_video_mode == "screen":
                if ImageGrab:
                    screen = ImageGrab.grab()
                    # Scale down for fast low-latency streaming (max width 640)
                    w, h = screen.size
                    target_w = 640
                    target_h = int(h * (target_w / w))
                    resized = screen.resize((target_w, target_h), Image.Resampling.BILINEAR)

                    buf = io.BytesIO()
                    resized.save(buf, format="JPEG", quality=55)
                    b64_frame = base64.b64encode(buf.getvalue()).decode("ascii")

                    await websocket.send_text(json.dumps({
                        "type": "video_frame",
                        "image_base64": b64_frame,
                    }))
                await asyncio.sleep(0.09)  # ~11 FPS
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[PhoneBridge] Screen stream error: {e}")

    async def _webcam_stream_loop(self, websocket: WebSocket) -> None:
        """Stream laptop built-in webcam video to phone at 12-15 FPS."""
        print("[PhoneBridge] 👁️ Laptop Webcam stream started")
        cap = None
        try:
            if cv2:
                cap = cv2.VideoCapture(0)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            while self.active_video_mode == "webcam" and cap and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # Compress to JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 55])
                    b64_frame = base64.b64encode(buffer).decode("ascii")

                    await websocket.send_text(json.dumps({
                        "type": "video_frame",
                        "image_base64": b64_frame,
                    }))
                await asyncio.sleep(0.07)  # ~14 FPS
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[PhoneBridge] Webcam stream error: {e}")
        finally:
            if cap:
                cap.release()
                print("[PhoneBridge] Laptop Webcam stream released")

    # ─── Speech & Vision Turn Processing ──────────────────────────────────────

    async def _process_spoken_turn(self, websocket: WebSocket, pcm_bytes: bytes) -> None:
        """Transcribe speech and handle intent with multimodal vision support."""
        if len(pcm_bytes) < 3200:
            return

        try:
            await websocket.send_text(json.dumps({"type": "state", "state": "thinking"}))

            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm_bytes)
            wav_bytes = wav_io.getvalue()

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
        """Execute command, handle visual mode switching, and stream TTS response."""
        lower_cmd = text.lower().strip()

        # 1. Voice Command Video Mode Switches
        if any(p in lower_cmd for p in ["share your screen", "show your screen", "show me your desktop", "share desktop", "screenshare"]):
            self.active_video_mode = "screen"
            await websocket.send_text(json.dumps({"type": "set_video_mode", "mode": "screen"}))
            asyncio.create_task(self._screen_stream_loop(websocket))
            response_text = "Sharing my screen with your phone now, sir."

        elif any(p in lower_cmd for p in ["show your camera", "show me your webcam", "turn on your camera", "turn on laptop camera", "laptop webcam"]):
            self.active_video_mode = "webcam"
            await websocket.send_text(json.dumps({"type": "set_video_mode", "mode": "webcam"}))
            asyncio.create_task(self._webcam_stream_loop(websocket))
            response_text = "Activating laptop camera now, sir."

        elif any(p in lower_cmd for p in ["look at my camera", "turn on my camera", "look through my camera", "phone camera"]):
            self.active_video_mode = "phone_cam"
            await websocket.send_text(json.dumps({"type": "set_video_mode", "mode": "phone_cam"}))
            response_text = "Looking through your phone camera now, sir. Point at anything you'd like me to analyze."

        elif any(p in lower_cmd for p in ["turn off video", "stop video", "stop screenshare", "switch back to audio", "voice mode"]):
            self.active_video_mode = "orb"
            await websocket.send_text(json.dumps({"type": "set_video_mode", "mode": "orb"}))
            response_text = "Switched back to voice mode, sir."

        # 2. Multimodal Gemini Vision Question Check
        elif (self.active_video_mode == "phone_cam" or any(p in lower_cmd for p in ["what am i holding", "what is this", "look at this", "what do you see", "analyze this", "read this"])) and self.latest_phone_camera_bytes:
            try:
                gemini = getattr(self.orchestrator, "gemini_service", None)
                if gemini and hasattr(gemini, "generate_with_image"):
                    loop = asyncio.get_event_loop()
                    response_text = await loop.run_in_executor(
                        None,
                        lambda: gemini.generate_with_image(text, self.latest_phone_camera_bytes)
                    )
                else:
                    response_text = "Vision engine is currently offline, sir."
            except Exception as e:
                print(f"[PhoneBridge] Vision query error: {e}")
                response_text = "I couldn't analyze the camera image right now, sir."

        # 3. Standard Orchestrator Command
        else:
            try:
                loop = asyncio.get_event_loop()
                response_text = await loop.run_in_executor(None, self.orchestrator.handle_command, text)
                if not response_text:
                    response_text = "Task completed, sir."
            except Exception as e:
                print(f"[PhoneBridge] Command execution error: {e}")
                response_text = "I encountered an error executing that command, sir."

        # Send assistant transcript to phone
        await websocket.send_text(json.dumps({
            "type": "assistant_transcript",
            "text": response_text
        }))

        await websocket.send_text(json.dumps({"type": "state", "state": "speaking"}))

        # Synthesize audio and stream back to phone
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

    async def _synthesize_audio(self, text: str) -> Optional[bytes]:
        """Synthesize response text to audio bytes for streaming."""
        clean = (text or "").strip()
        if not clean:
            return None

        # Try ElevenLabs first if configured
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

        # Edge-TTS synthesis
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
                print(f"[PhoneBridge] 📱 Mobile Web Phone & Video live on http://0.0.0.0:{self.port}/call")
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
