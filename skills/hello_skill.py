"""
MakiAI — Hello Skill
Quick time-aware check-in: current block, next block, urgent flags only.

Triggered by: "hello", "hey", "what should i do now", "what's next"
Reads: time-management.md, carryover.md, deadlines.md
"""

from datetime import datetime
from skills.base_skill import BaseSkill


class HelloSkill(BaseSkill):

    SKILL_ID = "hello"
    REQUIRED_FILES = [
        "workflows/time-management.md",
        "workflows/daily.md",
        "workflows/carryover.md",
        "workflows/deadlines.md",
    ]

    def execute(self, text: str) -> str:
        """Generate a quick time-aware check-in and schedule response."""
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        day = now.strftime("%A")
        date_str = now.strftime("%B %d, %Y")

        prompt = f"""
The current live time is {time_str} ({day}, {date_str}) Philippine Standard Time (UTC+8).
The user said: "{text}"

Generate a natural, helpful spoken response for sir:
- Clearly state the exact current time ({time_str} PHT)
- Check workflows/time-management.md and workflows/daily.md to state what block or activity sir should be doing right now on this day ({day}) at {time_str}
- Mention what is coming up next on his schedule
- Mention any urgent deadlines if present

Keep it concise (3-4 sentences max), warm, and spoken aloud by a personal assistant.
Do not use bullet points or robotic lists. Do not say 'Certainly' or 'I don't have live-clock access'. You have direct access to the live clock.
""".strip()

        return self._ask_gemini(prompt)
