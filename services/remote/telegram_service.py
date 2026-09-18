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
import re
import time
import asyncio
import threading
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from typing import Optional, Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from services.voice.audio_transcriber import AudioTranscriber
from services.storage.maki_sync import StorageSecurityGuard, MAKI_SYNC_ROOT

TEMP_GUIDE_DIR = MAKI_SYNC_ROOT / "School" / "Temp-Guide"


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _format_mtime(mtime_ts: float) -> str:
    """Format file modification timestamp to readable string."""
    try:
        dt = datetime.fromtimestamp(mtime_ts)
        now = datetime.now()
        if dt.date() == now.date():
            return f"Today {dt.strftime('%I:%M %p')}"
        elif (now.date() - dt.date()).days == 1:
            return f"Yesterday {dt.strftime('%I:%M %p')}"
        elif (now.date() - dt.date()).days < 7:
            return dt.strftime("%a %I:%M %p")
        else:
            return dt.strftime("%b %d, %Y")
    except Exception:
        return "Unknown date"


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

        self._pending_folder_choices: Dict[int, List[Path]] = {}
        self._pending_file_choices: Dict[int, List[Path]] = {}
        self._last_search_folder_map: Dict[int, Dict[Path, List[Path]]] = {}
        self._last_search_query: Dict[int, str] = {}
        self._picker_step: Dict[int, str] = {}  # "folder" or "file"

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
            self._app.add_handler(CommandHandler("camera", self._cmd_camera))
            self._app.add_handler(CommandHandler("photo", self._cmd_camera))
            self._app.add_handler(CommandHandler("lastphoto", lambda u, c: self._send_last_photo(u)))
            self._app.add_handler(CommandHandler("lastcamera", lambda u, c: self._send_last_photo(u)))
            self._app.add_handler(CommandHandler("lastscreenshot", lambda u, c: self._send_last_screenshot(u)))
            self._app.add_handler(CommandHandler("lastscreen", lambda u, c: self._send_last_screenshot(u)))
            self._app.add_handler(CommandHandler("file", self._cmd_file))
            self._app.add_handler(CommandHandler("get", self._cmd_file))
            self._app.add_handler(CommandHandler("browse", self._cmd_browse))
            self._app.add_handler(CommandHandler("folders", self._cmd_browse))

            # Media & Content Handlers
            self._app.add_handler(CallbackQueryHandler(self._handle_callback))
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
            "📋 **MakiAI Mobile Remote Commands:**\n\n"
            "📷 **Camera & Visuals:**\n"
            "• `send me the last camera capture` or `/lastphoto` - Get your most recent camera picture\n"
            "• `send me the last screenshot` or `/lastscreenshot` - Get your most recent screenshot\n"
            "• `take a photo` or `/camera` - Snap live photo from webcam\n"
            "• `take a screenshot` or `/screenshot` - Capture live desktop screen\n\n"
            "📁 **Files & Storage:**\n"
            "• `/browse` or `browse capstone` - 2-step interactive folder & file explorer\n"
            "• `send me [filename/query]` (e.g. `send my CV`, `send capstone paper`)\n\n"
            "🧠 **Productivity & Schedule:**\n"
            "• `What is my schedule today?`\n"
            "• `Remind me at 8 PM to [task]`\n"
            "• `Add deadline: [task] due Friday`\n"
            "• Forward rubric photos/PDFs to generate Word homework!",
            parse_mode="Markdown"
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

    async def _cmd_camera(self, update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> None:
        """Capture a live webcam photo and send to Telegram."""
        if not self._is_authorized(update):
            return

        chat_obj = update.message or (update.callback_query.message if update.callback_query else None)
        if chat_obj:
            await chat_obj.reply_text("📷 Accessing webcam and capturing photo...")

        try:
            import cv2
            def _capture_frame():
                cap = None
                for dev_idx in [0, 1]:
                    try:
                        cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW)
                        if not cap.isOpened():
                            cap.release()
                            cap = cv2.VideoCapture(dev_idx)
                        if cap and cap.isOpened():
                            break
                    except Exception:
                        if cap:
                            cap.release()
                        cap = None

                if not cap or not cap.isOpened():
                    return None, "I couldn't access your webcam device, sir."

                for _ in range(5):
                    cap.read()
                    time.sleep(0.04)

                ret, frame = cap.read()
                cap.release()

                if not ret or frame is None:
                    return None, "Failed to grab frame from webcam."

                # Save photo to MakiSync Storage/Photos/YYYY-MM-DD
                from services.storage.maki_sync import get_dated_folder
                save_dir = get_dated_folder("Photos")
                save_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_file = save_dir / f"photo_{ts}.jpg"
                cv2.imwrite(str(save_file), frame)

                ret_enc, buf = cv2.imencode(".jpg", frame)
                if not ret_enc:
                    return None, "Failed to encode image."

                return buf.tobytes(), str(save_file)

            raw_bytes, result_info = await asyncio.to_thread(_capture_frame)
            if not raw_bytes:
                if chat_obj:
                    await chat_obj.reply_text(f"⚠️ {result_info}")
                return

            bio = io.BytesIO(raw_bytes)
            bio.name = "webcam_capture.jpg"
            bio.seek(0)

            pht_time = datetime.now().strftime("%I:%M %p")
            if chat_obj:
                await chat_obj.reply_photo(
                    photo=bio,
                    caption=f"📷 **Live Webcam Capture**\n🕒 Today at {pht_time}\n💾 Saved to `{Path(result_info).name}`",
                    parse_mode="Markdown"
                )
        except Exception as e:
            if chat_obj:
                await chat_obj.reply_text(f"❌ Camera capture error: {e}")

    async def _send_last_photo(self, update: Update) -> None:
        """Find the most recently captured camera photo and send to Telegram."""
        if not self._is_authorized(update):
            return

        chat_obj = update.message or (update.callback_query.message if update.callback_query else None)
        if chat_obj:
            await chat_obj.reply_text("🔍 Locating your latest camera capture...")

        try:
            from services.storage.maki_sync import MAKI_SYNC_ROOT
            search_dirs = [
                MAKI_SYNC_ROOT / "Photos",
                Path.home() / "Pictures" / "MakiAI",
                Path.home() / "Pictures" / "Camera Roll",
                Path.home() / "Pictures",
            ]

            photo_candidates = []
            valid_exts = {".jpg", ".jpeg", ".png"}

            for root in search_dirs:
                if not root.exists():
                    continue
                for dirpath, _, filenames in os.walk(str(root)):
                    for fn in filenames:
                        p = Path(dirpath) / fn
                        if p.suffix.lower() in valid_exts and not p.name.startswith("."):
                            try:
                                photo_candidates.append((p.stat().st_mtime, p))
                            except Exception:
                                pass

            if not photo_candidates:
                if chat_obj:
                    await chat_obj.reply_text("📷 No camera photos found in your storage yet, sir. You can type `take a photo` to capture one now!")
                return

            photo_candidates.sort(key=lambda x: x[0], reverse=True)
            last_mtime, latest_photo = photo_candidates[0]
            mtime_str = _format_mtime(last_mtime)

            if chat_obj:
                with open(latest_photo, "rb") as f:
                    await chat_obj.reply_photo(
                        photo=f,
                        caption=f"📷 **Latest Camera Capture**\n📄 `{latest_photo.name}`\n🕒 Modified: {mtime_str}\n📍 `{latest_photo.parent}`",
                        parse_mode="Markdown"
                    )
        except Exception as e:
            if chat_obj:
                await chat_obj.reply_text(f"❌ Failed to fetch latest photo: {e}")

    async def _send_last_screenshot(self, update: Update) -> None:
        """Find the most recently captured desktop screenshot and send to Telegram."""
        if not self._is_authorized(update):
            return

        chat_obj = update.message or (update.callback_query.message if update.callback_query else None)
        if chat_obj:
            await chat_obj.reply_text("🔍 Locating your latest desktop screenshot...")

        try:
            from services.storage.maki_sync import MAKI_SYNC_ROOT
            search_dirs = [
                MAKI_SYNC_ROOT / "Screenshots",
                Path.home() / "Pictures" / "Screenshots",
                Path.home() / "Pictures" / "MakiAI",
                Path.home() / "Pictures",
            ]

            ss_candidates = []
            valid_exts = {".png", ".jpg", ".jpeg"}

            for root in search_dirs:
                if not root.exists():
                    continue
                for dirpath, _, filenames in os.walk(str(root)):
                    for fn in filenames:
                        p = Path(dirpath) / fn
                        if p.suffix.lower() in valid_exts and not p.name.startswith("."):
                            try:
                                ss_candidates.append((p.stat().st_mtime, p))
                            except Exception:
                                pass

            if not ss_candidates:
                if chat_obj:
                    await chat_obj.reply_text("🖥️ No screenshots found in your storage yet, sir. Type `/screenshot` to capture one right now!")
                return

            ss_candidates.sort(key=lambda x: x[0], reverse=True)
            last_mtime, latest_ss = ss_candidates[0]
            mtime_str = _format_mtime(last_mtime)

            if chat_obj:
                with open(latest_ss, "rb") as f:
                    await chat_obj.reply_photo(
                        photo=f,
                        caption=f"🖥️ **Latest Desktop Screenshot**\n📄 `{latest_ss.name}`\n🕒 Modified: {mtime_str}\n📍 `{latest_ss.parent}`",
                        parse_mode="Markdown"
                    )
        except Exception as e:
            if chat_obj:
                await chat_obj.reply_text(f"❌ Failed to fetch latest screenshot: {e}")

    async def _cmd_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /file or /get <filename or search term>."""
        if not self._is_authorized(update):
            return
        query = " ".join(context.args).strip() if context.args else ""
        if not query:
            await update.message.reply_text("Please specify a filename, sir. Example: `/file capstone paper` or `/file Mark_CV`", parse_mode="Markdown")
            return
        await self._find_and_send_file(query, update, context)

    async def _cmd_browse(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /browse or /folders to explore PC directories interactively."""
        if not self._is_authorized(update):
            return

        target_dir_str = " ".join(context.args).strip() if context.args else ""
        await self._render_folder_browser(target_dir_str, update)

    async def _render_folder_browser(self, target_folder_str: str, update: Update) -> None:
        """Render an interactive folder navigation list with buttons."""
        default_roots = [
            ("🎓 Capstone", Path(r"C:\capstone")),
            ("📁 MakiSync Storage", Path(r"C:\MakiSync Storage")),
            ("🧠 Knowledge-Base", Path(r"C:\Knowledge-Base")),
            ("📄 Documents", Path.home() / "Documents"),
            ("🖥️ Desktop", Path.home() / "Desktop"),
            ("⬇️ Downloads", Path.home() / "Downloads"),
        ]

        # If no specific folder was requested, show root hub
        if not target_folder_str:
            buttons = []
            for label, p in default_roots:
                if p.exists():
                    buttons.append([InlineKeyboardButton(label, callback_data=f"browse_dir:{p}")])
            buttons.append([InlineKeyboardButton("❌ Close", callback_data="cancel_picker")])

            msg = "📂 *MakiAI PC Storage Explorer*\nSelect a folder to browse its files:"
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
            return

        # Resolve folder
        folder_path = None
        for _, p in default_roots:
            if target_folder_str.lower() in p.name.lower() or target_folder_str.lower() in str(p).lower():
                folder_path = p
                break
        if not folder_path:
            folder_path = Path(target_folder_str)

        if not folder_path.exists() or not folder_path.is_dir():
            await update.message.reply_text(f"⚠️ Folder `{target_folder_str}` does not exist.", parse_mode="Markdown")
            return

        try:
            subdirs = []
            files = []
            ignore = {"venv", ".git", "__pycache__", "node_modules", "vendor", "obj", "bin", "build", "dist"}
            
            for item in folder_path.iterdir():
                if item.name.startswith(".") or item.name.lower() in ignore:
                    continue
                if item.is_dir():
                    subdirs.append(item)
                elif item.is_file():
                    files.append(item)

            # Sort files by newest first
            files.sort(key=lambda f: f.stat().st_mtime if f.exists() else 0, reverse=True)

            text_lines = [f"📂 *Folder:* `{folder_path}`\n"]
            if subdirs:
                text_lines.append("📁 *Subfolders:*")
                for d in subdirs[:6]:
                    text_lines.append(f"  • `{d.name}/`")
                text_lines.append("")

            text_lines.append(f"📄 *Files ({len(files)} total):*")
            buttons = []

            # Save files to pending choices for direct button click or number selection
            chat_id = update.effective_chat.id
            self._pending_file_choices[chat_id] = files[:10]

            for idx, f in enumerate(files[:10], start=1):
                mtime_str = _format_mtime(f.stat().st_mtime)
                size_str = _format_size(f.stat().st_size)
                text_lines.append(f"  **[{idx}]** `{f.name}` ({size_str}) • _{mtime_str}_")
                buttons.append([InlineKeyboardButton(f"📄 {idx}. {f.name[:35]}", callback_data=f"pickfile:{idx-1}")])

            if subdirs:
                sub_row = []
                for d in subdirs[:4]:
                    sub_row.append(InlineKeyboardButton(f"📁 {d.name[:18]}", callback_data=f"browse_dir:{d}"))
                buttons.insert(0, sub_row)

            buttons.append([InlineKeyboardButton("❌ Close", callback_data="cancel_picker")])

            reply_text = "\n".join(text_lines)
            if len(reply_text) > 4000:
                reply_text = reply_text[:3950] + "\n..."

            await update.message.reply_text(reply_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"⚠️ Error reading folder: {e}")

    async def _find_and_send_file(self, query: str, update: Update, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
        """Search local storage, projects, and documents with smart fuzzy token ranking, then present choices or send."""
        clean_q = query.strip().strip('"').strip("'")

        # 1. Direct path check
        direct_p = Path(clean_q)
        if direct_p.is_file() and direct_p.exists():
            return await self._send_single_file(direct_p, update)

        # 2. Extract intent and keywords
        q_lower = clean_q.lower()
        wants_latest = any(w in q_lower for w in ("latest", "recent", "newest", "last", "new"))
        is_cv_query = any(k in q_lower for k in ("cv", "resume", "curriculum vitae"))

        # Strip stopwords to get core search tokens
        stop_words = {"latest", "recent", "newest", "last", "my", "the", "a", "an", "our", "me", "this", "send", "give", "get", "fetch", "file", "doc", "document"}
        raw_tokens = [re.sub(r"[^\w]", "", w) for w in q_lower.split()]
        tokens = [t for t in raw_tokens if t and t not in stop_words]
        
        # If all were stop words, keep original non-empty tokens
        if not tokens:
            tokens = [t for t in raw_tokens if t]

        # Prioritized roots
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

        scored_matches = []  # list of (score, mtime, Path)
        ignore_dirs = {"venv", ".git", "__pycache__", "node_modules", "vendor", "obj", "bin", "build", "dist", ".next", "appdata"}
        preferred_exts = {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".txt", ".md", ".csv", ".zip"}

        for root in priority_roots:
            if not root.exists():
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(str(root)):
                    dirnames[:] = [d for d in dirnames if d.lower() not in ignore_dirs and not d.startswith(".")]

                    for fn in filenames:
                        fn_lower = fn.lower()
                        p_obj = Path(dirpath) / fn
                        full_path_str = str(p_obj).lower()

                        score = 0
                        
                        # CV Special Check
                        if is_cv_query:
                            if any(k in fn_lower for k in ("_cv", "cv_", "-cv", "cv.", "resume", "cv")):
                                score += 200
                        else:
                            # 1. Exact phrase in filename
                            if q_lower in fn_lower:
                                score += 100

                            # 2. Token matches in filename
                            matching_tokens_fn = [t for t in tokens if t in fn_lower]
                            score += len(matching_tokens_fn) * 40

                            # 3. Token matches in parent directory path (e.g. C:\capstone)
                            matching_tokens_dir = [t for t in tokens if t in full_path_str]
                            score += len(matching_tokens_dir) * 15

                        if score > 0:
                            # Preference for actual documents
                            if p_obj.suffix.lower() in preferred_exts:
                                score += 20
                            if p_obj.suffix.lower() == ".pdf":
                                score += 10
                            elif p_obj.suffix.lower() == ".docx":
                                score += 8

                            try:
                                mtime = p_obj.stat().st_mtime
                            except Exception:
                                mtime = 0

                            scored_matches.append((score, mtime, p_obj))
            except Exception:
                pass

        if not scored_matches:
            await update.message.reply_text(f"🔍 I searched your PC folders (`C:\\capstone`, `MakiSync Storage`, Documents, Desktop) for `{clean_q}`, but couldn't find a matching file, sir.", parse_mode="Markdown")
            return False

        # Sort matches by score/mtime
        scored_matches.sort(key=lambda item: (item[0] if not wants_latest else (item[0] // 30, item[1])), reverse=True)
        
        # Deduplicate paths while preserving rank order
        unique_matches = []
        seen_paths = set()
        for s, m, p in scored_matches:
            if str(p).lower() not in seen_paths:
                seen_paths.add(str(p).lower())
                unique_matches.append(p)

        # ── Case 1: Exactly 1 Match or direct CV match with 1 item ────────────
        if len(unique_matches) == 1 or (is_cv_query and len(unique_matches) <= 2):
            return await self._send_single_file(unique_matches[0], update)

        # ── Case 2: Group by Folder for 2-Step Selection ──────────────────────
        folder_map = defaultdict(list)
        for p in unique_matches[:20]:
            folder_map[p.parent].append(p)

        chat_id = update.effective_chat.id
        self._last_search_folder_map[chat_id] = folder_map
        self._last_search_query[chat_id] = clean_q
        folders_list = list(folder_map.keys())
        self._pending_folder_choices[chat_id] = folders_list

        if len(folders_list) == 1:
            # Single folder contains all matches -> Show files inside this folder directly
            await self._render_files_in_folder(folders_list[0], folder_map[folders_list[0]], update, is_new_message=True, can_go_back=False)
        else:
            # Multiple folders contain matches -> Present Folders First!
            await self._render_folder_selection(folders_list, folder_map, clean_q, update, is_new_message=True)
        return True

    async def _render_folder_selection(self, folders_list: List[Path], folder_map: Dict[Path, List[Path]], query_str: str, update: Update, is_new_message: bool = True) -> None:
        """Step 1: Render list of folders containing matching files."""
        chat_id = update.effective_chat.id
        self._picker_step[chat_id] = "folder"
        self._pending_folder_choices[chat_id] = folders_list

        total_files = sum(len(flist) for flist in folder_map.values())
        msg_lines = [
            f"🔍 *Found {total_files} matching files across {len(folders_list)} folders for* \"{query_str}\":\n",
            "📁 *Select a folder to view its files:*"
        ]

        buttons = []
        for idx, fpath in enumerate(folders_list[:8], start=1):
            file_count = len(folder_map.get(fpath, []))
            folder_display_name = fpath.name or str(fpath)
            msg_lines.append(f"  **[{idx}]** `{fpath}` ({file_count} file{'s' if file_count != 1 else ''})")
            buttons.append([InlineKeyboardButton(f"📁 {idx}. {folder_display_name[:32]} ({file_count})", callback_data=f"pickfolder:{idx-1}")])

        msg_lines.append("\n👉 *Tap a folder button below* or reply with the folder number (e.g. `1`):")
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_picker")])

        full_msg = "\n".join(msg_lines)
        if is_new_message or not update.callback_query:
            target_chat = update.message or (update.callback_query.message if update.callback_query else None)
            if target_chat:
                await target_chat.reply_text(
                    full_msg,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="Markdown"
                )
        else:
            await update.callback_query.edit_message_text(
                full_msg,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )

    async def _render_files_in_folder(self, folder_path: Path, files_list: List[Path], update: Update, is_new_message: bool = False, can_go_back: bool = True) -> None:
        """Step 2: Render files inside the chosen folder."""
        chat_id = update.effective_chat.id
        self._picker_step[chat_id] = "file"
        self._pending_file_choices[chat_id] = files_list

        msg_lines = [
            f"📂 *Folder:* `{folder_path}`\n",
            f"📄 *Files in this folder ({len(files_list)} total):*"
        ]

        buttons = []
        for idx, p in enumerate(files_list[:10], start=1):
            mtime_str = _format_mtime(p.stat().st_mtime if p.exists() else 0)
            size_str = _format_size(p.stat().st_size if p.exists() else 0)
            msg_lines.append(f"  **[{idx}]** `{p.name}` ({size_str}) • _{mtime_str}_")
            buttons.append([InlineKeyboardButton(f"📄 {idx}. {p.name[:36]}", callback_data=f"pickfile:{idx-1}")])

        msg_lines.append("\n👉 *Tap a file to download* or reply with the file number (e.g. `1` or `send 1`):")
        
        control_row = []
        if can_go_back:
            control_row.append(InlineKeyboardButton("🔙 Back to Folders", callback_data="back_to_folders"))
        control_row.append(InlineKeyboardButton("❌ Cancel", callback_data="cancel_picker"))
        buttons.append(control_row)

        full_msg = "\n".join(msg_lines)
        if len(full_msg) > 4000:
            full_msg = full_msg[:3950] + "\n..."

        if is_new_message or not update.callback_query:
            target_chat = update.message or (update.callback_query.message if update.callback_query else None)
            if target_chat:
                await target_chat.reply_text(
                    full_msg,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="Markdown"
                )
        else:
            await update.callback_query.edit_message_text(
                full_msg,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle interactive inline buttons from Telegram."""
        if not self._is_authorized(update):
            return

        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass

        data = query.data or ""
        chat_id = update.effective_chat.id

        if data.startswith("pickfolder:"):
            try:
                folder_idx = int(data.split(":")[1])
                folders = self._pending_folder_choices.get(chat_id, [])
                if 0 <= folder_idx < len(folders):
                    selected_folder = folders[folder_idx]
                    files_in_folder = self._last_search_folder_map.get(chat_id, {}).get(selected_folder, [])
                    await self._render_files_in_folder(selected_folder, files_in_folder, update, is_new_message=False, can_go_back=True)
                else:
                    await query.edit_message_text("⚠️ Folder selection session expired. Please search again.", parse_mode="Markdown")
            except Exception as e:
                await query.edit_message_text(f"❌ Folder selection error: {e}")

        elif data.startswith("pickfile:"):
            try:
                idx = int(data.split(":")[1])
                pending = self._pending_file_choices.get(chat_id, [])
                if 0 <= idx < len(pending):
                    selected_file = pending[idx]
                    await query.edit_message_text(f"✅ Selected: `{selected_file.name}`\nUploading to your chat...", parse_mode="Markdown")
                    await self._send_single_file(selected_file, update)
                else:
                    await query.edit_message_text("⚠️ This file selection session has expired. Please search again.", parse_mode="Markdown")
            except Exception as e:
                await query.edit_message_text(f"❌ Selection error: {e}")

        elif data == "back_to_folders":
            folders = self._pending_folder_choices.get(chat_id, [])
            folder_map = self._last_search_folder_map.get(chat_id, {})
            query_str = self._last_search_query.get(chat_id, "files")
            if folders and folder_map:
                await self._render_folder_selection(folders, folder_map, query_str, update, is_new_message=False)
            else:
                await query.edit_message_text("⚠️ Search session expired. Please search again.", parse_mode="Markdown")

        elif data.startswith("browse_dir:"):
            folder_str = data[len("browse_dir:"):]
            await self._render_folder_browser(folder_str, update)

        elif data == "cancel_picker":
            self._pending_folder_choices.pop(chat_id, None)
            self._pending_file_choices.pop(chat_id, None)
            self._picker_step.pop(chat_id, None)
            await query.edit_message_text("❌ Selection cancelled.")

    async def _send_single_file(self, file_path: Path, update: Update, additional_matches: list = None) -> bool:
        """Send a single file document to Telegram chat after checking security guard."""
        try:
            # Enforce storage security guard: Never leak credentials or sensitive system files
            if not StorageSecurityGuard.is_safe_for_remote_sending(file_path):
                msg = f"🛡️ **Security Block:** `{file_path.name}` is a protected system credential and cannot be sent over remote chat, sir."
                if update.message:
                    await update.message.reply_text(msg, parse_mode="Markdown")
                elif update.callback_query:
                    await update.callback_query.message.reply_text(msg, parse_mode="Markdown")
                return False

            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 49.0:
                msg = f"⚠️ File `{file_path.name}` is {file_size_mb:.1f} MB (Telegram bot limit is 50 MB)."
                if update.message:
                    await update.message.reply_text(msg, parse_mode="Markdown")
                elif update.callback_query:
                    await update.callback_query.message.reply_text(msg, parse_mode="Markdown")
                return False

            caption_text = f"📄 {file_path.name}\n📍 {file_path.parent}"
            chat_obj = update.message or (update.callback_query.message if update.callback_query else None)

            if chat_obj:
                await chat_obj.reply_text(f"📤 Uploading `{file_path.name}` from `{file_path.parent}` to your phone...", parse_mode="Markdown")
                with open(file_path, "rb") as f:
                    await chat_obj.reply_document(
                        document=f,
                        filename=file_path.name,
                        caption=caption_text
                    )
            return True
        except Exception as e:
            err_msg = f"❌ Failed to send file `{file_path.name}`: {e}"
            if update.message:
                await update.message.reply_text(err_msg, parse_mode="Markdown")
            elif update.callback_query:
                await update.callback_query.message.reply_text(err_msg, parse_mode="Markdown")
            return False

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process incoming text message through Orchestrator."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        text = (update.message.text or "").strip()
        if not text:
            return

        chat_id = update.effective_chat.id

        # Check 1: User replied with a number (e.g. "1", "2", "send 1", "folder 2", "pick 3")
        num_match = re.match(r"^(?:send\s+|list\s+|file\s+|folder\s+|pick\s+)?(\d{1,2})$", text, flags=re.IGNORECASE)
        if num_match:
            idx = int(num_match.group(1)) - 1
            current_step = self._picker_step.get(chat_id)

            if current_step == "folder":
                folders = self._pending_folder_choices.get(chat_id, [])
                if 0 <= idx < len(folders):
                    selected_folder = folders[idx]
                    files_in_folder = self._last_search_folder_map.get(chat_id, {}).get(selected_folder, [])
                    await self._render_files_in_folder(selected_folder, files_in_folder, update, is_new_message=True, can_go_back=True)
                    return
            elif current_step == "file":
                pending = self._pending_file_choices.get(chat_id, [])
                if 0 <= idx < len(pending):
                    selected_file = pending[idx]
                    await update.message.reply_text(f"✅ Selected: `{selected_file.name}`\nUploading to your chat...", parse_mode="Markdown")
                    await self._send_single_file(selected_file, update)
                    return

        # Check 2: User asked to browse folders (e.g. "browse capstone", "explore folders", "browse files", "folders")
        browse_match = re.search(r"^(?:browse|explore|open\s+folder|list\s+folder|show\s+folders?)(?:\s+(.+))?$", text, flags=re.IGNORECASE)
        if browse_match:
            folder_target = (browse_match.group(1) or "").strip()
            await self._render_folder_browser(folder_target, update)
            return

        # Check 3: Last Camera Capture / Photo Request (e.g. "send me the last camera capture you have taken", "last photo")
        if re.search(r"\b(?:last|latest|recent|previous)\s+(?:camera\s+(?:capture|shot|photo|picture|pic)|photo|picture|webcam\s+capture)\b", text, flags=re.IGNORECASE) or \
           re.search(r"\b(?:send|give|get|show|upload)\s+(?:me\s+)?(?:the\s+)?(?:last|latest|recent)\s+(?:camera\s+(?:capture|shot|photo|picture|pic)|photo|picture|webcam\s+capture)\b", text, flags=re.IGNORECASE):
            await self._send_last_photo(update)
            return

        # Check 4: Last Screenshot Request (e.g. "send me the last screenshot", "latest screenshot")
        if re.search(r"\b(?:last|latest|recent|previous)\s+screenshot\b", text, flags=re.IGNORECASE) or \
           re.search(r"\b(?:send|give|get|show|upload)\s+(?:me\s+)?(?:the\s+)?(?:last|latest|recent)\s+screenshot\b", text, flags=re.IGNORECASE):
            await self._send_last_screenshot(update)
            return

        # Check 5: Live Camera Snap (e.g. "take a photo", "snap photo", "capture camera")
        if re.search(r"^(?:take\s+(?:a\s+)?(?:photo|picture|webcam\s+shot|camera\s+capture)|capture\s+(?:the\s+)?camera|webcam\s+photo|snap\s+(?:a\s+)?photo)$", text, flags=re.IGNORECASE):
            await self._cmd_camera(update, context)
            return

        # Check 6: Live Screenshot Snap (e.g. "take a screenshot", "screenshot screen")
        if re.search(r"^(?:take\s+(?:a\s+)?screenshot|capture\s+(?:the\s+)?screen)$", text, flags=re.IGNORECASE):
            await self._cmd_screenshot(update, context)
            return

        # Check 7: User asked to send/upload a generic file (e.g. "send me my CV", "send file Prompt.md", "send capstone paper")
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

            # If a Word document or automated script files were generated during this command, send them too!
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

                interpreter_skill = self.skill_router.get_skill("interpreter")
                if interpreter_skill and getattr(interpreter_skill, "last_generated_files", None):
                    for gen_path in interpreter_skill.last_generated_files:
                        if gen_path and Path(gen_path).exists():
                            with open(gen_path, "rb") as gf:
                                await update.message.reply_document(
                                    document=gf,
                                    filename=Path(gen_path).name,
                                    caption=f"📁 Automation Output: {Path(gen_path).name}"
                                )
                    interpreter_skill.last_generated_files = []

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

    def send_notification(self, text: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a proactive outbound push notification to the authorized user's Telegram chat.
        Can be called from any background service (RoutineEngine, ReminderService, etc.).
        """
        if not self._token or not self._allowed_user_id:
            return False

        if not self._app or not self._loop or not self._loop.is_running():
            # Fallback to direct HTTP request if loop isn't active
            try:
                import urllib.request
                import urllib.parse
                data = urllib.parse.urlencode({
                    "chat_id": self._allowed_user_id,
                    "text": text,
                    "parse_mode": parse_mode
                }).encode()
                req = urllib.request.Request(f"https://api.telegram.org/bot{self._token}/sendMessage", data=data)
                urllib.request.urlopen(req, timeout=5)
                return True
            except Exception as e:
                print(f"[TelegramBridge] Outbound HTTP notification error: {e}")
                return False

        async def _async_send():
            try:
                await self._app.bot.send_message(
                    chat_id=int(self._allowed_user_id),
                    text=text,
                    parse_mode=parse_mode
                )
            except Exception as ex:
                print(f"[TelegramBridge] Outbound send_message error: {ex}")

        try:
            asyncio.run_coroutine_threadsafe(_async_send(), self._loop)
            return True
        except Exception as e:
            print(f"[TelegramBridge] Failed to schedule outbound notification: {e}")
            return False

