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
        "workflows/carryover.md",
        "workflows/deadlines.md",
    ]

    def execute(self, text: str) -> str:
        """Generate a quick time-aware check-in response."""
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        day = now.strftime("%A")

        prompt = f"""
It is currently {time_str} on {day}.

Generate a quick check-in for Mark. Keep it very short — 3 to 5 sentences max.
This will be spoken aloud, so be concise.

Include only:
- 🟢 What Mark should be doing RIGHT NOW based on his schedule
- ⏭️ What's coming up next
- 🔴 Any overdue or urgent deadlines (if any — skip if none)
- One carry-over item if present (skip if clean)

Do NOT give the full schedule. Keep it quick and actionable.
""".strip()

        return self._ask_gemini(prompt)
