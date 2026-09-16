"""
MakiAI — Reminder Skill
Set, list, and cancel reminders stored in data/reminders.json.
Reminders are fired by ReminderService (Phase 8).

Triggered by: "remind me at X to Y", "set a reminder", "show reminders", "cancel reminder"
Reads/Writes: data/reminders.json (via ReminderService)
"""

import re
import uuid
from datetime import datetime
from skills.base_skill import BaseSkill


class ReminderSkill(BaseSkill):

    SKILL_ID = "reminder"
    REQUIRED_FILES = []   # No KB files needed — uses local reminders.json

    def __init__(self, gemini_service, context_builder, kb_reader, kb_writer, reminder_service=None):
        super().__init__(gemini_service, context_builder, kb_reader, kb_writer)
        self.reminder_service = reminder_service  # Injected in Phase 8
        self.ui_bridge = None

    def set_ui_bridge(self, ui_bridge) -> None:
        """Connect UI bridge to trigger interactive reminder modal."""
        self.ui_bridge = ui_bridge

    def execute(self, text: str) -> str:
        """Route to add, query/list, or cancel subcommand."""
        lowered = text.lower().strip()

        # 1. Cancel / Delete
        if any(kw in lowered for kw in ["cancel", "delete", "remove", "clear", "erase"]):
            return self._cancel(text)

        # 2. Check if explicitly an ADD command
        add_patterns = [
            r"\bremind\s+me\b",
            r"\badd\s+(?:this\s+)?to\s+(?:my\s+)?(?:schedule|calendar)\b",
            r"\b(?:add|set|put|create|book)\s+(?:a\s+|an\s+|new\s+)?(?:reminder|meeting|interview|event|appointment|call|schedule)\b",
            r"\bschedule\s+(?:a\s+|an\s+|new\s+)?(?:meeting|event|call|session|task|zoom|interview|appointment)\b",
            r"\b(?:paalala|ipaalala|paalalahanan)\b",
        ]
        is_add = any(re.search(p, lowered) for p in add_patterns)

        # 3. Check if it's a question or inquiry (e.g. "Do I have a schedule on Oct 1?", "Show my meetings")
        is_question = (
            "?" in text
            or lowered.startswith(("do i have", "do we have", "is there", "are there", "what is", "what's", "what are", "show", "list", "check", "view", "tell me", "when is"))
            or bool(re.search(r"\b(do\s+(?:i|we)\s+have|what\s+(?:is|are|was)|any\s+scheduled|upcoming)\b", lowered))
        )

        if is_add and not is_question:
            return self._add(text)
        else:
            return self._query(text)

    def _query(self, text: str) -> str:
        """
        Query stored reminders, meetings, and calendar events.
        Uses Gemini with the current date/time and all active events to generate a natural conversational answer.
        """
        reminders = self._load_reminders()
        now = datetime.now()
        today_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")

        # Collect active/pending events
        events_list = []
        for r in reminders:
            status = r.get("status")
            dt_str = r.get("datetime")
            msg = r.get("text", "")
            if status in ("pending", "active", None) and dt_str:
                try:
                    dt = datetime.fromisoformat(dt_str)
                    events_list.append((dt, msg))
                except Exception:
                    pass

        events_list.sort(key=lambda x: x[0])

        if not events_list:
            events_text = "None. There are currently no upcoming meetings, events, or reminders scheduled."
        else:
            lines = []
            for dt, msg in events_list:
                date_formatted = dt.strftime("%A, %B %d, %Y at %I:%M %p")
                lines.append(f"- {date_formatted} (PHT): {msg}")
            events_text = "\n".join(lines)

        prompt = f"""
The user asked: "{text}"
Current Local Date: {today_str}
Current Local Time: {time_str} (Philippine Standard Time, UTC+8)

Here are the user's Active Scheduled Events, Meetings & Reminders:
{events_text}

Instructions:
1. Answer the user's question directly and conversationally as Maki (personal AI assistant, address sir).
2. If the user asks about a specific date (e.g. October 1st, tomorrow, next week), check if any event matches that date (including events taking place in another timezone like Hawaii Time that map to that date).
3. If there is a matching meeting or event, clearly state the event name, time, and any timezone details.
4. If no events are scheduled for that specific date or overall, clearly and politely inform the user.
5. Keep the response concise (2-3 sentences max), warm, natural, and suitable for being spoken aloud via TTS.
6. Do NOT return JSON, do NOT use markdown symbols (no asterisks, no bullets, no hashes). Output plain conversational text only.
""".strip()

        try:
            return self.gemini.send(prompt, "")
        except Exception as e:
            print(f"[ReminderSkill] Query error: {e}")
            if not events_list:
                return "You have no upcoming meetings or reminders scheduled, sir."
            return self._list()

    def _format_relative_datetime(self, dt: datetime) -> str:
        """Format datetime into natural conversational time ('8:29 PM today', '9:00 PM tomorrow')."""
        now = datetime.now()
        today = now.date()
        rem_date = dt.date()
        
        # Format time without leading zero (e.g. "8:29 PM" instead of "08:29 PM")
        time_str = dt.strftime("%I:%M %p").lstrip("0")
        
        from datetime import timedelta
        if rem_date == today:
            return f"{time_str} today"
        elif rem_date == today + timedelta(days=1):
            return f"{time_str} tomorrow"
        elif 0 < (rem_date - today).days < 7:
            return f"{time_str} this {dt.strftime('%A')}"
        else:
            return f"{time_str} on {dt.strftime('%A, %B %d')}"

    # ─── Subcommands ─────────────────────────────────────────────────────────

    def _add(self, text: str) -> str:
        """
        Parse the reminder time and text, then schedule it.
        Uses Gemini to extract datetime and reminder text from natural language.
        Converts any mentioned timezones into local Philippine Standard Time (UTC+8).
        """
        now = datetime.now()
        today = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")

        prompt = f"""
The user said: "{text}"
Today's local date: {today}
Current local time: {time_str} (Philippine Standard Time, UTC+8)

Extract the event/reminder details and return ONLY a JSON object in this exact format:
{{
  "datetime": "YYYY-MM-DDTHH:MM:00",
  "text": "reminder or scheduled event description"
}}

Rules:
1. If the user mentions another timezone (e.g. Hawaii Standard Time HST UTC-10, EST, PST), convert that time into the user's local Philippine Standard Time (UTC+8) datetime ISO string.
2. If no date is mentioned, assume today. If date is 'tomorrow', calculate based on Today's date.
3. If no specific time is mentioned, make a reasonable guess.
4. Return ONLY the JSON object — no explanation, no markdown.
""".strip()

        try:
            raw = self.gemini.send(prompt, "")
            raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

            import json
            parsed = json.loads(raw)
            reminder_text = parsed.get("text") or text
            reminder_dt_str = parsed.get("datetime")
            
            if not reminder_dt_str or not isinstance(reminder_dt_str, str):
                return "I couldn't detect a specific time for that schedule or reminder, sir. Could you please specify the date and time?"

            # Clean and parse ISO string
            reminder_dt_str = reminder_dt_str.strip()
            reminder_dt = datetime.fromisoformat(reminder_dt_str)
            friendly_time = self._format_relative_datetime(reminder_dt)

            # 1. If UI bridge is connected, open interactive modal for confirmation
            if hasattr(self, "ui_bridge") and self.ui_bridge:
                try:
                    category = "Meeting" if any(k in reminder_text.lower() for k in ["meeting", "call", "interview", "zoom", "session"]) else (
                        "Personal" if any(k in reminder_text.lower() for k in ["workout", "gym", "doctor", "medicine", "water", "sleep"]) else "Task"
                    )
                    draft = {
                        "id": f"rem_{int(datetime.now().timestamp())}",
                        "title": reminder_text,
                        "category": category,
                        "target_date": reminder_dt.strftime("%Y-%m-%d"),
                        "target_time": reminder_dt.strftime("%H:%M"),
                    }
                    self.ui_bridge.set_active_modal("reminder", draft)
                    return f"I've drafted that reminder for {reminder_text} at {friendly_time}, sir. Please confirm or adjust on your screen."
                except Exception as e:
                    print(f"[ReminderSkill] Modal warning: {e}")

            # 2. Fallback / Direct schedule
            if self.reminder_service:
                self.reminder_service.add(
                    reminder_id=str(uuid.uuid4()),
                    text=reminder_text,
                    dt=reminder_dt,
                )
            else:
                self._save_reminder(reminder_text, reminder_dt_str)

            return f"Got it, sir. I have added {reminder_text} for {friendly_time}."

        except Exception as e:
            print(f"[ReminderSkill] Parse error: {e}")
            return "I had trouble understanding the specific date and time, sir. Could you please say the time again, for example: remind me tomorrow at 3 PM?"

    def _list(self) -> str:
        """List all pending reminders with relative dates."""
        reminders = self._load_reminders()
        now = datetime.now()
        
        # Deduplicate and filter active pending reminders
        seen_keys = set()
        valid_pending = []
        needs_save = False

        for r in reminders:
            if r.get("status") == "pending":
                try:
                    dt = datetime.fromisoformat(r["datetime"])
                    if dt <= now:
                        # Already expired
                        r["status"] = "fired"
                        needs_save = True
                        continue
                    key = (r.get("text", "").strip().lower(), r.get("datetime"))
                    if key in seen_keys:
                        # Duplicate entry
                        r["status"] = "duplicate"
                        needs_save = True
                        continue
                    seen_keys.add(key)
                    valid_pending.append((dt, r))
                except Exception:
                    continue

        if needs_save:
            self._save_reminders(reminders)

        if not valid_pending:
            return "You have no pending reminders."

        # Sort chronologically
        valid_pending.sort(key=lambda x: x[0])

        lines = [f"You have {len(valid_pending)} reminder{'s' if len(valid_pending) > 1 else ''}:"]
        for dt, r in valid_pending[:5]:    # Speak at most 5
            friendly = self._format_relative_datetime(dt)
            lines.append(f"— {r['text']} at {friendly}")

        return " ".join(lines)

    def _cancel(self, text: str) -> str:
        """Cancel a reminder by matching text."""
        reminders = self._load_reminders()
        lowered = text.lower()

        cancelled = False
        for r in reminders:
            if r.get("status") == "pending" and r.get("text", "").lower() in lowered:
                r["status"] = "cancelled"
                cancelled = True
                break

        if cancelled:
            self._save_reminders(reminders)
            return "Reminder cancelled."
        return "I couldn't find a matching reminder to cancel."

    # ─── Storage Helpers ─────────────────────────────────────────────────────

    def _load_reminders(self) -> list[dict]:
        """Load reminders.json from data/."""
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "data" / "reminders.json"
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("reminders", [])
        except Exception:
            return []

    def _save_reminders(self, reminders: list[dict]) -> None:
        """Write reminders list back to reminders.json."""
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "data" / "reminders.json"
        try:
            path.write_text(
                json.dumps({"reminders": reminders}, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[ReminderSkill] Save error: {e}")

    def _save_reminder(self, text: str, dt_str: str) -> None:
        """Add a single new reminder to reminders.json."""
        reminders = self._load_reminders()
        reminders.append({
            "id": str(uuid.uuid4()),
            "text": text,
            "datetime": dt_str,
            "repeat": None,
            "status": "pending",
        })
        self._save_reminders(reminders)
