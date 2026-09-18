"""
MakiAI — Routine & Workspace Provisioning Skill
Executes on-demand workspace preparation and triggers the interactive Interview/Routine modal.

Triggered by:
  - "Prep for class" / "Prep for online class" / "Prep for Capstone"
  - "Prep for client work" / "Prep for work"
  - "Prep for interview" / "Schedule interview with..." / "Add interview schedule"
  - "Prep for coding" / "Prep for dev"
  - "Prep for job hunting"
  - "Set meeting link" / "Set class link"
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from skills.base_skill import BaseSkill


class RoutineSkill(BaseSkill):
    SKILL_ID = "routine"
    REQUIRED_FILES = []

    TRIGGERS = [
        r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(class|online\s+class|bat\s*600|icc\s*600|school)\b",
        r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(client\s+work|client|content|marketing|work)\b",
        r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(interview|zoom|google\s+meet|meeting)\b",
        r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(coding|programming|dev|development)\b",
        r"\b(prep|prepare|start|launch|open|setup|let'?s\s+do|let'?s)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(job\s+hunting|job\s+search|jobs?|hunt\s+a\s+job|hunt\s+jobs?)\b",
        r"\b(hunt|apply\s+for)\s+(a\s+)?(job|jobs|work)\b",
        r"\b(ai\s*video|smm|social\s+media)\s+(jobs?|job\s+hunting|hunt)\b",
        r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(gaming|stream|games|leisure)\b",
        r"\b(launch|start|open|run)\s+(the\s+)?(routine|workspace)\b",
        r"\b(set|schedule|add)\s+(an?\s+)?(interview|meeting\s+link|class\s+link)\b",
        r"\b(add|schedule)\s+(an?\s+)?interview\s+schedule\b",
        r"\b(open|trigger|show)\s+(the\s+)?(interview|routine)\s+(modal|form|card)\b",
    ]

    def __init__(self, gemini_service, context_builder, kb_reader, kb_writer, routine_engine=None, reminder_service=None):
        super().__init__(gemini_service, context_builder, kb_reader, kb_writer)
        self.routine_engine = routine_engine
        self.reminder_service = reminder_service
        self.ui_bridge = None

    def set_ui_bridge(self, ui_bridge) -> None:
        """Connect UI bridge for interactive modal triggers."""
        self.ui_bridge = ui_bridge

    def execute(self, text: str) -> str:
        lowered = text.lower().strip()

        # 1. Check if user wants to schedule an interview or open the modal
        schedule_intent = bool(re.search(
            r"\b(schedule|add|set|book|create|open|trigger|show)\s+.*?(interview|meeting\s+link|class\s+link|modal|routine\s+form)\b",
            lowered
        ))
        if schedule_intent or "interview schedule" in lowered or "schedule interview" in lowered:
            return self._handle_schedule_modal(text)

        # 2. Check for Specific Job Hunting Niches
        if re.search(r"\b(ai\s*video|video\s+creator|video\s+editor|video)\b", lowered) and any(k in lowered for k in ["job", "hunt", "prep", "apply", "work"]):
            return self._launch_preset("job_hunting_ai_video", "AI Video Creator Job Hunting")

        if re.search(r"\b(smm|social\s+media|social\s+media\s+manager)\b", lowered) and any(k in lowered for k in ["job", "hunt", "prep", "apply", "work"]):
            return self._launch_preset("job_hunting_smm", "Social Media Manager Job Hunting")

        # 3. General Job Hunting Trigger -> Ask user which niche
        if any(k in lowered for k in ["hunt a job", "hunt jobs", "job hunting", "job search", "apply for jobs", "hunt for jobs"]):
            return self._handle_job_niche_prompt(text)

        # 4. Check for On-Demand Workspace Prep Triggers
        if re.search(r"\b(class|bat|icc|school)\b", lowered):
            now_day = datetime.now().strftime("%A")
            if "bat" in lowered or ("icc" not in lowered and now_day in ["Monday", "Wednesday"]):
                return self._launch_preset("online_class_bat600", "BAT-600 Online Class")
            else:
                return self._launch_preset("online_class_icc600", "ICC-600 Online Class")

        if re.search(r"\b(client\s+work|content|marketing)\b", lowered) or ("prep" in lowered and "work" in lowered):
            return self._launch_preset("client_content_work", "Client Content & Marketing")

        if re.search(r"\b(interview|zoom)\b", lowered):
            return self._launch_preset("interview_essence", "Interview")

        if re.search(r"\b(coding|programming|dev|development)\b", lowered):
            return self._launch_preset("coding_session", "Coding & Development")

        if re.search(r"\b(gaming|stream|games|leisure)\b", lowered):
            return self._launch_preset("gaming_leisure", "Gaming & Leisure")

        if re.search(r"\b(job|hunting)\b", lowered):
            return self._handle_job_niche_prompt(text)

        # Fallback to general routine trigger or modal
        return self._handle_schedule_modal(text)

    def _handle_job_niche_prompt(self, text: str) -> str:
        """Prompt user conversationally and display interactive niche picker."""
        now = datetime.now()
        is_on_schedule = (10 <= now.hour < 12) or (17 <= now.hour < 18)

        if self.ui_bridge:
            self.ui_bridge.set_active_modal("job_niche", {
                "title": "Job Hunting Niche Selection",
                "options": [
                    {
                        "id": "job_hunting_ai_video",
                        "label": "AI Video Creator",
                        "desc": "Dual Profiles (OnlineJobs, LinkedIn, ChatGPT, Gemini, Portfolio, Resume)"
                    },
                    {
                        "id": "job_hunting_smm",
                        "label": "Social Media Manager",
                        "desc": "Dual Profiles (OnlineJobs, LinkedIn, Indeed, Canva Portfolio, Resume)"
                    }
                ]
            })

        if is_on_schedule:
            return "Sir, entering your Job Hunting block. Which niche would you like to focus on for today's hunt — AI Video Creator or Social Media Manager?"
        else:
            return "It's not currently your scheduled time for job hunting, sir. But since you'd like to apply now, which niche would you like to focus on — AI Video Creator or Social Media Manager?"

    def _launch_preset(self, routine_id: str, label: str) -> str:
        """Launch configured preset workspace."""
        if self.routine_engine:
            msg = self.routine_engine.launch_routine(routine_id)
            return msg
        return f"Routine engine unavailable to prepare your {label} workspace, sir."

    def _handle_schedule_modal(self, text: str) -> str:
        """Extract draft details and pop up the interactive Interview & Routine modal."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        # Quick heuristic extraction for platform & category
        platform = "Google Meet"
        if "zoom" in text.lower():
            platform = "Zoom"
        elif "teams" in text.lower():
            platform = "Teams"
        elif "custom" in text.lower():
            platform = "Custom"

        category = "Interview"
        if "class" in text.lower():
            category = "Online Class"
        elif "client" in text.lower() or "work" in text.lower():
            category = "Client Work"
        elif "coding" in text.lower() or "dev" in text.lower():
            category = "Coding"

        lead_time = 15 if category == "Online Class" else 30
        profile = "Profile 1" if category == "Client Work" else "Default"

        title = "Interview Session" if category == "Interview" else f"{category} Session"
        # If user specified a company or topic, e.g. "schedule interview with Essence"
        match_with = re.search(r"(?:interview\s+(?:with|at|for)|meeting\s+with)\s+([a-zA-Z0-9\s]+?)(?:\s+(?:on|at|tomorrow|this|\?|$))", text, re.IGNORECASE)
        if match_with:
            target_name = match_with.group(1).strip()
            title = f"Interview with {target_name.title()}"

        draft = {
            "title": title,
            "category": category,
            "date": date_str,
            "time": time_str,
            "platform": platform,
            "link": "",
            "lead_time": lead_time,
            "profile": profile,
        }

        if self.ui_bridge:
            self.ui_bridge.set_active_modal("interview", draft)
            return f"I have opened the {title} schedule card for you, sir. You can paste the link and adjust the workspace options on screen."

        return f"Interactive modal bridge not connected, sir."
