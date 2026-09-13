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

TEMP_GUIDE_DIR = Path(r"C:\MakiSync Storage\School\Temp-Guide")


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

        self._pending_file_choices: Dict[int, List[Path]] = {}

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
            "📋 **MakiAI Mobile Commands:**\n\n"
            "• `/browse` - Browse your PC folders (Capstone, MakiSync Storage, Documents)\n"
            "• `/file <name>` or `send me [file]` - Search & pick PC files interactively\n"
            "• `/screenshot` - Send live desktop capture\n"
            "• `/status` - Check PC status, time, and active state\n"
            "• `What is my schedule today?`\n"
            "• `Remind me at 8 PM to [task]`\n"
            "• `Add deadline: [task] due Friday`\n"
            "• Attach a photo/PDF rubric to generate Word homework!",
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

        # ── Case 1: Exactly 1 Match or direct CV match ────────────────────────
        if len(unique_matches) == 1 or (is_cv_query and len(unique_matches) <= 2):
            return await self._send_single_file(unique_matches[0], update)

        # ── Case 2: Multiple Matches -> Group by Folders & Render Interactive List ──
        top_candidates = unique_matches[:10]
        chat_id = update.effective_chat.id
        self._pending_file_choices[chat_id] = top_candidates

        # Group by parent folder
        folder_groups = defaultdict(list)
        for global_idx, p in enumerate(top_candidates, start=1):
            folder_groups[p.parent].append((global_idx, p))

        msg_lines = [
            f"🔍 *Found {len(unique_matches)} matching files for* \"{clean_q}\":\n"
        ]

        buttons = []
        for folder_path, items in folder_groups.items():
            msg_lines.append(f"📂 `{folder_path}`")
            for idx, p in items:
                mtime_str = _format_mtime(p.stat().st_mtime if p.exists() else 0)
                size_str = _format_size(p.stat().st_size if p.exists() else 0)
                msg_lines.append(f"  **[{idx}]** `{p.name}` ({size_str}) • _{mtime_str}_")
                buttons.append([InlineKeyboardButton(f"📄 {idx}. {p.name[:38]}", callback_data=f"pickfile:{idx-1}")])
            msg_lines.append("")

        msg_lines.append("👉 *Tap a button below* or reply with the number (e.g. `1` or `send 1`):")
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_picker")])

        full_msg = "\n".join(msg_lines)
        if len(full_msg) > 4000:
            full_msg = full_msg[:3950] + "\n..."

        await update.message.reply_text(
            full_msg,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
        return True

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle interactive inline buttons from Telegram."""
        if not self._is_authorized(update):
            return

        query = update.callback_query
        await query.answer()
        data = query.data or ""
        chat_id = update.effective_chat.id

        if data.startswith("pickfile:"):
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

        elif data.startswith("browse_dir:"):
            folder_str = data[len("browse_dir:"):]
            await self._render_folder_browser(folder_str, update)

        elif data == "cancel_picker":
            self._pending_file_choices.pop(chat_id, None)
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

        # Check 1: User replied with a number to pick from recent search (e.g. "1", "2", "send 1", "list 2", "pick 3")
        num_match = re.match(r"^(?:send\s+|list\s+|file\s+|pick\s+)?(\d{1,2})$", text, flags=re.IGNORECASE)
        if num_match:
            idx = int(num_match.group(1)) - 1
            pending = self._pending_file_choices.get(chat_id, [])
            if pending and 0 <= idx < len(pending):
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

        # Check 3: User asked to send/upload a file (e.g. "send me my CV", "send me the CV pdf", "send file Prompt.md", "send capstone paper")
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
