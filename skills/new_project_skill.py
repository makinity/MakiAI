"""
MakiAI — New Project Skill
Manages the complete 11-Stage Knowledge Base Project Planning Lifecycle.
Strictly adheres to:
  - C:\\Knowledge-Base\\projects\\_template\\project-structure.md
  - C:\\Knowledge-Base\\workflows\\website-development.md
  - C:\\Knowledge-Base\\web-development\\folder-structure.md
  - C:\\Knowledge-Base\\config\\coding-standards.md

At Stage 11 (Approval), automatically writes the complete 6-file suite:
  - overview.md
  - plan.md
  - architecture.md
  - filepath.md
  - decisions.md
  - progress.md
  - ui.md (if web/mobile)
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, List
from skills.base_skill import BaseSkill


class NewProjectSkill(BaseSkill):

    SKILL_ID = "new_project"
    REQUIRED_FILES = [
        "config/coding-standards.md",
        "web-development/architecture.md",
        "web-development/folder-structure.md",
        "projects/_template/project-structure.md",
        "workflows/website-development.md",
    ]

    STAGE_NAMES = {
        1: "Requirements & Idea Clarification",
        2: "Tech Stack & Architecture Selection",
        3: "Feature Specifications & Core Scope",
        4: "Database Design & Data Persistence",
        5: "Folder Structure & Layer Architecture",
        6: "API & Service Layer Contracts",
        7: "UI/UX & Design Tokens",
        8: "Implementation Milestones & Checklist",
        9: "Architecture Decision Records (ADRs)",
        10: "Workspace & File Path Setup",
        11: "Final Review & Knowledge Base Generation",
    }

    def __init__(self, gemini_service, context_builder, kb_reader, kb_writer):
        super().__init__(gemini_service, context_builder, kb_reader, kb_writer)
        self._is_active: bool = False
        self._current_stage: int = 1
        self._project_data: Dict[str, Any] = self._empty_project_data()
        self._history: List[Dict[str, str]] = []
        self.ui_bridge = None

    def set_ui_bridge(self, ui_bridge) -> None:
        """Connect UI bridge to trigger interactive project scaffolding modal."""
        self.ui_bridge = ui_bridge

    def _empty_project_data(self) -> Dict[str, Any]:
        user_name = os.getenv("USER_NAME", "User")
        return {
            "name": "NewProject",
            "summary": "",
            "target_users": f"{user_name} (Personal / Client)",
            "platform": "Web (Next.js App Router)",
            "core_problem": "",
            "stack": "Next.js 14/15 (App Router, TypeScript) + Tailwind CSS",
            "stack_category": "NextJS",
            "features": [],
            "database": "LocalStorage (Client) / Supabase (Future)",
            "folder_structure": "",
            "ui_tokens": {
                "palette": "Dark Glassmorphic (Background #0d1117, Accent #00f2fe)",
                "typography": "Inter / Roboto",
            },
            "milestones": [],
            "decisions": [],
            "dev_path": "C:\\development\\NextJS\\NewProject\\",
        }

    def is_planning_active(self) -> bool:
        """Check if an interactive 11-stage planning session is underway."""
        return self._is_active

    def reset(self) -> None:
        """Reset the planning session state."""
        self._is_active = False
        self._current_stage = 1
        self._project_data = self._empty_project_data()
        self._history = []

    def execute(self, text: str) -> str:
        """
        Execute or advance the 11-stage planning session.
        """
        cleaned = text.strip()

        # Check for cancellation
        if re.search(r"\b(cancel|stop|abort|exit|quit|nevermind|never\s+mind)\b", cleaned, flags=re.IGNORECASE):
            self.reset()
            return "Project planning session cancelled, sir. Let me know when you'd like to start anew."

        if not self._is_active:
            return self._start_stage_1(cleaned)
        else:
            return self._handle_subsequent_stages(cleaned)

    def _start_stage_1(self, text: str) -> str:
        """Initiate Stage 1: Idea Clarification."""
        self._is_active = True
        self._current_stage = 1
        self._history = [{"user": text}]

        prompt = f"""
The user wants to start a new software/web project. Their input: "{text}"

