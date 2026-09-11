"""
MakiAI — Good Morning Skill
Generates Mark's morning briefing from KB workflow files.

Triggered by: "good morning", "what's my schedule today", "morning briefing"
Reads: time-management.md, carryover.md, deadlines.md
"""

from datetime import datetime
from skills.base_skill import BaseSkill


class GoodMorningSkill(BaseSkill):

    SKILL_ID = "goodmorning"
    REQUIRED_FILES = [
        "workflows/time-management.md",
        "workflows/carryover.md",
        "workflows/deadlines.md",
    ]

    def execute(self, text: str) -> str:
        """Generate the morning briefing from KB workflow files."""
        now = datetime.now()
        day = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")

        prompt = f"""
Today is {day}. The current time is {time_str}.

Generate Mark's morning briefing following this exact format:

1. 🌅 Good Morning, Mark! — today's date
2. 📋 Today's Priority Order — from time-management.md
3. ⏰ Right Now — detect the current time block from the weekly schedule:
   - 🟢 Now ({time_str}) — what Mark should be doing right now
   - ⏭️ Up next — the next block
   - 🔜 Later — the block after that
4. 🕐 Today's Full Schedule — all blocks for today with 👉 marking the current one
5. 📌 Carry-over from Yesterday — from carryover.md (✅ if clean)
6. 📅 Upcoming Deadlines — from deadlines.md (🔴 overdue, 🚨 today, 🟠 tomorrow, 🟡 within 3 days, ⚪ within 7 days)
7. 💡 Day Highlight — 1–2 sentence summary
8. ⚡ Daily Minimum — quick reminder

End with: "Do you have any additional tasks or activities to add for today?"

Keep the spoken version concise — this will be read aloud.
""".strip()

        return self._ask_gemini(prompt)
