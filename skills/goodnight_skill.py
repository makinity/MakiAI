"""
MakiAI — Good Night Skill
Generates the night wrap-up and asks about missed tasks.
After Mark responds, updates carryover.md.

Triggered by: "good night", "wrap up my day", "end of day"
Reads: time-management.md, carryover.md
Writes: carryover.md (after Mark answers)
"""

from datetime import datetime, timedelta
from skills.base_skill import BaseSkill


class GoodNightSkill(BaseSkill):

    SKILL_ID = "goodnight"
    REQUIRED_FILES = [
        "workflows/time-management.md",
        "workflows/carryover.md",
    ]

    def execute(self, text: str) -> str:
        """Generate the night wrap-up briefing."""
        now = datetime.now()
        today = now.strftime("%A, %B %d, %Y")
        tomorrow = (now + timedelta(days=1)).strftime("%A")

        prompt = f"""
Today is {today}. Tomorrow is {tomorrow}.

Generate Mark's night wrap-up following this exact format:

1. 🌙 Good Night, Mark! — today's date
2. 🔭 Tomorrow: {tomorrow} — tomorrow's full schedule from the weekly table in time-management.md
3. 🎒 What to Prepare Tonight — specific prep items based on tomorrow's schedule
4. 📋 Tomorrow's Priority Order — from time-management.md

End with: "What tasks or activities did you miss or leave unfinished today?"

Keep the spoken version concise — this will be read aloud.
""".strip()

        return self._ask_gemini(prompt)

    def update_carryover(self, missed_tasks: str) -> str:
        """
        Update carryover.md with tasks Mark missed today.
        Called after Mark answers the follow-up question.

        Args:
            missed_tasks: Mark's answer about what he didn't finish.

        Returns:
            Confirmation response string.
        """
        if not missed_tasks.strip() or missed_tasks.lower() in ["nothing", "none", "nope", "no"]:
            # Clear carryover
            content = self.kb_reader.read("workflows/carryover.md")
            cleared = self._ask_gemini(
                f"The current carryover.md is:\n\n{content}\n\n"
                "Mark said he finished everything today. "
                "Rewrite carryover.md to show it's clean — no pending tasks. "
                "Keep the file structure but mark everything as done or cleared."
            )
            self.kb_writer.write("workflows/carryover.md", cleared)
            return "Great work today! Carryover cleared. Sleep well, Mark."

        # Add missed tasks to carryover
        current = self.kb_reader.read("workflows/carryover.md")
        updated = self._ask_gemini(
            f"The current carryover.md is:\n\n{current}\n\n"
            f"Mark missed or didn't finish these tasks today: {missed_tasks}\n\n"
            "Update carryover.md to include these as pending carry-over tasks for tomorrow. "
            "Keep the existing file structure. Return the full updated file content."
        )
        self.kb_writer.write("workflows/carryover.md", updated)
        self.kb_writer.update_last_updated("workflows/carryover.md")
        return "Got it. I've added those to tomorrow's carry-over. Rest well, Mark."
