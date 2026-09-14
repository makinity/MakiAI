"""
MakiAI — Reminder Service
Schedules, persists, and fires reminders using APScheduler.

When a reminder fires:
  1. Shows a Windows desktop notification
  2. Maki speaks the reminder aloud via TTS

Reminders survive app restarts — stored in data/reminders.json.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger


REMINDERS_FILE = Path(__file__).resolve().parents[2] / "data" / "reminders.json"


class ReminderService:
    """
    Reminder scheduling and firing service.

    Usage:
        service = ReminderService(on_fire=lambda text: tts.speak(text))
        service.start()
        service.add("Study for exam", datetime(2026, 9, 11, 15, 0))
        service.list_pending()  → list of reminder dicts
        service.cancel(reminder_id)
        service.stop()
    """

    def __init__(self, on_fire: Callable[[str], None] | None = None):
        """
        Args:
            on_fire: Called with the reminder text when a reminder fires.
                     Should speak the text aloud via TTS.
        """
        self.on_fire = on_fire or (lambda text: print(f"[Reminder] {text}"))
        self._scheduler = BackgroundScheduler(timezone="Asia/Manila")
        self._started = False

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the scheduler and re-schedule all pending reminders from disk."""
        if self._started:
            return

        self._scheduler.start()
        self._started = True
        self._restore_pending()
        print("[ReminderService] Scheduler started.")

    def stop(self) -> None:
        """Shut down the scheduler gracefully."""
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    def add(self, text: str, dt: datetime, reminder_id: str | None = None) -> str:
        """
        Schedule a new reminder.

        Args:
            text:        The reminder message to speak aloud.
            dt:          When to fire the reminder.
            reminder_id: Optional existing ID (for restoring from disk).

        Returns:
            The reminder ID string.
        """
        if dt <= datetime.now():
            print(f"[ReminderService] Reminder time is in the past: {dt}")
            return ""

        rid = reminder_id or str(uuid.uuid4())

        # Schedule the job
        self._scheduler.add_job(
            func=self._fire,
            trigger=DateTrigger(run_date=dt),
            args=[rid, text],
            id=rid,
            replace_existing=True,
            misfire_grace_time=60,
        )

        # Persist to disk
        self._save_reminder(rid, text, dt)
        print(f"[ReminderService] Reminder set: '{text}' at {dt.strftime('%Y-%m-%d %H:%M')}")
        return rid

    def cancel(self, reminder_id: str) -> bool:
        """
        Cancel a pending reminder by ID.

        Args:
            reminder_id: The reminder ID to cancel.

        Returns:
            True if cancelled, False if not found.
        """
        try:
            self._scheduler.remove_job(reminder_id)
        except Exception:
            pass

        return self._update_status(reminder_id, "cancelled")

    def list_pending(self) -> list[dict]:
        """Return all pending reminders from disk."""
        reminders = self._load_all()
        return [r for r in reminders if r.get("status") == "pending"]

    def list_all(self) -> list[dict]:
        """Return all reminders from disk."""
        return self._load_all()

    # ─── Fire ────────────────────────────────────────────────────────────────

    def _fire(self, reminder_id: str, text: str) -> None:
        """
        Called by APScheduler when a reminder triggers.
        Speaks the reminder aloud and shows a desktop notification.
        """
        print(f"[ReminderService] Firing: '{text}'")

        # Mark as fired in storage
        self._update_status(reminder_id, "fired")

        # Desktop notification
        self._show_notification(text)

        # Speak aloud
        spoken = f"Reminder: {text}"
        try:
            self.on_fire(spoken)
        except Exception as e:
            print(f"[ReminderService] on_fire error: {e}")

    def _show_notification(self, text: str) -> None:
        """Show a Windows toast notification."""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                "MakiAI Reminder",
                text,
                duration=8,
                threaded=True,
            )
        except ImportError:
            # win10toast not installed — skip desktop notification, TTS handles it
            pass
        except Exception as e:
            print(f"[ReminderService] Notification error: {e}")

    # ─── Restore ─────────────────────────────────────────────────────────────

    def _restore_pending(self) -> None:
        """Re-schedule all pending reminders from disk on startup."""
        pending = self.list_pending()
        restored = 0

        for reminder in pending:
            try:
                dt = datetime.fromisoformat(reminder["datetime"])
                if dt > datetime.now():
                    self.add(
                        text=reminder["text"],
                        dt=dt,
                        reminder_id=reminder["id"],
                    )
                    restored += 1
                else:
                    # Past reminder — mark as missed
                    self._update_status(reminder["id"], "missed")
            except Exception as e:
                print(f"[ReminderService] Failed to restore reminder: {e}")

        if restored:
            print(f"[ReminderService] Restored {restored} pending reminder(s).")

    # ─── Storage ─────────────────────────────────────────────────────────────

    def _load_all(self) -> list[dict]:
        """Load all reminders from reminders.json."""
        try:
            if not REMINDERS_FILE.exists():
                return []
            return json.loads(REMINDERS_FILE.read_text(encoding="utf-8")).get("reminders", [])
        except Exception as e:
            print(f"[ReminderService] Load error: {e}")
            return []

    def _save_reminder(self, rid: str, text: str, dt: datetime) -> None:
        """Add or update a reminder entry in reminders.json."""
        reminders = self._load_all()
        for r in reminders:
            if r.get("id") == rid:
                r["text"] = text
                r["datetime"] = dt.isoformat()
                r["status"] = "pending"
                self._write(reminders)
                return

        reminders.append({
            "id": rid,
            "text": text,
            "datetime": dt.isoformat(),
            "repeat": None,
            "status": "pending",
        })
        self._write(reminders)

    def _update_status(self, reminder_id: str, status: str) -> bool:
        """Update the status of all instances of a reminder in reminders.json."""
        reminders = self._load_all()
        found = False
        for r in reminders:
            if r.get("id") == reminder_id:
                r["status"] = status
                found = True
        if found:
            self._write(reminders)
        return found

    def _write(self, reminders: list[dict]) -> None:
        """Write reminders list to reminders.json."""
        try:
            REMINDERS_FILE.write_text(
                json.dumps({"reminders": reminders}, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[ReminderService] Write error: {e}")
