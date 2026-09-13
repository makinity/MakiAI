# 🎙️ MakiAI — Voice Command Training & Engine Calibration Log

This document records the user voice/text commands, analysis, step-by-step internal execution mapping, status, and any potential engine adjustments needed.

---

## 📋 Command Evaluation Log

### 🔹 Command #1
* **Spoken Phrase:** `"Hey Maki, what is my current schedule today?"`
* **Audio Input:** User Voice Recording (`.wav`)
* **Extracted Payload:** `"what is my current schedule today"`
* **Status:**  **Optimal & 100% Supported**

#### ⚙️ Internal Execution Flow:
1. **Audio Capture & STT**: Transcribed via Groq Whisper (`whisper-large-v3-turbo`). Strips `"Hey Maki"`.
2. **Skill Routing**: Matches `SkillRouter` trigger pattern `r"\bwhat\s+is\s+(our|my)\s+schedule\b"` ➔ **`HelloSkill`** (`skills/hello_skill.py`).
3. **Execution**:
   - Calculates Philippine Time (PHT).
   - Reads user schedule & active time-block from Knowledge Base (`KBReader`).
   - Checks active reminders and memory entries for today.
4. **TTS Spoken Output**: Edge TTS (`en-US-GuyNeural`) speaks current time block and upcoming events.
5. **State Machine**: Transitions to **Active Conversation Session** (45s listening window) for direct follow-up commands without wake words.

### 🔹 Command #2
* **Spoken Phrase:** `"Can you add a schedule for tomorrow at 9:00 PM that we have a meeting via Zoom?"`
* **Audio Input:** User Voice Recording (`.wav`)
* **Extracted Payload:** `"add a schedule for tomorrow at 9:00 PM that we have a meeting via Zoom"`
* **Status:** ⚠️ **Routing Gap Identified (Fallback to general chat instead of Reminder Engine)**
* **User Desired Outcome:** **Option A (Scheduled Voice Alert / Reminder)** — Save into `data/reminders.json` so Maki triggers an active audible alert at 9:00 PM tomorrow.

#### ⚙️ Internal Execution Flow (Target Behavior):
1. **Audio Capture & STT**: Transcribed via Groq Whisper (`whisper-large-v3-turbo`).
2. **Skill Routing**: Matches `SkillRouter` ➔ **`ReminderSkill`** (`skills/reminder_skill.py`).
3. **Execution**:
   - `ReminderSkill._add()` parses `"tomorrow at 9:00 PM"` and message `"Zoom meeting"`.
   - Schedules reminder in `ReminderService` and saves to `data/reminders.json`.
4. **TTS Spoken Confirmation**: Edge TTS speaks: *"Got it. I'll remind you about the Zoom meeting tomorrow at 9:00 PM."*
5. **Scheduled Trigger**: Tomorrow at 21:00 PHT, MakiAI speaks: *"Sir, this is your reminder: Zoom meeting."*

### 🔹 Command #3
* **Spoken Phrase:** `"Remind me that we have an assignment task to finish later at 7:00 PM."`
* **Audio Input:** User Voice Recording (`.wav`)
* **Extracted Payload:** `"remind me that we have an assignment task to finish later at 7:00 PM"`
* **Status:** ⚠️ **Routing Gap Identified (Missing `"that"` in `remind me` trigger)**
* **Target Outcome:** Schedule an active reminder in `data/reminders.json` for 7:00 PM today.

#### ⚙️ Internal Execution Flow (Target Behavior):
1. **Audio Capture & STT**: Transcribed via Groq Whisper (`whisper-large-v3-turbo`).
2. **Skill Routing**: Matches `SkillRouter` ➔ **`ReminderSkill`** (`skills/reminder_skill.py`).
3. **Execution**:
   - `ReminderSkill._add()` parses `"later at 7:00 PM"` (Today at 19:00 PHT) and task `"finish assignment task"`.
   - Schedules in `ReminderService` and writes to `data/reminders.json`.
