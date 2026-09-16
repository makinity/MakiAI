"""
MakiAI — Deadline Skill
Add, list, and complete deadlines in workflows/deadlines.md.

Triggered by: "add deadline", "show my deadlines", "list deadlines", "deadline done"
Reads: workflows/deadlines.md
Writes: workflows/deadlines.md
"""

import re
from skills.base_skill import BaseSkill


class DeadlineSkill(BaseSkill):

    SKILL_ID = "deadline"
    REQUIRED_FILES = ["workflows/deadlines.md"]

    def execute(self, text: str) -> str:
        """
        Route to the correct deadline subcommand based on input.

        Subcommands:
            add     — "add deadline [task] by [date]"
            list    — "show my deadlines" / "list deadlines"
            done    — "deadline done [task]"
        """
        lowered = text.lower()

        if any(kw in lowered for kw in ["add", "new", "create", "have a deadline", "set deadline", "urgent deadline"]):
            return self._add(text)
        elif any(kw in lowered for kw in ["done", "complete", "finish", "completed"]):
            return self._complete(text)
        else:
            return self._list()

    # ─── Subcommands ─────────────────────────────────────────────────────────

    def _add(self, text: str) -> str:
        """Add a new deadline entry to deadlines.md."""
        current = self.kb_reader.read("workflows/deadlines.md")

        if not current:
            current = "# Deadlines\n\n## Pending\n\n## Completed\n"

        prompt = f"""
The user said: "{text}"

Current deadlines.md content:
{current}

Extract the deadline task and due date from the user's request.
Add it as a new entry in the Pending section following the existing format.
Return the full updated deadlines.md content only — no explanation.
""".strip()

        updated = self._ask_gemini(prompt)
        self.kb_writer.write("workflows/deadlines.md", updated)
        self.kb_writer.update_last_updated("workflows/deadlines.md")
        if self.context_builder:
            self.context_builder.invalidate_cache()

        # Confirm with a short spoken response
        confirm_prompt = f'The user said "{text}". Confirm in one short sentence that the deadline was added.'
        return self._ask_gemini(confirm_prompt)

    def _list(self) -> str:
        """Read and summarize all current deadlines."""
        content = self.kb_reader.read("workflows/deadlines.md")

        if not content or content.strip() == "":
            return "You have no deadlines tracked yet. Say 'add deadline' to add one."

        from datetime import datetime
        today = datetime.now().strftime("%A, %B %d, %Y")

        prompt = f"""
Today is {today}.

Here are Mark's current deadlines from workflows/deadlines.md:
{content}

Summarize the pending deadlines clearly, warmly, and concisely for sir:
- Clearly state the task and due dates.
- Highlight urgency naturally (e.g., due today, tomorrow, or later this week).
- Speak in natural flowing conversational sentences suitable for TTS (no markdown asterisks, no bullets, no emojis, no numbered headers).
- Address sir directly. Keep it short (under 90 words).
- Only mention pending deadlines, not completed ones.
- If there are no pending deadlines, say "You have no pending deadlines right now, sir. Great work!"
""".strip()

        resp = self._ask_gemini(prompt)
        if not resp or "I had trouble thinking" in resp:
            # Extract first pending item if any
            lines = [l.strip() for l in content.splitlines() if l.strip().startswith("-") or l.strip().startswith("*")]
            if lines:
                first_items = ", ".join(lines[:3])
                return f"Here are your upcoming deadlines, sir: {first_items}."
            return "You currently have no pending deadlines recorded, sir."
        return resp


    def _complete(self, text: str) -> str:
        """Mark a deadline as completed."""
        current = self.kb_reader.read("workflows/deadlines.md")

        if not current:
            return "I couldn't find your deadlines file."

        prompt = f"""
The user said: "{text}"

Current deadlines.md:
{current}

The user wants to mark a deadline as completed.
Move the matching deadline from Pending to Completed section.
Return the full updated deadlines.md content only — no explanation.
""".strip()

        updated = self._ask_gemini(prompt)
        self.kb_writer.write("workflows/deadlines.md", updated)
        self.kb_writer.update_last_updated("workflows/deadlines.md")

        confirm_prompt = f'The user said "{text}". Confirm in one short sentence that the deadline was marked complete.'
        return self._ask_gemini(confirm_prompt)
