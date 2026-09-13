"""
MakiAI — Telegram Remote Mobile Bridge (telegram_service.py)
Provides 24/7 mobile access and remote desktop control from your smartphone.

Features:
  1. Whitelist Security: Only responds to your authorized Telegram User ID.
  2. Text Commands: Full access to all MakiAI skills, deadlines, schedule, and general AI.
  3. Voice Notes: Downloads voice memos from phone, transcribes via Groq Whisper, and replies.
  4. Homework Rubric Ingestion: Drops rubric photos/PDFs into School/Temp-Guide/, generates Word .docx,
     and uploads the .docx document straight back to your phone chat!
  5. Desktop Screen Remote: /screenshot captures all PC monitors and sends photo to Telegram.
  6. Zero Blocking: Runs in an isolated background asyncio daemon thread.
"""

import os
import io
import time
import asyncio
import threading
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from services.voice.audio_transcriber import AudioTranscriber
from services.storage.maki_sync import StorageSecurityGuard, MAKI_SYNC_ROOT

TEMP_GUIDE_DIR = Path(r"C:\MakiSync Storage\School\Temp-Guide")


class TelegramRemoteService:
    """
    Background Telegram Bot Bridge for MakiAI.
    Connects smartphone messages to the core Orchestrator.
    """

    def __init__(
        self,
        settings_service,
        orchestrator,
        state_manager=None,
        tts_service=None,
        skill_router=None,
    ):
        self.settings = settings_service
        self.orchestrator = orchestrator
        self.state_manager = state_manager
        self.tts_service = tts_service
        self.skill_router = skill_router

        self._token: str = self.settings.get_env("TELEGRAM_BOT_TOKEN", "").strip()
        self._allowed_user_id: str = self.settings.get_env("TELEGRAM_ALLOWED_USER_ID", "").strip()
        self._transcriber = AudioTranscriber()

        self._app: Optional[Application] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running: bool = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Initialize and run Telegram bot in a non-blocking background thread."""
        self._token = self.settings.get_env("TELEGRAM_BOT_TOKEN", "").strip()
        self._allowed_user_id = self.settings.get_env("TELEGRAM_ALLOWED_USER_ID", "").strip()

        if not self._token or self._token.startswith("your_"):
            print("[TelegramBridge] No TELEGRAM_BOT_TOKEN found. Mobile bridge paused.")
            return False

        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(
            target=self._run_bot_thread,
            name="TelegramBridgeThread",
            daemon=True,
        )
        self._thread.start()
        print("[TelegramBridge] Mobile Telegram Bridge started in background.")
        return True

    def stop(self) -> None:
        """Stop the background bot polling loop."""
        self._running = False
        if self._app and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._app.stop(), self._loop)
            print("[TelegramBridge] Telegram Mobile Bridge stopped.")

    # ─── Internal Event Loop ──────────────────────────────────────────────────

    def _run_bot_thread(self) -> None:
        """Dedicated asyncio event loop for python-telegram-bot."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _main_async_runner():
            self._app = ApplicationBuilder().token(self._token).build()

            # Command Handlers
            self._app.add_handler(CommandHandler("start", self._cmd_start))
            self._app.add_handler(CommandHandler("help", self._cmd_help))
            self._app.add_handler(CommandHandler("status", self._cmd_status))
            self._app.add_handler(CommandHandler("screenshot", self._cmd_screenshot))
            self._app.add_handler(CommandHandler("screen", self._cmd_screenshot))
            self._app.add_handler(CommandHandler("file", self._cmd_file))
            self._app.add_handler(CommandHandler("get", self._cmd_file))

            # Media & Content Handlers
            self._app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, self._handle_voice))
            self._app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, self._handle_document_or_photo))
            self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))

            await self._app.initialize()
            await self._app.start()
            await self._app.updater.start_polling(drop_pending_updates=False)
            print("[TelegramBridge] Polling active! Ready to receive messages from smartphone.")

            while self._running:
                await asyncio.sleep(0.5)

            if self._app.updater and self._app.updater.running:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

        try:
            self._loop.run_until_complete(_main_async_runner())
        except Exception as e:
            print(f"[TelegramBridge] Runtime error: {e}")
        finally:
            self._running = False

    # ─── Security Guard ───────────────────────────────────────────────────────

    def _is_authorized(self, update: Update) -> bool:
        """Verify that incoming message is from the authorized user ID."""
        if not update.effective_user:
            return False

        if not self._allowed_user_id:
            # Auto-pair: If no allowed ID was set yet, log the first user's ID
            sender_id = str(update.effective_user.id)
            print(f"[TelegramBridge] Successfully paired with User ID: {sender_id}. Saved to config.")
            self._allowed_user_id = sender_id
            self.settings.set_env("TELEGRAM_ALLOWED_USER_ID", sender_id)
            return True

        sender_id = str(update.effective_user.id)
        if sender_id == str(self._allowed_user_id).strip():
            return True

        print(f"[TelegramBridge] Blocked unauthorized access from User ID: {sender_id} ({update.effective_user.username})")
        return False

    # ─── Bot Handlers ─────────────────────────────────────────────────────────

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start greeting."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized access. This MakiAI assistant is private.")
            return

        user_name = update.effective_user.first_name or "sir"
        await update.message.reply_text(
            f"👋 Greetings, {user_name}!\n\n"
            "MakiAI Mobile Remote Bridge is connected and online.\n\n"
            "📱 **You can send me:**\n"
            "• **Text Messages**: Any task, deadline, schedule check, or research.\n"
            "• **Voice Notes**: Speak naturally — I'll transcribe and execute.\n"
            "• **Photos / Rubric PDFs**: Forward your school rubrics, and I'll generate your Word `.docx` assignment and send it right back!\n"
            "• **/screenshot**: Capture and view your PC desktop screen right now."
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not self._is_authorized(update):
            return
        await update.message.reply_text(
            "📋 **MakiAI Mobile Commands:**\n\n"
            "• `/status` - Check PC status, time, and active state\n"
            "• `/screenshot` - Send live desktop capture\n"
            "• `What is my schedule today?`\n"
            "• `Remind me at 8 PM to [task]`\n"
            "• `Add deadline: [task] due Friday`\n"
            "• Attach a photo/PDF rubric to generate Word homework!"
        )

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Report PC and assistant status."""
        if not self._is_authorized(update):
            return
        pht_time = time.strftime("%I:%M %p PHT")
        await update.message.reply_text(
            f"🟢 **MakiAI Desktop Core is Online**\n"
            f"🕒 Current Time: {pht_time}\n"
            f"💻 Host: Windows Desktop\n"
            f"⚡ Remote Bridge: Active"
        )

    async def _cmd_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Capture and send multi-monitor screenshot to Telegram."""
        if not self._is_authorized(update):
            return

        await update.message.reply_text("📸 Capturing desktop screens...")
        try:
            import pyautogui
            screenshot = await asyncio.to_thread(pyautogui.screenshot)
            bio = io.BytesIO()
            bio.name = "desktop_screenshot.png"
            screenshot.save(bio, "PNG")
            bio.seek(0)
            await update.message.reply_photo(photo=bio, caption="🖥️ Current Desktop Screen View")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to capture screenshot: {e}")

    async def _cmd_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /file or /get <filename or search term>."""
        if not self._is_authorized(update):
            return
        query = " ".join(context.args).strip() if context.args else ""
        if not query:
            await update.message.reply_text("Please specify a filename, sir. Example: `/file Prompt.md` or `/file assignment.docx`", parse_mode="Markdown")
            return
        await self._find_and_send_file(query, update, context)

    async def _find_and_send_file(self, query: str, update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
        """Search local storage, projects, and documents, then send matching file."""
        clean_q = query.strip().strip('"').strip("'")

        # 1. Direct path check
        direct_p = Path(clean_q)
        if direct_p.is_file() and direct_p.exists():
            return await self._send_single_file(direct_p, update)

        # 2. Fast Prioritized Search Roots
        priority_roots = [
            Path(r"C:\capstone\CV"),
            Path(r"C:\capstone"),
            Path(r"C:\MakiSync Storage"),
            Path(r"C:\Knowledge-Base"),
            Path.home() / "Documents",
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path(r"C:\development\Python\MakiAI"),
        ]

        matches = []
        q_lower = clean_q.lower()
        is_cv_query = any(k in q_lower for k in ("cv", "resume", "curriculum vitae"))
        ignore_dirs = {"venv", ".git", "__pycache__", "node_modules", "vendor", "obj", "bin", "build", "dist", ".next"}

        for root in priority_roots:
            if not root.exists():
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(str(root)):
                    # Prune ignore directories in-place for fast traversal
                    dirnames[:] = [d for d in dirnames if d.lower() not in ignore_dirs and not d.startswith(".")]
                    
                    for fn in filenames:
                        fn_lower = fn.lower()
                        p_obj = Path(dirpath) / fn
                        # If looking for CV, match CV / resume in filename
                        if is_cv_query:
                            if any(k in fn_lower for k in ("_cv", "cv_", "-cv", "cv.", "resume", "cv")) or "cv" in fn_lower:
                                if p_obj not in matches:
                                    matches.append(p_obj)
                        elif q_lower in fn_lower:
                            if p_obj not in matches:
                                matches.append(p_obj)

                        if len(matches) >= 5:
                            break
                    if len(matches) >= 5:
                        break
            except Exception:
                pass
            if len(matches) >= 5:
                break

        if not matches:
            await update.message.reply_text(f"🔍 I searched your PC folders (`C:\\capstone\\CV`, `MakiSync Storage`, Documents) for `{clean_q}`, but couldn't find a matching file, sir.", parse_mode="Markdown")
            return False

        # If PDF exists among matches, prioritize sending the PDF
        matches.sort(key=lambda p: (0 if p.suffix.lower() == ".pdf" else (1 if p.suffix.lower() == ".docx" else 2)))
        target_file = matches[0]
        return await self._send_single_file(target_file, update, additional_matches=matches[1:])

    async def _send_single_file(self, file_path: Path, update: Update, additional_matches: list = None) -> bool:
        """Send a single file document to Telegram chat after checking security guard."""
        try:
            # Enforce storage security guard: Never leak credentials or sensitive system files
            if not StorageSecurityGuard.is_safe_for_remote_sending(file_path):
                await update.message.reply_text(f"🛡️ **Security Block:** `{file_path.name}` is a protected system credential and cannot be sent over remote chat, sir.", parse_mode="Markdown")
                return False

            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 49.0:
                await update.message.reply_text(f"⚠️ File `{file_path.name}` is {file_size_mb:.1f} MB (Telegram bot limit is 50 MB).", parse_mode="Markdown")
                return False

            await update.message.reply_text(f"📤 Uploading `{file_path.name}` from `{file_path.parent}` to your phone...", parse_mode="Markdown")
            with open(file_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=file_path.name,
                    caption=f"📄 {file_path.name}\n📍 {file_path.parent}"
                )

            if additional_matches:
                other_names = "\n".join([f"• `{p.name}` in `{p.parent.name}`" for p in additional_matches[:3]])
                await update.message.reply_text(f"ℹ️ Other matching files found:\n{other_names}", parse_mode="Markdown")
            return True
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to send file `{file_path.name}`: {e}", parse_mode="Markdown")
            return False

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process incoming text message through Orchestrator."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        text = (update.message.text or "").strip()
        if not text:
            return

        # Check if user asked to send/upload a file (e.g. "send me my CV", "send me the CV pdf", "send file Prompt.md")
        import re
        file_match = re.search(
            r"^(?:hey\s+|hi\s+|ok\s+)?(?:maki[,.]?\s*)?(?:can\s+you\s+|please\s+)?(?:send|upload|give|get|fetch)\s+(?:me\s+)?(?:the\s+|my\s+)?(?:file\s+|document\s+|pdf\s+)?(.+)$",
            text,
            flags=re.IGNORECASE
        )
        if file_match:
            candidate = file_match.group(1).strip().rstrip(".!?")
            # Strip trailing word like 'pdf' or 'file' if user said 'cv pdf' or 'notes document'
            candidate = re.sub(r"\s+(?:pdf|docx|file|document)$", "", candidate, flags=re.IGNORECASE).strip()
            if candidate and not any(k in candidate.lower() for k in ("schedule", "time", "weather", "screenshot", "status", "hi", "hello")):
                handled = await self._find_and_send_file(candidate, update)
                if handled:
                    return

        # Let user know Maki is thinking
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        try:
            response = await asyncio.to_thread(self.orchestrator.handle_command, text)
            if not response:
                response = "I processed your request, sir."

            await update.message.reply_text(response)

            # If a Word document was generated during this command, send the file too!
            if self.skill_router:
                hw_skill = self.skill_router.get_skill("homework")
                if hw_skill and getattr(hw_skill, "last_generated_docx", None):
                    docx_path = hw_skill.last_generated_docx
                    if docx_path and Path(docx_path).exists():
                        with open(docx_path, "rb") as doc_file:
                            await update.message.reply_document(
                                document=doc_file,
                                filename=Path(docx_path).name,
                                caption=f"📄 Generated Assignment: {Path(docx_path).name}"
                            )
                        hw_skill.last_generated_docx = None

        except Exception as e:
            await update.message.reply_text(f"⚠️ Error executing command: {e}")

    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Download voice note from Telegram, transcribe via Groq Whisper, and execute."""
        if not self._is_authorized(update):
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
        voice = update.message.voice or update.message.audio
        if not voice:
            return

        try:
            # Download voice file bytes
            file_obj = await context.bot.get_file(voice.file_id)
            byte_array = await file_obj.download_as_bytearray()
            raw_bytes = bytes(byte_array)

            # Transcribe with Groq Whisper
            transcribed_text, provider = await asyncio.to_thread(self._transcriber.transcribe_wav_bytes, raw_bytes)
            if not transcribed_text or len(transcribed_text.strip()) < 2:
                await update.message.reply_text("I heard your voice note, but couldn't make out the words clearly, sir.")
                return

            await update.message.reply_text(f"🗣️ *Heard:* \"{transcribed_text}\"", parse_mode="Markdown")

            # Route through Orchestrator
            response = await asyncio.to_thread(self.orchestrator.handle_command, transcribed_text)
            if response:
                await update.message.reply_text(response)

        except Exception as e:
            print(f"[TelegramBridge] Voice handler error: {e}")
            await update.message.reply_text(f"⚠️ Voice processing error: {e}")

    async def _handle_document_or_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Download incoming school rubric photo/PDF, drop it into Temp-Guide/,
        and trigger automatic Word .docx generation!
        """
        if not self._is_authorized(update):
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")
        TEMP_GUIDE_DIR.mkdir(parents=True, exist_ok=True)

        caption = (update.message.caption or "").strip()
        filename = f"rubric_{int(time.time())}"
        target_path = None

        try:
            if update.message.photo:
                # Get highest resolution photo
                photo = update.message.photo[-1]
                file_obj = await context.bot.get_file(photo.file_id)
                target_path = TEMP_GUIDE_DIR / f"{filename}.jpg"
                StorageSecurityGuard.assert_write_permitted(target_path)
                await file_obj.download_to_drive(str(target_path))
                await update.message.reply_text(f"📥 Received rubric photo. Saved to `Temp-Guide/{target_path.name}`.", parse_mode="Markdown")

            elif update.message.document:
                doc = update.message.document
                file_obj = await context.bot.get_file(doc.file_id)
                orig_name = doc.file_name or f"{filename}.pdf"
                target_path = TEMP_GUIDE_DIR / orig_name
                StorageSecurityGuard.assert_write_permitted(target_path)
                await file_obj.download_to_drive(str(target_path))
                await update.message.reply_text(f"📥 Received document: `{orig_name}`. Saved to `Temp-Guide/`.", parse_mode="Markdown")

            # If user provided instructions in the caption, generate homework immediately!
            if caption and self.skill_router:
                hw_skill = self.skill_router.get_skill("homework")
                if hw_skill:
                    await update.message.reply_text("⚙️ Reading rubric and generating your Microsoft Word `.docx` assignment...")
                    result_msg = hw_skill.create_homework(caption)
                    await update.message.reply_text(result_msg)

                    # Return the generated .docx file to Telegram!
                    if getattr(hw_skill, "last_generated_docx", None):
                        docx_path = hw_skill.last_generated_docx
                        if docx_path and Path(docx_path).exists():
                            with open(docx_path, "rb") as doc_file:
                                await update.message.reply_document(
                                    document=doc_file,
                                    filename=Path(docx_path).name,
                                    caption=f"📄 Here is your generated assignment, sir: {Path(docx_path).name}"
                                )
                            hw_skill.last_generated_docx = None
            else:
                await update.message.reply_text(
                    "💡 **Rubric saved in Temp-Guide!**\n"
                    "Now send me your instructions (e.g., *'Write a 2-page essay on Network Security following this rubric'*), "
                    "and I'll create your Word `.docx` document and send it back to your phone!"
                )

        except Exception as e:
            print(f"[TelegramBridge] Document/Photo error: {e}")
            await update.message.reply_text(f"⚠️ Failed to process file: {e}")