4. **TTS Spoken Confirmation**: Edge TTS speaks: *"Got it. I'll remind you to finish assignment task at 07:00 PM today."*
5. **Scheduled Trigger**: At 19:00 PHT today, MakiAI alerts: *"Sir, this is your reminder: finish assignment task."*

### 🔹 Command #4
* **Spoken Phrase:** `"Can you help me finish my homework assignment and guide me so that we can finish this today and ready to pass?"`
* **Audio Input:** User Voice Recording (`.wav`)
* **Extracted Payload:** `"can you help me finish my homework assignment and guide me so that we can finish this today and ready to pass"`
* **Status:**  **Optimal & 100% Supported (2-Step Interactive Homework Engine)**

#### ⚙️ Internal Execution Flow:
1. **Audio Capture & STT**: Transcribed via Groq Whisper (`whisper-large-v3-turbo`).
2. **Skill Routing**: Matches `SkillRouter` pattern `r"\bfinish\s+(my\s+)?homework\b"` ➔ **`HomeworkSkill`** (`skills/homework_skill.py`).
3. **Step 1 Execution (Folder & Guidance)**:
   - Automatically opens `C:\MakiSync Storage\School\Temp-Guide\` in Windows File Explorer.
   - `Orchestrator` sets `_awaiting_homework_instructions = True`.
4. **TTS Spoken Guidance**: Edge TTS speaks:
   > *"I've opened the Temp-Guide folder for you, sir. Please drop in your guide files — like the format template, rubric, or reference documents. Once you've added them, tell me what the homework is about and I'll take care of the rest."*
5. **Step 2 Execution (When you speak the prompt)**:
   - When you say the topic (e.g., *"Write a reflection paper on Data Privacy following the rubric"*), Maki parses the rubric files, generates the academic content via Gemini, compiles a formatted Microsoft Word (`.docx`) file in `C:\MakiSync Storage\School\Assignments\<today>\`, and opens the `.docx` document automatically!

### 🔹 Command #5
* **Spoken Phrase:** `"Maki, I have a new project idea. It is about a Crispy King website project where it is a POS system that allows the Crispy King staff to manage their inventory, sales, and etc."`
* **Audio Input:** User Voice Recording (`.wav`)
* **Extracted Payload:** `"i have a new project idea it is about a crispy king website project where it is a pos system that allows the crispy king staff to manage their inventory sales and etc"`
* **Status:**  **Optimal & 100% Supported (11-Stage Project Pipeline Engine)**

#### ⚙️ Internal Execution Flow:
1. **Audio Capture & STT**: Transcribed via Groq Whisper (`whisper-large-v3-turbo`). Strips `"Maki"`.
2. **Skill Routing**: Matches `SkillRouter` pattern `r"\bi\s+have\s+(a\s+)?project\s+idea\b"` ➔ **`NewProjectSkill`** (`skills/new_project_skill.py`).
3. **Stage 1 Activation**:
   - `NewProjectSkill` initializes the interactive 11-Stage Planning Pipeline (`_is_active = True`, `Stage 1: Requirements & Idea Clarification`).
   - Extracts:
     - **Project Name:** `CrispyKingPOS`
     - **Core Scope:** Point of Sale, Inventory Management, Sales Tracking for staff.
     - **Architecture Standards:** Follows `C:\Knowledge-Base\projects\_template\project-structure.md`.
4. **TTS Spoken Response**: Edge TTS speaks:
   > *"Understood, sir! Let's plan the Crispy King POS project. For Stage 1: We're scoping a Point of Sale web app for staff with inventory control and sales reporting. What specific roles or hardware features should we support — such as cashier vs manager roles, receipt printing, or barcode scanning?"*
5. **Multi-Stage Conversational Progression**:
   - As you speak naturally in the active session, Maki walks with you through all 11 stages (Tech Stack, DB schema, UI wireframes, Folder structure).
   - At Stage 11 approval, Maki automatically writes the full 6-file suite (`overview.md`, `plan.md`, `architecture.md`, `filepath.md`, `decisions.md`, `progress.md`, `ui.md`) into your Knowledge Base and can scaffold it directly with Kiro CLI!

### 🔹 Command #6
* **Spoken Phrase:** `"Maki, can you help me find out if the ROs Legacy... ROs Legacy game is legit or not? You can do a deep research on my Chrome."`
* **Audio Input:** User Voice Recording (`.wav`)
* **Extracted Payload:** `"help me find out if the ROs Legacy game is legit or not you can do a deep research on my Chrome"`
* **Status:** ⚠️ **Adjustment Identified (Option B: Spoken Answer + Auto-Launch Chrome Tab)**
* **User Desired Outcome:** **Option B** — Maki performs autonomous web search via BareResearch (`paulablaza/bare-research` engine), speaks the summarized legitimacy verdict aloud, AND automatically opens Chrome with the search query / top reference link so the user can inspect it visually.

#### ⚙️ Internal Execution Flow (Target Behavior):
1. **Audio Capture & STT**: Transcribed via Groq Whisper (`whisper-large-v3-turbo`). Strips `"Maki"`.
2. **Skill Routing**: Matches `SkillRouter` pattern `r"\b(search|look\s+up|google|research)\b"` ➔ **`ResearchSkill`** (`skills/research_skill.py`).
3. **Deep Web Search**:
   - `ResearchSkill` uses the `BareResearch` engine (Multi-tier: Tavily / Serper / DuckDuckGo fallback) to search for `"ROs Legacy game legit review scam"`.
   - Synthesizes findings using Gemini.
4. **TTS Spoken Verdict**: Edge TTS speaks:
   > *"Sir, based on online community reports and server reviews, ROs Legacy is [verdict summary]. I've opened the search results and discussion page on your Chrome browser."*
5. **Visual Browser Launch**:
   - Automatically opens Google Chrome (`webbrowser.open_new_tab(google_search_url)`) to the search results / top discussion page.

#### 📝 Pending Adjustments (To be batch applied later):
* In `skills/research_skill.py`:
  - Enhance query extraction to distill natural speech (`"help me find out if X is legit... on my Chrome"`) into clean search terms (`"X legit or scam review"`).
  - If `"chrome"`, `"browser"`, or `"open"` is mentioned in the voice command, call `webbrowser.open_new_tab()` to open the top search URL / Google results in Chrome.

---






### 🔹 Live Session Command — 04:54:36 PM
* **Spoken / Typed Command:** `"Hey Maki."`
* **Extracted Payload:** `""`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"Good afternoon, sir. How can I assist you today?"`

