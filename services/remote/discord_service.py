"""
MakiAI — Discord Remote Voice & Messaging Bridge (discord_service.py)
Provides 24/7 Discord integration with two-way messaging, voice channel calling,
and proactive routine voice announcements.

Features:
  1. Live Voice Calling: Joins Discord Voice Channel and speaks with British Neural Voice.
  2. Two-Way Chat: Responds to commands, questions, routine triggers, and homework requests in Discord.
  3. Proactive Routine Alerts: Broadcasts upcoming class/client/job-hunting reminders to voice and chat.
  4. Remote Desktop Controls: /screenshot, /camera, /status.
  5. Multi-Threaded Daemon: Operates on a dedicated non-blocking asyncio event loop.
"""

import os
import io
import asyncio
import tempfile
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

import discord
from discord.ext import commands

from services.voice.tts_service import TTSService


class DiscordRemoteService:
    """
    Background Discord Bot & Voice Bridge for MakiAI.
    """

    def __init__(
        self,
        settings_service,
        orchestrator,
        state_manager=None,
        tts_service: Optional[TTSService] = None,
        skill_router=None,
    ):
        self.settings = settings_service
        self.orchestrator = orchestrator
        self.state_manager = state_manager
        self.tts_service = tts_service
        self.skill_router = skill_router

        self._token: str = self.settings.get_env("DISCORD_BOT_TOKEN", "").strip()
        self._guild_id: str = self.settings.get_env("DISCORD_GUILD_ID", "").strip()
        self._voice_channel_id: str = self.settings.get_env("DISCORD_VOICE_CHANNEL_ID", "").strip()
        self._text_channel_id: str = self.settings.get_env("DISCORD_TEXT_CHANNEL_ID", "").strip()
        self._allowed_user_id: str = self.settings.get_env("DISCORD_ALLOWED_USER_ID", "").strip()

        self._bot: Optional[commands.Bot] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._voice_client: Optional[discord.VoiceClient] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Launch Discord bot in background daemon thread."""
        self._token = self.settings.get_env("DISCORD_BOT_TOKEN", "").strip()
        if not self._token:
            print("[DiscordBridge] No DISCORD_BOT_TOKEN found. Discord bridge paused.")
            return False

        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(
            target=self._run_bot_thread,
            name="DiscordBridgeThread",
            daemon=True,
        )
        self._thread.start()
        print("[DiscordBridge] Discord Voice & Messaging Bridge started.")
        return True

    def stop(self) -> None:
        """Stop the background Discord loop."""
        self._running = False
        if self._bot and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._bot.close(), self._loop)
            print("[DiscordBridge] Discord Bridge stopped.")

    # ─── Internal Event Loop ──────────────────────────────────────────────────

    def _run_bot_thread(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True

        self._bot = commands.Bot(command_prefix="!", intents=intents)

        @self._bot.event
        async def on_ready():
            print(f"[DiscordBridge] MakiAI logged in as {self._bot.user} (ID: {self._bot.user.id})")
            # Auto-announce in general
            if self._text_channel_id:
                try:
                    ch = self._bot.get_channel(int(self._text_channel_id))
                    if ch:
                        await ch.send("🤖 **MakiAI Voice & Remote Assistant** is online and connected to Makinity.")
                except Exception as ex:
                    print(f"[DiscordBridge] Announcement error: {ex}")

        @self._bot.event
        async def on_message(message: discord.Message):
            if message.author.bot or message.author == self._bot.user:
                return

            # Check authorization if allowed_user_id is configured
            if self._allowed_user_id and str(message.author.id) != self._allowed_user_id:
                return

            content = message.content.strip()
            if not content:
                return

            # Process commands like !join, !call, !leave, !screen, !say, !speak
            if content.startswith("!join") or content.startswith("!call"):
                await self._handle_voice_join(message)
                return

            if content.startswith("!leave") or content.startswith("!stop"):
                await self._handle_voice_leave(message)
                return

            if content.startswith("!screen") or content.startswith("!screenshot"):
                await self._handle_screenshot(message)
                return

            if content.startswith("!say ") or content.startswith("!speak "):
                text_to_say = content.split(" ", 1)[1].strip()
                if text_to_say:
                    if self._voice_client and self._voice_client.is_connected():
                        await message.reply(f"🗣️ *Speaking in voice:* \"{text_to_say}\"")
                        await self._speak_in_voice_async(text_to_say)
                    else:
                        await message.reply("Sir, please type `!call` first so I can join the voice channel, then I will speak.")
                return

            if content == "!testvoice" or content == "!testcall":
                if self._voice_client and self._voice_client.is_connected():
                    await self._speak_in_voice_async("Testing Discord voice transmission. All systems operational, Sir Maki.")
                    await message.reply("🎙️ Played test audio in voice channel, sir.")
                else:
                    await self._handle_voice_join(message)
                return

            # Normal conversation / commands -> Route through Orchestrator
            async with message.channel.typing():
                try:
                    resp = await asyncio.to_thread(self.orchestrator.handle_command, content)
                    if resp:
                        await message.reply(resp)
                        # If voice connected, speak it in voice too
                        if self._voice_client and self._voice_client.is_connected():
                            await self._speak_in_voice_async(resp)
                except Exception as e:
                    await message.reply(f"⚠️ Error processing command: {e}")

        try:
            self._loop.run_until_complete(self._bot.start(self._token))
        except Exception as e:
            print(f"[DiscordBridge] Discord runtime error: {e}")
        finally:
            self._running = False

    # ─── Voice Channel Operations ─────────────────────────────────────────────

    async def _handle_voice_join(self, message: discord.Message):
        """Join voice channel when user calls."""
        # Find user's current voice channel or default configured channel
        v_channel = None
        if message.author.voice and message.author.voice.channel:
            v_channel = message.author.voice.channel
        elif self._voice_channel_id:
            v_channel = self._bot.get_channel(int(self._voice_channel_id))

        if not v_channel:
            await message.reply("Sir, please join the **General** voice channel so I can connect to you.")
            return

        try:
            if self._voice_client and self._voice_client.is_connected():
                if self._voice_client.channel.id != v_channel.id:
                    await self._voice_client.move_to(v_channel)
            else:
                self._voice_client = await v_channel.connect()

            await asyncio.sleep(1.0)  # Allow Discord voice UDP socket to initialize
            await message.reply(f"🎙️ Connected to **{v_channel.name}**. Standing by for voice briefing, sir.")
            await self._speak_in_voice_async("Sir Maki, I have joined your Discord voice channel. System is operational and standing by.")
        except Exception as e:
            print(f"[DiscordBridge] Voice connect error: {e}")
            await message.reply(f"⚠️ Failed to connect to voice: {e}")

    async def _handle_voice_leave(self, message: discord.Message):
        """Disconnect from voice channel."""
        if self._voice_client and self._voice_client.is_connected():
            await self._voice_client.disconnect()
            self._voice_client = None
            await message.reply("👋 Disconnected from voice channel, sir.")
        else:
            await message.reply("I am not currently connected to any voice channel, sir.")

    async def _handle_screenshot(self, message: discord.Message):
        """Capture screenshot and post in Discord."""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(all_screens=True)
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            file = discord.File(fp=img_bytes, filename="screenshot.png")
            await message.reply("📸 Here is your desktop screen capture, sir:", file=file)
        except Exception as e:
            await message.reply(f"⚠️ Screenshot capture failed: {e}")

    # ─── Outbound Voice & Notification Methods ────────────────────────────────

    async def _speak_in_voice_async(self, text: str) -> bool:
        """Synthesize text via Edge-TTS and stream into connected voice channel."""
        if not self._voice_client or not self._voice_client.is_connected():
            return False

        try:
            import edge_tts
            temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_mp3_path = temp_mp3.name
            temp_mp3.close()

            communicate = edge_tts.Communicate(text, voice="en-GB-RyanNeural", rate="+2%", pitch="-8Hz")
            await communicate.save(temp_mp3_path)

            if self._voice_client.is_playing():
                self._voice_client.stop()

            source = discord.FFmpegPCMAudio(temp_mp3_path)
            self._voice_client.play(source, after=lambda e: self._cleanup_file(temp_mp3_path))
            return True
        except Exception as e:
            print(f"[DiscordBridge] Voice playback error: {e}")
            return False

    def _cleanup_file(self, path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def speak_in_voice(self, text: str) -> bool:
        """Thread-safe public method to speak text in Discord voice."""
        if not self._bot or not self._loop or not self._loop.is_running():
            return False
        try:
            future = asyncio.run_coroutine_threadsafe(self._speak_in_voice_async(text), self._loop)
            return True
        except Exception as e:
            print(f"[DiscordBridge] Schedule voice error: {e}")
            return False

    def send_notification(self, text: str) -> bool:
        """Thread-safe public method to post text/alert in Discord channel."""
        if not self._bot or not self._loop or not self._loop.is_running():
            return False

        async def _async_send():
            try:
                target_id = self._text_channel_id or self._voice_channel_id
                if target_id:
                    ch = self._bot.get_channel(int(target_id))
                    if ch:
                        await ch.send(text)
            except Exception as e:
                print(f"[DiscordBridge] Outbound message error: {e}")

        try:
            asyncio.run_coroutine_threadsafe(_async_send(), self._loop)
            return True
        except Exception as e:
            print(f"[DiscordBridge] Schedule notification error: {e}")
            return False
