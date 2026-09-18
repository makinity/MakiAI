"""
MakiAI — Good Night Skill
Generates the night wrap-up and asks about missed tasks.
After the user responds, updates carryover.md.

Triggered by: "good night", "wrap up my day", "end of day"
Reads: time-management.md, carryover.md
Writes: carryover.md (after user answers)
"""

import os
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
The user said: "{text}"

Generate a warm, natural spoken night wrap-up briefing for sir:
1. Greet sir warmly for the night ("Good night, sir.").
2. Briefly summarize tomorrow's key routine ({tomorrow}) from workflows/time-management.md.
3. Mention any key prep items or priority focus for tomorrow.
4. End warmly with: "What tasks or activities did you miss or leave unfinished today, sir?"

Constraints:
- Speak in natural flowing conversational sentences suitable for TTS (no markdown asterisks, no bullets, no emojis, no numbered headers).
- Address the user as 'sir'.
- Keep total response concise (under 100 words).
""".strip()

        resp = self._ask_gemini(prompt)
        if not resp or "I had trouble thinking" in resp:
            return f"Good night, sir. Tomorrow is {tomorrow}, and I have your schedule ready for when you wake up. What tasks or activities did you miss or leave unfinished today, sir?"
        return resp

    def update_carryover(self, missed_tasks: str) -> str:
        """
        Update carryover.md with tasks missed today.
        Called after user answers the follow-up question.

        Args:
            missed_tasks: User's answer about what wasn't finished.

        Returns:
            Confirmation response string.
        """
        user_name = os.getenv("USER_NAME", "User")
        if not missed_tasks.strip() or missed_tasks.lower() in ["nothing", "none", "nope", "no"]:
            # Clear carryover
            content = self.kb_reader.read("workflows/carryover.md")
            cleared = self._ask_gemini(
                f"The current carryover.md is:\n\n{content}\n\n"
                f"{user_name} said they finished everything today. "
                "Rewrite carryover.md to show it's clean — no pending tasks. "
                "Keep the file structure but mark everything as done or cleared."
            )
            self.kb_writer.write("workflows/carryover.md", cleared)
            return "Great work today! Carryover cleared. Sleep well, sir."

        # Add missed tasks to carryover
        current = self.kb_reader.read("workflows/carryover.md")
        updated = self._ask_gemini(
            f"The current carryover.md is:\n\n{current}\n\n"
            f"{user_name} missed or didn't finish these tasks today: {missed_tasks}\n\n"
            "Update carryover.md to include these as pending carry-over tasks for tomorrow. "
            "Keep the existing file structure. Return the full updated file content."
        )
        self.kb_writer.write("workflows/carryover.md", updated)
        self.kb_writer.update_last_updated("workflows/carryover.md")
        return "Got it. I've added those to tomorrow's carry-over, sir. Rest well."

