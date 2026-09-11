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

Generate a quick, natural spoken check-in for sir. Speak like a warm, helpful assistant — not a robot.
Keep it to 3 to 4 sentences maximum, spoken naturally.

Tell sir:
- What he should be doing right now based on his schedule
- What is coming up next
- Any urgent deadlines if there are any (skip if none)
- Any carry-over tasks if present (skip if clean)

Do not use bullet points, lists, or formatting. Just speak naturally as if talking to him.
Do not say "Certainly" or "Of course". Just respond directly and warmly.
""".strip()

        return self._ask_gemini(prompt)