---

### 🔹 Live Session Command — 04:54:59 PM
* **Spoken / Typed Command:** `"Thank you."`
* **Extracted Payload:** `"Thank you."`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"You're welcome, sir. Anything you'd like me to take care of right now?"`

---

### 🔹 Live Session Command — 04:56:40 PM
* **Spoken / Typed Command:** `"Hi"`
* **Extracted Payload:** `"Hi"`
* **Matched Handler:** `Skill:HelloSkill`
* **Status:** ✅ **Optimal & Routed**
* **Maki Spoken Response:** `"Good afternoon, sir. It’s 04:56 PM Philippine Time, and you’re right now in your dedicated Video Editing and AI Video Editing Mastery sessio..."`

---

### 🔹 Live Session Command — 04:57:14 PM
* **Spoken / Typed Command:** `"Can you open google classroom?"`
* **Extracted Payload:** `"Can you open google classroom?"`
* **Matched Handler:** `Skill:ResearchSkill`
* **Status:** ✅ **Optimal & Routed**
* **Maki Spoken Response:** `"Sure thing, sir. I’m opening Google Classroom for you now at https://classroom.google.com/. Let me know if you need anything else once you’r..."`

---

### 🔹 Live Session Command — 04:57:37 PM
* **Spoken / Typed Command:** `"Open facebook"`
* **Extracted Payload:** `"Open facebook"`
* **Matched Handler:** `ComputerRouter`
* **Status:** ✅ **Optimal & Routed**
* **Maki Spoken Response:** `"Opening Facebook in your personal profile, sir."`

---

### 🔹 Live Session Command — 04:57:46 PM
* **Spoken / Typed Command:** `"Thank you."`
* **Extracted Payload:** `"Thank you."`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"You’re welcome, sir. Anything else I can help with right now?"`

