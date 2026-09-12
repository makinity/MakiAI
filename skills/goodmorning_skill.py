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

Generate a warm, natural spoken morning briefing for sir. Speak like a trusted personal assistant, not a robot.
Do not use bullet points, markdown, emoji labels, or formatted lists.
Speak in natural flowing sentences as if you are talking to him directly.

Cover these topics naturally in your speech:
1. A warm good morning greeting with today's date
2. What sir should be doing right now and what is coming up next in his schedule
3. His full schedule for today, described naturally in a sentence or two
4. Any carry-over tasks from yesterday if there are any, or confirm everything is clean
5. Any upcoming deadlines or saved meetings/notes for today (from Saved Long-Term Memories) — mention them warmly, skip if none
6. A brief encouraging closing thought about his day

End by asking: "Is there anything you would like to add to your day, sir?"

Keep the total response under 120 words. Speak warmly and naturally.
""".strip()

        return self._ask_gemini(prompt)
