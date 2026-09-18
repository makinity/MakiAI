"""
MakiAI — Good Morning Skill
Generates the user's morning briefing from KB workflow files.

Triggered by: "good morning", "what's my schedule today", "morning briefing"
Reads: time-management.md, carryover.md, deadlines.md
"""

import os
from datetime import datetime, timedelta
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
                    # Robust regex match for time formats like "9:00-10:00", "09:00 - 10:00 AM", "12:00 PM"
                    match = re.match(r"^-\s*(\d{1,2}:\d{2}(?:\s*[-–]\s*\d{1,2}:\d{2})?(?:\s*[AaPp][Mm])?|\d{1,2}\s*[AaPp][Mm]):?\s*(.*)$", line)
                    if match:
                        t_slot = match.group(1).strip()
                        act = match.group(2).strip()
                    else:
                        parts = line[2:].split(":", 1)
                        t_slot = parts[0].strip() if len(parts) > 1 else "--:--"
                        act = parts[1].strip() if len(parts) > 1 else line[2:].strip()

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

    def execute(self, text: str) -> str:
        """Generate the time-aware schedule briefing from KB workflow files."""
        now = datetime.now()
        lowered = text.lower()
        is_tomorrow = any(k in lowered for k in ["tomorrow", "bukas"])

        if is_tomorrow:
            target_date = now + timedelta(days=1)
            day_name = target_date.strftime("%A")
            date_str = target_date.strftime("%B %d, %Y")
            day_schedule = self._get_day_schedule(day_name)
            self._trigger_mission_modal_if_available(day_name, date_str, day_schedule)

            prompt = f"""
The current real-time clock is {now.strftime("%I:%M %p")} on {now.strftime("%A, %B %d, %Y")}.
The user asked for TOMORROW'S schedule: "{text}"
Target Date for tomorrow: {day_name}, {date_str}.

{day_schedule}

Generate a warm, clear spoken schedule briefing for tomorrow for sir:
1. Greet sir and state that this is the schedule overview for tomorrow ({day_name}, {date_str}).
2. Summarize the key routine blocks planned for {day_name} (e.g. morning routine, classes/work, coding/study, exercise, evening leisure).
3. Check for any upcoming deadlines or active calendar appointments on {day_name} from the Knowledge Base or mention if the day looks open.
4. End warmly: "Let me know if you would like to prepare anything for tomorrow, sir."

Constraints:
- Focus on tomorrow ({day_name}, {date_str}). Do NOT confuse it with today's live time block.
- Speak in natural flowing conversational sentences suitable for TTS (no markdown asterisks, no bullets, no headers).
- Keep total response concise (under 120 words).
""".strip()
        else:
            day_name = now.strftime("%A")
            date_str = now.strftime("%B %d, %Y")
            time_str = now.strftime("%I:%M %p")
            hour = now.hour
            day_schedule = self._get_day_schedule(day_name)
            self._trigger_mission_modal_if_available(day_name, date_str, day_schedule)

            if 5 <= hour < 12:
                greeting = "Good morning"
            elif 12 <= hour < 18:
                greeting = "Good afternoon"
            else:
                greeting = "Good evening"

            prompt = f"""
The current real-time clock is {time_str} ({day_name}, {date_str}) Philippine Standard Time (UTC+8).
The appropriate time-of-day greeting is "{greeting}".
The user asked: "{text}"

{day_schedule}

Generate a warm, natural spoken briefing for sir:
1. Start with the greeting ("{greeting}, sir.") and state the current time ({time_str} PHT).
2. Using the schedule table above for {day_name}, accurately state his EXACT active activity block right now at {time_str} (e.g., if it is between 10:00 PM and 11:00 PM, state that it is his gaming/free time block).
3. Mention what is coming up next (e.g., wind down at 11:00 PM, sleep at midnight).
4. End warmly: "Is there anything you would like to add to your day, sir?"

Constraints:
- Always respect the current live clock ({time_str}).
- Speak in natural flowing conversational sentences suitable for TTS (no markdown asterisks, no bullets, no headers).
- Keep total response concise (under 120 words).
""".strip()

        resp = self._ask_gemini(prompt)
        if not resp or "I had trouble thinking" in resp:
            if is_tomorrow:
                return f"Here is your schedule overview for tomorrow, {day_name}, {date_str}, sir. You have your standard routine and planned activities scheduled. Let me know if you would like to prepare anything for tomorrow, sir."
            return f"{greeting}, sir. The current time is {time_str}. According to your schedule, you are currently in your scheduled focus block for {day_name}. Is there anything you would like to add to your day, sir?"
        return resp
