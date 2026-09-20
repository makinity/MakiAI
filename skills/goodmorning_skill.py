"""
MakiAI — Good Morning Skill
Generates the user's morning briefing from KB workflow files.

Triggered by: "good morning", "what's my schedule today", "morning briefing"
Reads: time-management.md, carryover.md, deadlines.md
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional
from skills.base_skill import BaseSkill


class GoodMorningSkill(BaseSkill):

    SKILL_ID = "goodmorning"
    REQUIRED_FILES = [
        "workflows/time-management.md",
        "workflows/carryover.md",
        "workflows/deadlines.md",
    ]

    def _get_day_schedule(self, target_day_name: str) -> str:
        """Extract the exact schedule rows for target_day_name from workflows/time-management.md."""
        if not self.kb_reader:
            return ""
        content = self.kb_reader.read("workflows/time-management.md")
        if not content:
            return ""

        lines = content.splitlines()
        table_lines = []
        in_table = False
        headers = []
        for line in lines:
            if "| Time |" in line or "|Time|" in line:
                in_table = True
                headers = [h.strip().lower() for h in line.split("|")[1:-1]]
                continue
            if in_table:
                if not line.strip().startswith("|"):
                    break
                if "---" in line:
                    continue
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) == len(headers):
                    table_lines.append(cols)

        if not table_lines:
            return ""

        target_col_idx = -1
        for idx, h in enumerate(headers):
            if target_day_name.lower() in h:
                target_col_idx = idx
                break

        if target_col_idx == -1:
            return ""

        user_name = os.getenv("USER_NAME", "User")
        schedule_rows = [f"### {user_name}'s Planned Schedule for {target_day_name}:"]
        for row in table_lines:
            time_slot = row[0]
            activity = row[target_col_idx]
            schedule_rows.append(f"- {time_slot}: {activity}")

        return "\n".join(schedule_rows)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui_bridge = None

    def set_ui_bridge(self, ui_bridge) -> None:
        """Connect UI bridge to trigger interactive morning mission modal."""
        self.ui_bridge = ui_bridge

    def _trigger_mission_modal_if_available(self, day_name: str, date_str: str, day_schedule: str) -> None:
        """Parse schedule and deadlines, then push Today's Mission modal to UI."""
        if not hasattr(self, "ui_bridge") or not self.ui_bridge:
            return

        timeline_items = []
        if day_schedule:
            for line in day_schedule.splitlines():
                if line.startswith("- "):
                    clean_line = line.lstrip("- *").strip()
                    parts = clean_line.split(":", 1)
                    if len(parts) == 2:
                        t_slot = parts[0].strip()
                        act = parts[1].strip()
                    else:
                        t_slot = "--:--"
                        act = clean_line

                    routine_id = ""
                    if "bat" in act.lower():
                        routine_id = "online_class_bat600"
                    elif "icc" in act.lower():
                        routine_id = "online_class_icc600"
                    elif "job" in act.lower() or "hunt" in act.lower():
                        routine_id = "job_hunting_ai_video"
                    elif "client" in act.lower() or "content" in act.lower():
                        routine_id = "client_content_work"

                    timeline_items.append({
                        "time": t_slot,
                        "title": act,
                        "desc": f"Planned block for {day_name}",
                        "routine_id": routine_id,
                    })

        deadlines_text = ""
        if self.kb_reader:
            d_content = self.kb_reader.read("workflows/deadlines.md")
            if d_content:
                urgent = [l for l in d_content.splitlines() if "- [ ]" in l][:3]
                if urgent:
                    deadlines_text = "\n".join(urgent)

        mission_data = {
            "date_label": f"{day_name}, {date_str}",
            "active_block": "Daily Operating Schedule",
            "timeline_items": timeline_items,
            "deadlines_text": deadlines_text or "No pending deadlines logged.",
        }
        self.ui_bridge.show_morning_mission(mission_data)

    def _find_current_and_next_blocks(self, day_schedule: str, current_time: datetime) -> tuple[Optional[str], Optional[str]]:
        """Find the exact active block and next upcoming block from day_schedule."""
        if not day_schedule:
            return None, None

        curr_mins = current_time.hour * 60 + current_time.minute
        parsed_slots = []

        for line in day_schedule.strip().splitlines():
            match = re.search(r"(\d{1,2}):(\d{2})\s*[-–—to]+\s*(\d{1,2}):(\d{2})\s*:\s*(.+)", line)
            if match:
                h1, m1, h2, m2, title = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4)), match.group(5).strip()
                start = h1 * 60 + m1
                end = h2 * 60 + m2
                start_label = datetime(2000, 1, 1, h1, m1).strftime("%I:%M %p").lstrip("0")
                end_label = datetime(2000, 1, 1, h2, m2).strftime("%I:%M %p").lstrip("0")
                time_label = f"{start_label} to {end_label}"
                parsed_slots.append((start, end, time_label, start_label, title))

        active_str = None
        next_str = None

        for idx, (start, end, time_label, start_label, title) in enumerate(parsed_slots):
            if start <= curr_mins < end:
                active_str = f"{title} ({time_label})"
                if idx + 1 < len(parsed_slots):
                    n_start_label = parsed_slots[idx + 1][3]
                    n_title = parsed_slots[idx + 1][4]
                    next_str = f"{n_title} at {n_start_label}"
                break
            elif curr_mins < start and not next_str:
                next_str = f"{title} at {start_label}"

        return active_str, next_str

    def execute(self, text: str) -> str:
        """Generate the time-aware schedule briefing with zero latency."""
        now = datetime.now()
        lowered = text.lower()
        is_tomorrow = any(k in lowered for k in ["tomorrow", "bukas"])

        if is_tomorrow:
            target_date = now + timedelta(days=1)
            day_name = target_date.strftime("%A")
            date_str = target_date.strftime("%B %d, %Y")
            day_schedule = self._get_day_schedule(day_name)
            self._trigger_mission_modal_if_available(day_name, date_str, day_schedule)

            # Instant briefing for tomorrow
            return (
                f"Here is your schedule overview for tomorrow, {day_name}, {date_str}, sir. "
                f"I have displayed your complete operating timeline and upcoming items on screen. "
                f"Let me know if you would like to make any adjustments."
            )
        else:
            day_name = now.strftime("%A")
            date_str = now.strftime("%B %d, %Y")
            time_str = now.strftime("%I:%M %p").lstrip("0")
            hour = now.hour
            day_schedule = self._get_day_schedule(day_name)
            self._trigger_mission_modal_if_available(day_name, date_str, day_schedule)

            if 5 <= hour < 12:
                greeting = "Good morning"
            elif 12 <= hour < 18:
                greeting = "Good afternoon"
            else:
                greeting = "Good evening"

            active_block, next_block = self._find_current_and_next_blocks(day_schedule, now)

            # Fast weather summary if cached or fast-responding
            weather_snippet = ""
            try:
                from skills.weather_skill import WeatherSkill
                w_skill = WeatherSkill()
                w_summary = w_skill.get_weather_summary()
                if w_summary and "location" in w_summary:
                    weather_snippet = f" It is {w_summary['temperature_c']} degrees in {w_summary['location']} with {w_summary['condition_phrase']}."
            except Exception:
                pass

            # Build natural, high-precision spoken response
            if active_block:
                spoken = f"{greeting}, sir. The time is {time_str}.{weather_snippet} According to your schedule for {day_name}, you are currently in your planned {active_block}."
                if next_block:
                    spoken += f" Up next is {next_block}."
                spoken += " I have opened your daily mission and timeline on screen."
            else:
                spoken = f"{greeting}, sir. The time is {time_str}.{weather_snippet} Here is your complete operating schedule and deadlines for {day_name} on screen. Is there anything you would like to prepare?"

            return spoken
