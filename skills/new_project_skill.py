"""
MakiAI — New Project Skill
Triggers the KB new-project planning process via voice.

Since full 11-stage planning requires back-and-forth, this skill
captures the project idea and generates Stage 1 to kick off planning.
The full session continues in the chat log via text/voice.

Triggered by: "new project", "I have a project idea", "I want to build", "let's build"
Reads: config/coding-standards.md, web-development/architecture.md
"""

from skills.base_skill import BaseSkill


class NewProjectSkill(BaseSkill):

    SKILL_ID = "new_project"
    REQUIRED_FILES = [
        "config/coding-standards.md",
        "web-development/architecture.md",
        "web-development/folder-structure.md",
        "projects/_template/project-structure.md",
    ]

    def execute(self, text: str) -> str:
        """
        Kick off Stage 1 of the new project planning session.
        Extracts the project idea from the user's voice input.
        """
        prompt = f"""
The user said: "{text}"

They want to start a new project. Extract their project idea from the input.

Then begin Stage 1 of the project planning process:

📍 Stage 1 of 11 — Requirements & Idea Clarification

Summarize your understanding of the idea:
- Project Name (suggested): [PascalCase]
- What it is: [1 sentence]
- Who it's for: [target users]
- Platform: [Web / Mobile / Desktop / CLI]
- Core problem it solves: [1 sentence]

If anything is unclear, list 2–3 clarifying questions.

End with: "Does this match your vision? Type or say your corrections, then say 'next' to continue to Stage 2."

Keep the voice output concise — under 100 words spoken. 
The full details will appear in the chat log.
""".strip()

        return self._ask_gemini(prompt)
