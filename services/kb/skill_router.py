"""
MakiAI — Skill Router
Maps voice/text commands to the correct KB skill.

Uses keyword matching — same trigger words defined in the KB
skill manifests (.agent/skills/user/*.skill.json).

Returns a skill instance ready to execute, or None if no skill matched.
"""

import re
from typing import Optional


class SkillRouter:
    """
    Detects which KB skill to execute based on the user's input.

    Skills are registered with their trigger keywords.
    The router checks each trigger against the input and returns
    the first matching skill instance.

    Usage:
        router = SkillRouter(skills_dict)
        skill = router.detect("good morning")
        if skill:
            response = skill.execute(text)
    """

    def __init__(self, skills: dict):
        """
        Args:
            skills: Dict mapping skill_id → skill instance.
                    e.g. {"goodmorning": GoodMorningSkill(...), ...}
        """
        self._skills = skills

        # Trigger map: list of (pattern, skill_id) tuples
        # Checked in order — more specific patterns first
        self._triggers: list[tuple[re.Pattern, str]] = []
        self._build_trigger_map()

    # ─── Trigger Map ──────────────────────────────────────────────────────────

    def _build_trigger_map(self) -> None:
        """Build regex patterns from skill trigger keywords."""
        trigger_definitions = [
            # (skill_id, [keyword patterns])
            ("goodmorning", [
                r"\bgood\s*morning\b",
                r"\bmorning\s+briefing\b",
                r"\b(show|view|check|list|get|tell\s+me)\s+(me\s+)?(my\s+|our\s+)?(upcoming\s+|active\s+|current\s+|today'?s?\s+|tomorrow'?s?\s+)?schedules?\b",
                r"\bwhat\s+(is|are|was|'s)\s+(my|our|the)\s+(upcoming\s+|active\s+|current\s+|today'?s?\s+|tomorrow'?s?\s+)?schedules?\b",
                r"\b(what'?s?\s+(my\s+)?agenda|agenda\s+(for\s+today|today|for\s+the\s+day))\b",
                r"\b(ano|ano\s+ang|anong)\s+(mga\s+)?(schedule|sked|agenda|gagawin|plano)\b",
                r"\b(ano|anong)\s+schedule\s+ko\b",
                r"\bschedule\s+ko\s+(today|bukas|ngayon)\b",
            ]),
            ("goodnight", [
                r"\bgood\s*night\b",
                r"\bwrap\s+up\s+my\s+day\b",
                r"\bend\s+of\s+(the\s+)?day\b",
                r"\bday\s+wrap\s*up\b",
                r"\b(matutulog|tulog)\s+na\s+ako\b",
            ]),
            ("hello", [
                r"^(hey\s+maki[,.]?\s*)?(hello|hey|hi)\b",
                r"\bwhat\s+should\s+(i|we)\s+(do|be\s+doing)\b",
                r"\bwhat\s+time\s+is\s+it\b",
                r"\bwhat'?s?\s+(the\s+)?(time|current\s+time)\b",
                r"\b(current|philippine)\s+time\b",
                r"\bwhat'?s?\s+next\b",
                r"\bcheck.?in\b",
                r"\banong\s+oras\s+na\b",
            ]),
            ("memory", [
                r"\bremember\s+that\b",
                r"\bremember\s+(this|my|our)\b",
                r"\b(do\s+you\s+)?remember\b",
                r"\bdon'?t\s+forget\b",
                r"\bwhat\s+do\s+you\s+remember\b",
                r"\bwhat\s+did\s+i\s+(say|tell\s+you)\b",
                r"\b(do\s+you\s+)?recall\b",
                r"\b(what\s+is|what'?s|ano\s+ang)\s+my\s+(secondary\s+email|wifi|password|birthday|secret|address|phone|saved\s+note|remembered)\b",
                r"\b(forget|delete|remove|clear)\b",
                r"\btandaan\s+mo\b",
                r"\bnaaalala\s+mo\s+ba\b",
            ]),
            ("deadline", [
                r"\badd\s+(a\s+)?deadline\b",
                r"\bset\s+(a\s+)?deadline\b",
                r"\bnew\s+deadline\b",
                r"\bdeadline\s+(?:for|to|on|by|called|named|due)\b",
                r"\b(?:have|got|may)\s+(?:a\s+)?deadline\b",
                r"\b(show|list|view|what\s+are|check)\s+(my\s+)?deadlines?\b",
                r"\b(do\s+(?:i|we)\s+have\s+(?:any\s+)?deadlines?|any\s+deadlines?\s+(?:coming\s+up|soon)|upcoming\s+deadlines?)\b",
                r"\bdeadline\s+(done|complete|completed|finished)\b",
                r"\b(mark|complete)\s+deadline\b",
                r"^deadlines?$",
                r"\b(may\s+deadline\s+ba|anong\s+deadline|mga\s+deadline)\b",
                r"\bdeadline\s+(this\s+week|today|tomorrow|ngayong\s+linggo)\b",
            ]),
            ("reminder", [
                r"\bremind\s+(me\s+)?(at|to|about|in|that|of)?\b",
                r"\b(tell|notify|alert|warn|let)\s+(me\s+)?(later|in\s+\d+|at\s+\d+|when|to|about|that)\b",
                r"\b(add|set|put|create)\s+(a\s+|an\s+)?(reminder|schedule|meeting|interview|appointment)\b",
                r"\bschedule\s+(an?\s+)?(meeting|event|call|session|task|zoom|interview|appointment)\b",
                r"\badd\s+(this\s+)?to\s+(my\s+)?(schedule|calendar)\b",
                r"\b(show|list|view|provide|check|what\s+are|get|do\s+(i|we)\s+have)\s+(a\s+|the\s+|my\s+|our\s+|any\s+)?(list\s+of\s+|scheduled\s+|upcoming\s+|active\s+)?(reminders?|meetings?|interviews?|appointments?|calendar|events?|schedules?)\b",
                r"\b(check|see)\s+if\s+(i|we)\s+have\s+(any\s+)?(meetings?|reminders?|appointments?|interviews?)\b",
                r"\b(check|search|look\s+(in|at)|read)\s+.*?\breminders?\b",
                r"\breminders?\s+(in|from|on)\s+(the\s+)?(knowledge\s+base|kb)\b",
                r"\breminders?\s+list\b",
                r"\bcancel\s+(reminder|meeting|interview)\b",
                r"^reminders?$",
                r"\b(paalala|paalalahanan|ipaalala|paalala\s+mamaya)\b",
            ]),
            ("new_project", [
                r"\bnew\s+project\b",
                r"\bstart\s+project\b",
                r"\bstart\s+a\s+project\b",
                r"\bi\s+have\s+(a\s+)?project\s+idea\b",
                r"\bi\s+(want|wanna)\s+to\s+build\b",
                r"\bwe\s+have\s+a\s+new\s+project\b",
                r"\blet'?s\s+build\b",
                r"\bnew\s+(app|website|system|tool)\b",
                r"\b(may\s+bago\s+akong\s+project|may\s+project\s+idea\s+ako|naisip\s+na\s+project)\b",
            ]),
            ("homework", [
                r"\bcreate\s+(my\s+)?homework\b",
                r"\bdo\s+(my\s+)?homework\b",
                r"\bmake\s+(my\s+)?homework\b",
                r"\bwrite\s+(my\s+)?homework\b",
                r"\bhelp\s+(me\s+with\s+)?(my\s+)?homework\b",
                r"\bcreate\s+(my\s+)?assignment\b",
                r"\bdo\s+(my\s+)?assignment\b",
                r"\bmake\s+(my\s+)?assignment\b",
                r"\bwrite\s+(my\s+)?assignment\b",
                r"\bfinish\s+(my\s+)?homework\b",
                r"\bhomework\s+help\b",
                r"\b(gawa\s+tayo\s+ng\s+homework|tulungan\s+mo\s+ako\s+sa\s+homework|assignment|homework)\b",
            ]),
            ("clip", [
                r"\b(find\s+clips?|create\s+clips?|make\s+clips?|clip\s+this|clip\s+(?:the\s+)?video|extract\s+clips?|viral\s+shorts?)\b",
                r"\b(clip|slice)\s+(?:the\s+)?(?:best\s+moments|highlights|viral\s+moments|latest\s+recording|my\s+video)\b",
                r"\b(deep\s*clip|deepclip)\b",
            ]),
            ("interpreter", [
                r"\b(run|write|execute)\s+(a\s+)?(python|powershell|script|code)\b",
                r"\b(write|run|execute)\s+(a\s+)?script\s+to\b",
                r"\b(automate|batch\s+convert|batch\s+resize|calculate\s+data|organize\s+folder)\b",
                r"\b(parse\s+csv|calculate\s+this\s+in\s+python|merge\s+pdf|resize\s+images?)\b",
                r"\b(script|python\s+code|run\s+python)\b",
            ]),
            ("composio", [
                r"\b(google\s+(doc|docs|sheet|sheets|drive|slides)|gdoc|gsheet)\b",
                r"\b(google\s+calendar|gcal|my\s+calendar|calendar\s+events?|check\s+(my\s+)?calendar)\b",
                r"\b(check\s+(my\s+)?(gmail|emails?)|unread\s+emails?|send\s+(an?\s+)?email|draft\s+(an?\s+)?email|emails?\s+on\s+gmail|read\s+(my\s+)?(gmail|emails?)|fetch\s+(my\s+)?(gmail|emails?)|inbox\s+emails?)\b",
                r"\b(connect|integrate|sync|link)\s+(with\s+)?(notion|trello|github|gitlab|discord|spotify)\b",
                r"\b(notion|trello)\s+(page|board|task|card)\b",
                r"\b(composio|cloud\s+app|connect\s+app)\b",
            ]),
            ("research", [
                r"https?://[^\s]+",
                r"\b(search|look\s+up|google|research)\b",
                r"\bsearch\s+(the\s+web|online|google)\b",
                r"\bfind\s+(out\s+about|information\s+about)\b",
                r"\b(read|check|summarize)\s+(this\s+)?(link|url|website|page|article)\b",
                r"\bwhat\s+is\s+the\s+latest\s+on\b",
                r"\bwho\s+won\s+the\b",
                r"\b(mag\s*research|magsaliksik|hanapin\s+sa\s+internet)\b",
            ]),
        ]

        for skill_id, patterns in trigger_definitions:
            for pattern in patterns:
                compiled = re.compile(pattern, re.IGNORECASE)
                self._triggers.append((compiled, skill_id))

    # ─── Public API ──────────────────────────────────────────────────────────

    def detect(self, text: str) -> Optional[object]:
        """
        Check if the input matches any registered skill trigger.

        Args:
            text: The transcribed or typed user input.
                  Wake word "Hey Maki" prefix is stripped before matching.

        Returns:
            A skill instance if matched, None otherwise.
        """
        # Strip wake word prefix before matching
        cleaned = re.sub(
            r"^(hey\s+maki[,.]?\s*|maki[,.]?\s*)",
            "",
            text.strip(),
            flags=re.IGNORECASE,
        ).strip()

        for pattern, skill_id in self._triggers:
            if pattern.search(cleaned):
                # 1. If research triggered but command asks to play/watch, pass to ComputerRouter
                if skill_id == "research" and re.search(r"\b(?:and\s+)?play\b|\bwatch\b|\bstream\b", cleaned, re.IGNORECASE):
                    continue

                # 2. Collision Shield: "open google chrome", "launch chrome", "open browser" -> let ComputerRouter handle it
                if skill_id == "research" and re.search(r"^(?:open|launch|start|run)\s+(?:google\s+)?(?:chrome|browser)\b", cleaned, re.IGNORECASE):
                    continue

                # 3. Collision Shield: "open github", "launch notion", "open discord", "open spotify" -> let ComputerRouter handle it
                if skill_id == "composio" and re.search(r"^(?:open|launch|start|go\s+to)\s+(?:github|notion|discord|spotify|trello|gitlab)\b", cleaned, re.IGNORECASE):
                    continue

                skill = self._skills.get(skill_id)
                if skill:
                    print(f"[SkillRouter] Matched skill: {skill_id}")
                    return skill
                else:
                    print(f"[SkillRouter] Skill '{skill_id}' matched but not registered.")

        return None

        return None

    def register(self, skill_id: str, skill_instance: object) -> None:
        """
        Register a new skill instance.

        Args:
            skill_id:       Unique skill identifier.
            skill_instance: The skill object with an execute() method.
        """
        self._skills[skill_id] = skill_instance
        print(f"[SkillRouter] Registered skill: {skill_id}")

    def get_skill(self, skill_id: str) -> Optional[object]:
        """Return the skill instance for a given skill_id, or None."""
        return self._skills.get(skill_id)

    def list_skills(self) -> list[str]:
        """Return a list of all registered skill IDs."""
        return list(self._skills.keys())