---

### 🔹 Live Session Command — 05:11:28 PM
* **Spoken / Typed Command:** `"Hey Maki."`
* **Extracted Payload:** `""`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"Good evening, sir. It's 5:11 PM here in the Philippines. You have the AI Ad Video deadline tomorrow at 1 PM, so you might want to set aside ..."`

---

### 🔹 Live Session Command — 05:11:58 PM
* **Spoken / Typed Command:** `"Maki, send me my cv"`
* **Extracted Payload:** `"Maki, send me my cv"`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"I don’t see a CV file listed in your Knowledge Base or in the MakiSync storage, sir. Could you let me know where it’s saved, or would you li..."`

---

### 🔹 Live Session Command — 05:15:33 PM
* **Spoken / Typed Command:** `"Maki, send me my cv"`
* **Extracted Payload:** `"Maki, send me my cv"`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"I don’t see a CV file listed in your Knowledge Base, sir. Would you like me to look through your MakiSync storage for it, or create a new do..."`

---

### 🔹 Live Session Command — 05:19:55 PM
* **Spoken / Typed Command:** `"Send me my latest capstone paper"`
* **Extracted Payload:** `"Send me my latest capstone paper"`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"Right away, sir. Let me look in your MakiSync Storage under the School folder for the most recent capstone paper. I’ll open it for you in a ..."`

---

### 🔹 Live Session Command — 05:20:14 PM
* **Spoken / Typed Command:** `"Maki."`
* **Extracted Payload:** `"Maki."`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"Yes, sir? How can I assist you?"`

---

### 🔹 Live Session Command — 05:20:18 PM
* **Spoken / Typed Command:** `"Open youtube"`
* **Extracted Payload:** `"Open youtube"`
* **Matched Handler:** `ComputerRouter`
* **Status:** ✅ **Optimal & Routed**
* **Maki Spoken Response:** `"Opening YouTube in your personal profile, sir."`

---

### 🔹 Live Session Command — 05:20:24 PM
* **Spoken / Typed Command:** `"Thank you."`
* **Extracted Payload:** `"Thank you."`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"You’re welcome, sir. Let me know if there’s anything else I can do for you."`

---

### 🔹 Live Session Command — 05:22:25 PM
* **Spoken / Typed Command:** `"what is the current time today?"`
* **Extracted Payload:** `"what is the current time today?"`
* **Matched Handler:** `Skill:HelloSkill`
* **Status:** ✅ **Optimal & Routed**
* **Maki Spoken Response:** `"It's 05:22 PM Philippine Time, sir. Right now you're in your Video Editing and AI Video Editing Mastery session, as today’s Sunday schedule ..."`

---

### 🔹 Live Session Command — 05:22:35 PM
* **Spoken / Typed Command:** `"Thank you."`
* **Extracted Payload:** `"Thank you."`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"You're welcome, sir. Let me know if there's anything else I can help with."`

---

### 🔹 Live Session Command — 05:29:12 PM
* **Spoken / Typed Command:** `"Hi"`
* **Extracted Payload:** `"Hi"`
* **Matched Handler:** `Skill:HelloSkill`
* **Status:** ✅ **Optimal & Routed**
* **Maki Spoken Response:** `"Good afternoon, sir. It’s 05:29 PM Philippine Time, and the day’s override has you in the Video Editing and AI Video Editing Mastery block r..."`

---

### 🔹 Live Session Command — 05:30:35 PM
* **Spoken / Typed Command:** `"I want the pdf one"`
* **Extracted Payload:** `"I want the pdf one"`
* **Matched Handler:** `Fallback:Gemini`
* **Status:** ⚠️ **Fallback / Needs Calibration**
* **Maki Spoken Response:** `"Sure thing, sir. Which PDF are you looking for—perhaps the schedule, the deadline list, or one of your project documents? Let me know and I’..."`

---