Follow Stage 1 of the 11-Stage Knowledge Base Project Planning Lifecycle:
📍 Stage 1 of 11 — Requirements & Idea Clarification

Extract/Propose:
- Project Name (PascalCase, e.g. TaskMaster, MunchBite)
- Summary: 1 clear sentence
- Target Users: (e.g. Personal productivity for user, or client-facing)
- Platform: Web (Next.js) / Backend (Laravel) / Mobile (React Native) / Desktop (C#)
- Core Problem Solved: 1 sentence

Ask 1-2 clarifying questions if needed.
End with: "Does this match your vision, sir? Say 'next' or provide your adjustments to proceed to Stage 2 (Tech Stack)."

Keep response concise and conversational (spoken by personal assistant).
""".strip()

        response = self._ask_gemini(prompt)
        
        # Try extracting project name from AI response or input
        name_match = re.search(r"Project Name(?:\s*\(suggested\))?:\s*\*?([A-Za-z0-9_\-]+)\*?", response)
        if name_match:
            self._project_data["name"] = name_match.group(1).strip()
        else:
            # Fallback extraction from user input
            cand = re.search(r"\b(?:called|named|build|project)\s+([A-Za-z0-9_\-]+)", text, flags=re.IGNORECASE)
            if cand and cand.group(1).lower() not in ("a", "an", "new", "this", "my"):
                self._project_data["name"] = cand.group(1).capitalize()

        # If UI bridge is connected, launch interactive Scaffolding Modal
        if hasattr(self, "ui_bridge") and self.ui_bridge:
            proj_name = self._project_data["name"]
            draft = {
                "id": f"proj_{int(datetime.now().timestamp())}",
                "name": proj_name,
                "vision": f"Modern application architecture for {proj_name}",
                "stack": "Next.js + Tailwind",
                "target_path": "c:\\development\\NextJS",
            }
            self.ui_bridge.set_active_modal("new_project", draft)
            return f"I've initiated the project configuration for {proj_name}, sir. You can select your preferred tech stack and target folder directly on your screen."

        return response

    def _handle_subsequent_stages(self, text: str) -> str:
        """Advance through Stages 2 to 11."""
        self._history.append({"user": text})

        # Advance stage counter if user approves or says next
        if re.search(r"\b(next|continue|proceed|looks good|yes|correct|agreed|approve)\b", text, flags=re.IGNORECASE) or len(text) > 5:
            self._current_stage += 1

        if self._current_stage > 11:
            return self._finalize_project()

        stage_name = self.STAGE_NAMES.get(self._current_stage, f"Stage {self._current_stage}")
        proj_name = self._project_data["name"]

        # Guide each stage adhering strictly to KB rules
        stage_instructions = {
            2: (
                f"📍 Stage 2 of 11 — Tech Stack & Architecture Selection\n"
                f"For Web apps, recommend Next.js (App Router, TypeScript) + Tailwind CSS.\n"
                f"For Backend/APIs, recommend Laravel (PHP) or Spring Boot (Java).\n"
                f"Define the stack table and layered architecture (Presentation ➔ Service ➔ Repository ➔ DB).\n"
                f"Ask user confirmation to move to Stage 3 (Feature Specifications)."
            ),
            3: (
                f"📍 Stage 3 of 11 — Feature Specifications & Core Scope\n"
                f"Break down 4-6 essential MVP features for {proj_name}.\n"
                f"Ask user if any features should be added or removed before Stage 4 (Database Design)."
            ),
            4: (
                f"📍 Stage 4 of 11 — Database Design & Persistence\n"
                f"Define the data model/schema (Entities, fields, relationships, or LocalStorage JSON schema).\n"
                f"Ask user confirmation to move to Stage 5 (Folder Structure)."
            ),
            5: (
                f"📍 Stage 5 of 11 — Folder Structure (Knowledge Base Standard)\n"
                f"Show the clean Next.js / framework folder layout (src/app, src/components/shared, src/services, src/repositories, src/types).\n"
                f"Ask user confirmation to move to Stage 6 (API & Service Contracts)."
            ),
            6: (
                f"📍 Stage 6 of 11 — API & Service Layer Contracts\n"
                f"Outline the core service methods / API routes.\n"
                f"Ask user confirmation to move to Stage 7 (UI/UX & Design Tokens)."
            ),
            7: (
                f"📍 Stage 7 of 11 — UI/UX & Design Tokens\n"
                f"Define the dark mode glassmorphic color palette, font styles, and component aesthetics.\n"
                f"Ask user confirmation to move to Stage 8 (Milestones & Checklist)."
            ),
            8: (
                f"📍 Stage 8 of 11 — Implementation Milestones & Checklist\n"
                f"Structure into Phase 1 (Setup ➔ Core Features ➔ Polish) with [ ] checklists matching MunchBite plan.md.\n"
                f"Ask user confirmation to move to Stage 9 (Architecture Decisions)."
            ),
            9: (
                f"📍 Stage 9 of 11 — Architecture Decision Records (ADRs)\n"
                f"Document why the tech stack, state management, and architecture patterns were chosen.\n"
                f"Ask user confirmation to move to Stage 10 (File Path Setup)."
            ),
            10: (
                f"📍 Stage 10 of 11 — Workspace & File Path Setup\n"
                f"Declare the source code path: C:\\development\\NextJS\\{proj_name}\\\n"
                f"Declare the KB docs path: C:\\Knowledge-Base\\projects\\{proj_name}\\\n"
                f"Ask user: 'Say approve to generate your Knowledge Base documentation suite and prepare for Kiro coding.'"
            ),
            11: (
                f"📍 Stage 11 of 11 — Final Review & Approval\n"
                f"Summarize the completed architecture for {proj_name}.\n"
                f"Confirm that all 6 Knowledge Base files will be written to C:\\Knowledge-Base\\projects\\{proj_name}\\.\n"
                f"Prompt: Say 'confirm' or 'yes' to write the Knowledge Base files."
            ),
        }

        current_prompt = f"""
Project Name: {proj_name}
Active Stage: {stage_name}
User response: "{text}"

{stage_instructions.get(self._current_stage, "Continue the planning dialogue.")}

Keep response structured, concise, and professional.
""".strip()

        return self._ask_gemini(current_prompt)

    def _finalize_project(self) -> str:
        """
        Stage 11 Complete: Write the full 6-file suite into C:\Knowledge-Base\projects\<name>\
        """
        proj = self._project_data["name"]
        date_str = datetime.now().strftime("%Y-%m-%d")
        stack_folder = self._project_data["stack_category"]
        dev_path = f"C:\\development\\{stack_folder}\\{proj}\\"

        # 1. overview.md
        overview_content = f"""# {proj}

> **Status:** Planning Completed
> **Stack:** {self._project_data['stack']}
> **Dev Path:** `{dev_path}`
> **Started:** {date_str}
> **Last Updated:** {date_str}

## What It Is
{self._project_data['summary'] or f'{proj} is a modern application built following Knowledge Base architecture standards.'}

## Target Users
{self._project_data['target_users']}

## Core Problem Solved
{self._project_data['core_problem'] or 'Streamlines workflow and delivers responsive user experience.'}

## Current Status
Stage 1-11 Planning completed. Ready for automated code scaffolding via Kiro CLI.
""".strip()

        # 2. filepath.md
        filepath_content = f"""# {proj} — File Path

> **Purpose:** Tells AI agents and Kiro CLI exactly where the source code lives.
> **Last Updated:** {date_str}

---

## Source Code Location

**Primary Path:** `{dev_path}`

---

## KB Documentation Location

```
C:\\Knowledge-Base\\projects\\{proj}\\
├── overview.md
├── plan.md
├── architecture.md
├── filepath.md
├── decisions.md
├── progress.md
└── ui.md
```

---

## Rules

- KB documentation only lives in `C:\\Knowledge-Base\\projects\\{proj}\\`
- Source code only lives in `{dev_path}`
- Never store source files inside the Knowledge Base
""".strip()

        # 3. architecture.md
        architecture_content = f"""# {proj} — Architecture

> **Last Updated:** {date_str}

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 14/15 (App Router, TypeScript) |
| Styling | Tailwind CSS (Glassmorphic Dark Theme) |
| Icons | Lucide-React |
| State/Storage | Isolated Repository Pattern (LocalStorage / API) |
| Deployment | Vercel |

---

## Layered Architecture

```
Presentation Layer (React Components / App Router)
        ↓
Service Layer (Business Logic / Hooks)
        ↓
Repository / Data Access Layer
        ↓
Data Source (Browser Storage / Database)
```

---

## Folder Structure

```
{dev_path}
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.mjs
└── src/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── globals.css
    ├── components/
    │   ├── shared/
    │   └── {proj.lower()}/
    ├── services/
    ├── repositories/
    ├── hooks/
    ├── types/
    └── lib/
```
""".strip()

        # 4. plan.md
        plan_content = f"""# {proj} — Development Plan

> **Last Updated:** {date_str}

---

## Phase 1 — Project Scaffolding & Core MVP

### Stage 1 — Setup
- [ ] Initialize Next.js project with TypeScript and Tailwind CSS
- [ ] Configure Tailwind palette and dark mode glassmorphism
- [ ] Create folder structure (`src/app`, `src/components`, `src/services`, `src/repositories`, `src/types`, `src/lib`)

### Stage 2 — Domain & Layer Implementation
- [ ] Implement TypeScript domain types
- [ ] Implement repository storage layer
- [ ] Implement service business logic & custom React hooks

### Stage 3 — Component Development
- [ ] Build reusable UI components in `src/components/shared/`
- [ ] Build feature components in `src/components/{proj.lower()}/`
- [ ] Assemble main dashboard in `src/app/page.tsx`

### Stage 4 — Polish & Verification
- [ ] Mobile responsive layout pass
- [ ] Micro-animations and toast notifications
- [ ] Final manual testing & validation
""".strip()

        # 5. decisions.md
        decisions_content = f"""# {proj} — Decisions Log

> **Last Updated:** {date_str}

---

## ADR 001: Technology Stack Selection
- **Decision:** Use Next.js App Router with TypeScript and Tailwind CSS.
- **Reason:** Aligns with Knowledge Base web standards, high performance, and rapid UI development.

## ADR 002: Layered Separation
- **Decision:** Separate repository persistence from service business logic.
- **Reason:** Enables seamless future transition from LocalStorage to Supabase or backend APIs without touching UI components.
""".strip()

        # 6. progress.md
        progress_content = f"""# {proj} — Progress Log

> **Last Updated:** {date_str}

---

## Current Status
- **Phase:** Phase 1 — MVP Scaffolding
- **Active Stage:** Ready for Kiro CLI execution
- **Completion:** Planning 100% complete
""".strip()

        # 7. ui.md
        ui_content = f"""# {proj} — UI & Design System

> **Last Updated:** {date_str}

---

## Design Theme
- **Style:** Dark Glassmorphism with Sleek Accents
- **Background:** `#0d1117`, `#161b22`
- **Accent:** Cyan / Sky Blue (`#00f2fe`, `#4facfe`)
- **Typography:** Inter / Roboto / System Sans
""".strip()

        # Write all files through KBWriter
        base_kb_dir = f"projects/{proj}"
        if self.kb_writer:
            self.kb_writer.write(f"{base_kb_dir}/overview.md", overview_content)
            self.kb_writer.write(f"{base_kb_dir}/filepath.md", filepath_content)
            self.kb_writer.write(f"{base_kb_dir}/architecture.md", architecture_content)
            self.kb_writer.write(f"{base_kb_dir}/plan.md", plan_content)
            self.kb_writer.write(f"{base_kb_dir}/decisions.md", decisions_content)
            self.kb_writer.write(f"{base_kb_dir}/progress.md", progress_content)
            self.kb_writer.write(f"{base_kb_dir}/ui.md", ui_content)

        # Reset active session
        self.reset()

        return (
            f"Planning for {proj} is complete, sir! All 7 Knowledge Base specification documents "
            f"have been saved to C:\\Knowledge-Base\\projects\\{proj}\\ following the MunchBite standard. "
            f"Whenever you are ready, simply say 'Start developing {proj} with Kiro' to scaffold the Next.js project in {dev_path}."
        )

