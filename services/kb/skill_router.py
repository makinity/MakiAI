"""
MakiAI — Skill Router
Maps voice/text commands to the correct KB skill.

Uses keyword matching — same trigger words defined in the KB
skill manifests (.agent/skills/user/*.skill.json).

Returns a skill instance ready to execute, or None if no skill matched.
"""

import re
from typing import Optional, Union, Dict, Any, List

from skills.base_skill import BaseSkill


class SkillRouter:
    """
    Detects which KB skill to execute based on the user's input.

    Skills can be provided as a dictionary or managed dynamically
    by a SkillRegistry.
    """

    def __init__(self, skills: Union[dict, Any]):
        """
        Args:
            skills: Dict mapping skill_id → skill instance or SkillRegistry instance.
        """
        self._registry = skills if hasattr(skills, "get_all_skills") else None
        self._skills: Dict[str, Any] = skills.get_all_skills() if self._registry else (skills or {})

        # Trigger map: list of (pattern, skill_id) tuples
        self._triggers: list[tuple[re.Pattern, str]] = []
        self._build_trigger_map()

    @property
    def skill_registry(self):
        """Return attached SkillRegistry instance if any."""
        return self._registry

    def reload(self) -> None:
        """Hot-reload skills and rebuild trigger maps."""
        if self._registry and hasattr(self._registry, "reload_skills"):
            self._skills = self._registry.reload_skills()
        self._build_trigger_map()
        print(f"[SkillRouter] Rebuilt trigger map with {len(self._triggers)} patterns across {len(self._skills)} skills.")

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
                r"\b(what\s+is|what'?s|ano\s+ang)\s+my\s+(secondary\s+email|wifi|password|birthday|secret|address|phone|saved\s+note|remembered|favorite\s+\w+)\b",
                r"\b(forget\s+(?:that|this|my|all|about)|forget\b|delete\s+(?:my\s+)?(?:memory|note|preference|fact)|clear\s+(?:all\s+)?(?:memories|facts|memory))\b",
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
            ("research", [
                r"https?://[^\s]+",
                r"\bsearch\s+(the\s+web|online|google|duckduckgo|internet)\b",
                r"\b(search|look\s+up|google|research)\b",
                r"\bfind\s+(out\s+about|information\s+about)\b",
                r"\b(read|check|summarize)\s+(this\s+)?(link|url|website|page|article)\b",
                r"\bwhat\s+is\s+the\s+latest\s+on\b",
                r"\bwho\s+won\s+the\b",
                r"\b(mag\s*research|magsaliksik|hanapin\s+sa\s+internet)\b",
            ]),
            ("composio", [
                r"\b(google\s+(doc|docs|sheet|sheets|drive|slides)|gdoc|gsheet)\b",
                r"\b(google\s+calendar|gcal|my\s+calendar|calendar\s+events?|check\s+(my\s+)?calendar)\b",
                r"\b(check|see|read|get|fetch|list|view|open|search|find)\s+.*?\b(emails?|gmail|messages?|inbox|conversations?|fb\s+posts?|social\s+posts?|mail)\b",
                r"\b(recent|latest|unread|new|incoming|check)\s+(emails?|gmail|messages?|mail|inbox)\b",
                r"\b(send|draft|compose|write)\s+.*?\b(email|emails|mail|message)\b",
                r"\b(facebook|fb|messenger|makisync)\b",
                r"\b(post|create\s+(a\s+)?post|publish)\s+(on|to|in)\s+(my\s+)?(facebook|fb|messenger|makisync|page)\b",
                r"^(?:i\s+want\s+you\s+to\s+|please\s+)?(?:read|open|show|tell\s+me(?:\s+about)?)\s+(?:it|the\s+email|the\s+message|the\s+body|the\s+details|that|them|more)[.!]?$",
                r"^(?:read|open|show)\s+(?:it|them|the\s+email|the\s+message)[.!]?$",
                r"\b(?:draft|write|compose|send|just)?\s*(?:a\s+)?(?:reply|response|replying|respond)\b",
                r"\b(?:reply\s+with|reply\s+saying|reply\s+a|just\s+reply|say\s+hello|send\s+it\s+directly)\b",
                r"\b(connect|integrate|sync|link)\s+(with\s+)?(notion|trello|github|gitlab|discord|spotify|facebook)\b",
                r"\b(notion|trello)\s+(page|board|task|card)\b",
                r"\b(composio|cloud\s+app|connect\s+app)\b",
            ]),
            ("routine", [
                r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(class|online\s+class|bat\s*600|icc\s*600|school)\b",
                r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(client\s+work|client|content|marketing|work)\b",
                r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(interview|zoom|google\s+meet|meeting)\b",
                r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(coding|programming|dev|development)\b",
                r"\b(prep|prepare|start|launch|open|setup|let'?s\s+do|let'?s)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(job\s+hunting|job\s+search|jobs?|hunt\s+a\s+job|hunt\s+jobs?)\b",
                r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(?:an?\s+)?(ai\s*video|video\s+creator|smm|social\s+media)\s*(?:jobs?|job\s+hunting|hunt|work)?\b",
                r"\b(hunt|apply\s+for)\s+(a\s+)?(job|jobs|work)\b",
                r"\b(ai\s*video|video\s+creator|smm|social\s+media)\s+(jobs?|job\s+hunting|hunt)\b",
                r"\b(prep|prepare|start|launch|open|setup)\s+(?:for\s+)?(?:my\s+|the\s+|our\s+)?(gaming|stream|games|leisure)\b",
                r"\b(launch|start|open|run)\s+(the\s+)?(routine|workspace)\b",
                r"\b(set|schedule|add)\s+(an?\s+)?(interview|meeting\s+link|class\s+link)\b",
                r"\b(add|schedule)\s+(an?\s+)?interview\s+schedule\b",
                r"\b(open|trigger|show)\s+(the\s+)?(interview|routine)\s+(modal|form|card)\b",
            ]),
        ]

        self._triggers = []
        registered_ids = set()

        # 1. Collect declared triggers from active skill instances
        for skill_id, skill in self._skills.items():
            declared_triggers = getattr(skill, "TRIGGERS", [])
            if declared_triggers:
                for pat in declared_triggers:
                    try:
                        self._triggers.append((re.compile(pat, re.IGNORECASE), skill_id))
                        registered_ids.add(skill_id)
                    except Exception as e:
                        print(f"[SkillRouter] Invalid regex in skill '{skill_id}': {pat} ({e})")

        # 2. Add fallback trigger definitions for standard skills
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

        # 1. Check custom can_handle() on active skills first
        for skill_id, skill in self._skills.items():
            try:
                if hasattr(skill, "can_handle") and skill.can_handle(cleaned):
                    print(f"[SkillRouter] can_handle matched skill: {skill_id}")
                    return skill
            except Exception as e:
                print(f"[SkillRouter] Error checking can_handle for {skill_id}: {e}")

        # 2. Check regex trigger patterns
        for pattern, skill_id in self._triggers:
            if pattern.search(cleaned):
                # 1. If research triggered but command asks to play/watch, pass to ComputerRouter
                if skill_id == "research" and re.search(r"\b(?:and\s+)?play\b|\bwatch\b|\bstream\b", cleaned, re.IGNORECASE):
                    continue

                # 2. Collision Shield: "open google chrome", "launch chrome", "open browser" -> let ComputerRouter handle it
                if skill_id == "research" and re.search(r"^(?:open|launch|start|run)\s+(?:google\s+)?(?:chrome|browser)\b", cleaned, re.IGNORECASE):
                    continue

                # 3. Collision Shield: Local file search commands ("search my files for ...", "find in files") -> let ComputerRouter handle it
                if skill_id == "research" and re.search(r"\b(?:my\s+files|local\s+files|in\s+files|files?\s+for|folder\s+for)\b", cleaned, re.IGNORECASE):
                    continue

                # 4. Collision Shield: Web search query -> prioritize ResearchSkill over Composio
                if skill_id == "composio" and re.search(r"\b(?:the\s+web|online|google|duckduckgo|internet)\b", cleaned, re.IGNORECASE):
                    continue

                # 5. Collision Shield: File deletion commands ("delete file ...", "remove file ...") -> let ComputerRouter handle it
                if skill_id == "memory" and re.search(r"\b(?:delete|remove|clear)\s+(?:file|document|folder|item|notes?\.txt|\w+\.\w{2,4})\b", cleaned, re.IGNORECASE):
                    continue

                # 6. Collision Shield: "open facebook", "open github", "launch notion", "open discord", "open spotify" -> let ComputerRouter handle it
                if skill_id == "composio" and re.search(r"^(?:open|launch|start|go\s+to)\s+(?:facebook|fb|github|notion|discord|spotify|trello|gitlab)\b", cleaned, re.IGNORECASE):
                    continue

                skill = self._skills.get(skill_id)
                if skill:
                    print(f"[SkillRouter] Matched skill: {skill_id}")
                    return skill

        return None

    def register(self, skill_id: str, skill_instance: object) -> None:
        """
        Register a new skill instance.

        Args:
            skill_id:       Unique skill identifier.
            skill_instance: The skill object with an execute() method.
        """
        self._skills[skill_id] = skill_instance
        self._build_trigger_map()
        print(f"[SkillRouter] Registered skill: {skill_id}")

    def get_skill(self, skill_id: str) -> Optional[object]:
        """Return the skill instance for a given skill_id, or None."""
        return self._skills.get(skill_id)

    def list_skills(self) -> list[str]:
        """Return a list of all registered skill IDs."""
        return list(self._skills.keys())

    def get_catalog(self) -> list[dict]:
        """Return structured skill catalog."""
        if self._registry and hasattr(self._registry, "get_catalog"):
            return self._registry.get_catalog()
        return [{"id": sid, "name": sid.title()} for sid in self._skills]

