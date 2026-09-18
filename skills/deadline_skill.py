"""
MakiAI — Deadline Skill
Add, list, and complete deadlines in workflows/deadlines.md.

Triggered by: "add deadline", "show my deadlines", "list deadlines", "deadline done"
Reads: workflows/deadlines.md
Writes: workflows/deadlines.md
"""

import re
import time
from datetime import datetime, timedelta
from skills.base_skill import BaseSkill


class DeadlineSkill(BaseSkill):

    SKILL_ID = "deadline"
    REQUIRED_FILES = ["workflows/deadlines.md"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui_bridge = None

    def set_ui_bridge(self, ui_bridge) -> None:
        """Connect UI bridge to trigger interactive modals."""
        self.ui_bridge = ui_bridge

    def execute(self, text: str) -> str:
        """
        Route to the correct deadline subcommand based on input.

        Subcommands:
            add     — "add deadline [task] by [date]" / "deadline for [task] by [date]"
            list    — "show my deadlines" / "list deadlines"
            done    — "deadline done [task]"
        """
        lowered = text.lower().strip()

        # Complete / Done subcommands
        is_complete_intent = bool(re.search(
            r"\b(?:mark\s+|set\s+)?deadlines?\s+(?:as\s+)?(?:done|complete|completed|finished)\b|"
            r"\b(?:mark|set)\s+.*?\s+(?:as\s+)?(?:done|complete|completed|finished)\b|"
            r"\b(?:complete|completed|finish|finished)\s+(?:the\s+)?deadlines?\b",
            lowered
        ))
        if is_complete_intent:
            return self._complete(text)

        # List / Query subcommands (explicit asking about existing deadlines)
        is_list_intent = any(kw in lowered for kw in [
            "what are", "what is", "show", "list", "view", "check my", "do i have", "do we have",
            "any deadline", "mga deadline", "upcoming deadline", "how many deadline"
        ]) or bool(re.match(r"^(?:my\s+)?deadlines?[.?]?$", lowered))

        if is_list_intent:
            return self._list()

        # Default to Add / Create for all task statements
        return self._add(text)

    # ─── Subcommands ─────────────────────────────────────────────────────────

    def _parse_deadline_draft(self, text: str) -> dict:
        """Extract structured metadata from natural language deadline requests."""
        lowered = text.lower()

        # 1. Category Detection
        category = "School"
        if any(k in lowered for k in ["client", "work", "job", "essence", "invoice", "marketing", "deliverable", "customer", "business", "meeting"]):
            category = "Work"
        elif any(k in lowered for k in ["makiai", "munchbite", "taskmaster", "feature", "git", "portfolio", "side project", "app", "code", "dev"]):
            category = "Projects"
        elif any(k in lowered for k in ["gym", "workout", "doctor", "buy", "groceries", "personal", "bill", "rent", "errand", "habit"]):
            category = "Personal"
        elif any(k in lowered for k in ["capstone", "homework", "assignment", "exam", "quiz", "lab", "thesis", "school", "class", "chapter", "paper", "essay", "subject", "prof"]):
            category = "School"

        # 2. Date Detection
        now = datetime.now()
        due_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")

        if "today" in lowered:
            due_date = now.strftime("%Y-%m-%d")
        elif "tomorrow" in lowered:
            due_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            days_map = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6
            }
            for day_name, day_idx in days_map.items():
                if day_name in lowered:
                    curr_day = now.weekday()
                    diff = (day_idx - curr_day) % 7
                    if diff == 0:
                        diff = 7
                    due_date = (now + timedelta(days=diff)).strftime("%Y-%m-%d")
                    break

        # Explicit YYYY-MM-DD date match if provided
        date_explicit = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if date_explicit:
            due_date = date_explicit.group(1)

        # 3. Time Detection (supports 11:59pm, 11.59pm, 5pm, 17:00, etc.)
        due_time = "23:59"
        m1 = re.search(r"\b(\d{1,2})[:.](\d{2})\s*(am|pm)?\b", lowered)
        if m1:
            hr = int(m1.group(1))
            mn = int(m1.group(2))
            ampm = m1.group(3)
            if ampm == "pm" and hr < 12:
                hr += 12
            elif ampm == "am" and hr == 12:
                hr = 0
            due_time = f"{hr:02d}:{mn:02d}"
        else:
            m2 = re.search(r"\b(\d{1,2})\s*(am|pm)\b", lowered)
            if m2:
                hr = int(m2.group(1))
                ampm = m2.group(2)
                if ampm == "pm" and hr < 12:
                    hr += 12
                elif ampm == "am" and hr == 12:
                    hr = 0
                due_time = f"{hr:02d}:00"

        # 4. Title Extraction
        title = text.strip()
        title = re.sub(
            r"^(?:hey maki,?|maki,?|can you|please|just)?\s*(?:add|set|create|put)?\s*(?:an?\s+)?(?:new\s+|urgent\s+)?deadlines?\s*(?:for\s+|to\s+|called\s+|named\s+|on\s+|about\s+|:\s*)?",
            "", title, flags=re.IGNORECASE
        ).strip()
        title = re.sub(
            r"\s+(?:by|on|due|at|before)\s+(?:this\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|today|tomorrow|\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm)?|\d{4}-\d{2}-\d{2}).*$",
            "", title, flags=re.IGNORECASE
        ).strip()
        title = title.strip(" .,!?")
        if not title:
            title = "New Task Submission"

        priority = "Urgent" if any(k in lowered for k in ["urgent", "important", "asap", "high priority", "critical"]) else "Normal"

        return {
            "id": f"dl_{int(time.time())}",
            "title": title,
            "category": category,
            "due_date": due_date,
            "due_time": due_time,
            "priority": priority,
        }

    def _add(self, text: str) -> str:
        """Draft a new deadline entry and trigger interactive UI modal."""
        draft = self._parse_deadline_draft(text)

        # 1. If UI bridge is connected, open interactive modal for user review & confirmation
        if hasattr(self, "ui_bridge") and self.ui_bridge:
            try:
                self.ui_bridge.set_active_modal("deadline", draft)
                return f"I've drafted that deadline for {draft['title']} under {draft['category']} due on {draft['due_date']}, sir. Please confirm or adjust the details on your screen."
            except Exception as e:
                print(f"[DeadlineSkill] Modal trigger warning: {e}")

        # 2. Fallback for headless / background execution: write directly
        current = self.kb_reader.read("workflows/deadlines.md")
        if not current:
            current = "# ⏳ Deadlines\n\n## 🎓 School Deadlines\n\n## 💼 Work / Client Deadlines\n\n## 🚀 Projects Deadlines\n\n## 👤 Personal Deadlines\n\n## ✅ Completed\n"

        entry = f"- [ ] **{draft['title']}** — Due: {draft['due_date']} {draft['due_time']} ({draft['priority']})"
        cat_header = f"## 🎓 School Deadlines" if draft["category"] == "School" else (
            "## 💼 Work / Client Deadlines" if draft["category"] == "Work" else (
                "## 🚀 Projects Deadlines" if draft["category"] == "Projects" else "## 👤 Personal Deadlines"
            )
        )

        if cat_header in current:
            updated = current.replace(cat_header, f"{cat_header}\n{entry}")
        elif "## Pending" in current:
            updated = current.replace("## Pending", f"## Pending\n{entry}")
        else:
            updated = f"{current.rstrip()}\n\n{cat_header}\n{entry}\n"

        self.kb_writer.write("workflows/deadlines.md", updated)
        self.kb_writer.update_last_updated("workflows/deadlines.md")
        if self.context_builder:
            self.context_builder.invalidate_cache()

        return f"I've added {draft['title']} under your {draft['category']} deadlines for {draft['due_date']}, sir."

    def _list(self) -> str:
        """Read and summarize all current deadlines."""
        content = self.kb_reader.read("workflows/deadlines.md")

        if not content or content.strip() == "":
            return "You have no pending deadlines right now, sir. Would you like to add one?"

        # Extract pending items directly
        pending_items = [
            l.strip() for l in content.splitlines() 
            if l.strip().startswith(("- [ ]", "* [ ]", "- [x]", "* [x]")) and not l.strip().startswith(("- [x]", "* [x]"))
        ]

        if not pending_items:
            return "You currently have no pending deadlines recorded, sir. Let me know if you would like me to add one for you."

        from datetime import datetime
        today = datetime.now().strftime("%A, %B %d, %Y")

        user_name = os.getenv("USER_NAME", "Mark")
        prompt = f"""
Today is {today}.

Here are {user_name}'s current deadlines from workflows/deadlines.md:
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
        if not resp or "I had trouble thinking" in resp or "don't have access" in resp.lower():
            first_items = ", ".join(pending_items[:3])
            return f"Here are your upcoming deadlines, sir: {first_items}."
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
