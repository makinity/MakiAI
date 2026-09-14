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

    def execute(self, text: str) -> str:
        """Route to add, list, or cancel subcommand."""
        lowered = text.lower()

        if any(kw in lowered for kw in ["show", "list", "what", "my reminders"]):
            return self._list()
        elif any(kw in lowered for kw in ["cancel", "delete", "remove"]):
            return self._cancel(text)
        else:
            return self._add(text)

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
        """
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        prompt = f"""
The user said: "{text}"
Today's date: {today}
Current time: {time_str}

Extract the reminder details and return ONLY a JSON object in this exact format:
{{
  "datetime": "YYYY-MM-DDTHH:MM:00",
  "text": "reminder message"
}}

If no date is mentioned, assume today. If no specific time, make a reasonable guess.
Return only the JSON — no explanation, no markdown.
""".strip()

        try:
            raw = self.gemini.send(prompt, "")
            # Strip markdown fences if present
            raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

            import json
            parsed = json.loads(raw)
            reminder_text = parsed.get("text", text)
            reminder_dt_str = parsed.get("datetime", "")
            reminder_dt = datetime.fromisoformat(reminder_dt_str)

            # Schedule through ReminderService or persist directly
            if self.reminder_service:
                self.reminder_service.add(
                    reminder_id=str(uuid.uuid4()),
                    text=reminder_text,
                    dt=reminder_dt,
                )
            else:
                self._save_reminder(reminder_text, reminder_dt_str)

            friendly_time = self._format_relative_datetime(reminder_dt)
            return f"Got it. I'll remind you to {reminder_text} at {friendly_time}."

        except Exception as e:
            print(f"[ReminderSkill] Parse error: {e}")
            return "I had trouble understanding that reminder. Could you say it again with a specific time? For example: remind me at 3pm to study."

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
