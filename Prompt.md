# 🎙️ MakiAI — The Ultimate Master Prompting & Command Encyclopedia

> **Personal Autonomous Operating Assistant for Mark Vencent Juntilla**  
> *Inspired by Jarvis — Connected to Knowledge Base, Hardware Telemetry, Vision, Computer Automation, and Kiro CLI.*

---

## 📑 Table of Contents

1. [Architectural Overview & Operating Principles](#1-architectural-overview--operating-principles)
2. [Input Channels & Interaction Modes](#2-input-channels--interaction-modes)
3. [Daily Workflow Routines & Live Clock Briefings](#3-daily-workflow-routines--live-clock-briefings)
4. [Long-Term Memory & Active Notes (`data/memory.json`)](#4-long-term-memory--active-notes-datamemoryjson)
5. [Deadlines & Task Management (`workflows/deadlines.md`)](#5-deadlines--task-management-workflowsdeadlinesmd)
6. [Timed Reminders & Audio Alarms (`data/reminders.json`)](#6-timed-reminders--audio-alarms-dataremindersjson)
7. [⚡ Kiro CLI Autonomous Coding Engine (`t=kiro`)](#7-⚡-kiro-cli-autonomous-coding-engine-tkiro)
8. [🏗️ 11-Stage Knowledge Base Project Pipeline](#8-🏗️-11-stage-knowledge-base-project-pipeline)
9. [📝 Automated Homework & Research Paper Engine (`.docx`)](#9-📝-automated-homework--research-paper-engine-docx)
10. [📂 MakiSync Storage & Intelligent File Operations](#10-📂-makisync-storage--intelligent-file-operations)
11. [👁️ Physical Optical Webcam Vision (World Observer)](#11-👁️-physical-optical-webcam-vision-world-observer)
12. [🖥️ Live Screen Vision & Visual Error Debugging](#12-🖥️-live-screen-vision--visual-error-debugging)
13. [🪟 Multi-Monitor Window Management & Auto-Tiling](#13-🪟-multi-monitor-window-management--auto-tiling)
14. [🌐 Chrome Multi-Profile Site Launcher](#14-🌐-chrome-multi-profile-site-launcher)
15. [🔊 Native Windows Audio, Volume & Media Controls](#15-🔊-native-windows-audio-volume--media-controls)
16. [⚡ System Health Telemetry & Power Controls](#16-⚡-system-health-telemetry--power-controls)
17. [🎯 High-Efficiency Power-User Workflow Combos](#17-🎯-high-efficiency-power-user-workflow-combos)
18. [🛠️ Troubleshooting, Audio Ducking & Fallback Lifecycles](#18-🛠️-troubleshooting-audio-ducking--fallback-lifecycles)

---

## 1. Architectural Overview & Operating Principles

MakiAI operates as a zero-latency desktop operating intelligence. Every request passes through an intelligent multi-layer cascade:

```
                  ┌──────────────────────────────┐
                  │ Voice (PTT/Wake) / Chat Input│
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ 1. Kiro Coding Engine │ ── (t=kiro, "code with kiro")
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ 2. Project Plan Engine│ ── (11-Stage MunchBite Flow)
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ 3. Homework Follow-up │ ── (Temp-Guide .docx Flow)
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ 4. KB Skills Router   │ ── (Memory, Deadlines, Reminders,
                     └───────────┬───────────┘     Hello, GoodMorning, GoodNight)
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ 5. Computer Router    │ ── (Apps, Windows, Profiles, Files,
                     └───────────┬───────────┘     Vision, Camera, Volume, Power)
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ 6. LLM General Fallback│── (Groq GPT-OSS / Gemini Flash
                     └───────────────────────┘     + Dynamic KB & Memory Context)
```

### Core Operating Rules:
- **Speech Style**: Warm, professional, polite, addresses you as **"sir"**, speaks in natural conversational sentences (never robotic bullet lists when speaking aloud).
- **Zero Hallucination Policy**: Never invents URLs, social links, or portfolio paths. Only quotes exact links from your Knowledge Base (`C:\Knowledge-Base\`).
- **Live State Awareness**: Injects real-time system clock (PHT, UTC+8), active workflow blocks, hardware health, and stored memories into every AI query.
- **Audio Ducking**: Automatically drops background Windows media volume by 70% whenever Maki speaks or listens, restoring full volume upon completion.

---

## 2. Input Channels & Interaction Modes

| Channel | Trigger / Action | When to Use |
| :--- | :--- | :--- |
| **Push-to-Talk (PTT)** | Hold **`Right Alt`** key ➔ speak ➔ release key. | Best for coding sessions, mechanical keyboards, gaming, or noisy environments. Eliminates wake-word delays. |
| **Hands-Free Wake Word** | Say **`"Hey Maki, [command]"`** or direct command. | Best for desk check-ins, walking around the room, or hands-free cooking/studying. |
| **Desktop Chat UI** | Type into the desktop interface and press **`Enter`**. | Best for complex prompts, pasting URLs, silent late-night typing, or inspecting formatted code. |

---

## 3. Daily Workflow Routines & Live Clock Briefings

Maki synchronizes with your `workflows/time-management.md`, `workflows/daily.md`, `workflows/deadlines.md`, and active saved memories.

---

### ☀️ 1. Morning Briefing (`GoodMorningSkill`)
* **Triggers**: `good morning`, `morning briefing`, `what's my schedule today`, `show me my schedule`
* **Sample Prompts**:
  - `"Hey Maki, good morning!"`
  - `"Good morning Maki, what does my schedule look like today?"`
  - `"Give me my morning briefing and any upcoming tasks."`
  - `"Show me my schedule for today."`
  - `"Morning briefing, sir."`
* **Expected Output**:
  - Greeting with today's day, date, and live clock time.
  - Current morning block and entire daily schedule narrated in natural sentences.
  - Any carryover tasks from yesterday or confirmation that everything is clear.
  - Urgent deadlines or scheduled meetings from Long-Term Memory.
  - Polite prompt: *"Is there anything you would like to add to your day, sir?"*

---

### ⏱️ 2. Real-Time Check-In & Live Clock (`HelloSkill`)
* **Triggers**: `hello`, `hey`, `hi`, `what's next`, `what should i do`, `what time is it`, `current time`, `check-in`
* **Sample Prompts**:
  - `"Hey Maki, hello!"`
  - `"What should I be doing right now?"`
  - `"What time is it right now?"`
  - `"What's the current time in Philippine Standard Time?"`
  - `"What's next on our schedule?"`
  - `"Quick check-in, Maki."`
* **Expected Output**:
  - Exact live clock time (`02:30 PM PHT`).
  - Active time block (e.g., Coding Block, Job-Hunting Block, Study Session).
  - Upcoming transition time and any saved meetings for today.

---

### 🌙 3. Evening Wrap-Up (`GoodNightSkill`)
* **Triggers**: `good night`, `wrap up my day`, `end of the day`, `day wrap up`
* **Sample Prompts**:
  - `"Hey Maki, good night."`
  - `"Let's wrap up my day."`
  - `"End of the day check-in."`
  - `"Day wrap up, Maki."`
* **Expected Output**:
  - Review of today's accomplishments.
  - Logging of any unfinished tasks to `workflows/carryover.md` for tomorrow.
  - Review of tomorrow's starting schedule and restful sign-off.

---

## 4. Long-Term Memory & Active Notes (`data/memory.json`)

Maki persists facts, dates, Wi-Fi keys, personal preferences, and spontaneous reminders across app restarts and reboots.

---

### 🧠 Storing Memories
* **Triggers**: `remember that`, `remember this`, `remember my`, `remember our`, `don't forget`
* **Sample Prompts**:
  - `"Hey Maki, remember that we have a Zoom meeting today at 8:00 PM."`
  - `"Remember that tomorrow at 1:00 PM we have an urgent deadline for the AI Ad Video."`
  - `"Don't forget that the studio Wi-Fi password is StudioSecure2026."`
  - `"Remember that my preferred coffee is Iced Americano with oat milk."`
  - `"Remember that my client John wants the Figma wireframes by Wednesday."`
  - `"Remember this: my GitHub token expires on November 30."`
* **What Happens**:
  - Stored in `data/memory.json`.
  - Injects into LLM background prompt immediately.
  - Automatically mentioned during `"Hello"` and `"Good Morning"` briefings!

---

### 🔍 Recalling Memories & Conversational Questions
* **Triggers**: `what do you remember`, `recall`, `do you recall`, `what did i tell you`, or direct conversational queries
* **Sample Prompts**:
  - `"Hey Maki, what do you remember?"`
  - `"Do we have a Zoom meeting today?"`
  - `"Do we have any deadlines scheduled for tomorrow?"`
  - `"Do you recall what I told you about the studio Wi-Fi?"`
  - `"What did I tell you about my coffee preference?"`
  - `"What meetings do I have scheduled for tonight?"`
* **Expected Output**:
  - Direct, natural confirmation of the saved details.

---

### 🗑️ Forgetting & Removing Memories
* **Triggers**: `forget`, `forget about`, `delete memory`, `remove memory`, `clear memories`
* **Sample Prompts**:
  - `"Forget about the AI Ad Video as it is extended."`
  - `"Remove the Canva Poster deadline."`
  - `"Forget that note about the Wi-Fi password."`
  - `"Delete memory regarding the client Figma wireframes."`
  - `"Forget about the Zoom meeting."`
* **What Happens**:
  - Matches the key or description directly and removes it from `data/memory.json`.
  - Invalidates prompt cache so it disappears from all future check-ins.

---

## 5. Deadlines & Task Management (`workflows/deadlines.md`)

Structured deadline tracking categorized with visual urgency indicators:
- 🔴 **Overdue**
- 🚨 **Due Today**
- 🟠 **Due Tomorrow**
- 🟡 **Due within 3 Days**
- ⚪ **Due within 7 Days**

---

### ➕ 1. Adding Deadlines
* **Triggers**: `add deadline`, `set deadline`, `new deadline`, `add a deadline`
* **Sample Prompts**:
  - `"Add a deadline: Machine Learning Final Project due this Friday at 11:59 PM."`
  - `"Set a deadline: Submit Upwork Freelance Proposal by tomorrow 5:00 PM."`
  - `"New deadline: Submit Capstone Documentation due September 20 at 6:00 PM."`
  - `"Add deadline: Pay Internet Bill by September 15."`

---

### 📋 2. Viewing Deadlines
* **Triggers**: `show my deadlines`, `list deadlines`, `what are my deadlines`, `check deadlines`, `deadlines`
* **Sample Prompts**:
  - `"Hey Maki, show my deadlines."`
  - `"What are my pending deadlines?"`
  - `"List all deadlines."`
  - `"Check my upcoming deadlines for this week."`

---

### ✅ 3. Marking Deadlines Complete
* **Triggers**: `deadline done`, `mark deadline complete`, `complete deadline`, `finish deadline`
* **Sample Prompts**:
  - `"Deadline done: Machine Learning Final Project."`
  - `"Mark deadline complete for Upwork proposal."`
  - `"Complete deadline: Pay Internet Bill."`

---

## 6. Timed Reminders & Audio Alarms (`data/reminders.json`)

Maki runs a background timer daemon that triggers audible voice notifications even if you are working in another app.

---

### ⏰ Setting Reminders
* **Triggers**: `remind me at`, `remind me in`, `remind me to`, `set a reminder`
* **Sample Prompts**:
  - `"Remind me in 25 minutes to take a short break."`
  - `"Remind me at 4:30 PM to commit my code to GitHub."`
  - `"Set a reminder in 10 minutes to check the oven."`
  - `"Remind me at 7:45 PM to get ready for the Zoom meeting."`
  - `"Remind me in 1 hour to drink water and stretch."`

---

### 📋 Managing Reminders
* **Triggers**: `show my reminders`, `list reminders`, `cancel reminder`
* **Sample Prompts**:
  - `"Show my active reminders."`
  - `"List all reminders."`
  - `"Cancel reminder for drink water."`
  - `"Cancel reminder for commit code."`

---

## 7. ⚡ Kiro CLI Autonomous Coding Engine (`t=kiro`)

Maki connects directly to your authenticated local **Kiro CLI** (`kiro-cli.exe`) to autonomously plan, scaffold, and code software in your project workspaces.

---

### 🖥️ Mode A: Interactive Visible Terminal Window
*Opens a visible, dedicated PowerShell window running Kiro CLI in your target project directory (`C:\Users\Maki Liones\MakiSync Storage\Personal\<ProjectName>\`).*

* **Sample Prompts**:
  - `"Open Kiro"`
  - `"Launch Kiro terminal"`
  - `"Open Kiro for TaskMaster"`
  - `"Launch Kiro in terminal to build TaskMaster"`
  - `"Start interactive Kiro terminal for MunchBite"`
  - `"Launch Kiro terminal for stage 2 of TaskMaster"`

---

### 🤖 Mode B: Headless Background Code Generation
*Directly executes Kiro CLI in headless automated mode (`--no-interactive --trust-all-tools`) with full Knowledge Base context injection.*

* **Command Syntax**: `t=kiro [instruction]` or `use kiro to [instruction]` or `code with kiro [instruction]`
* **Sample Full-Stack Prompts**:
  - `"t=kiro build a complete single-file task management website called taskmaster.html with sleek glassmorphic dark mode, smooth drag-and-drop, and localStorage persistence."`
  - `"use kiro to write a Python script for automated web scraping with BeautifulSoup that extracts article titles and saves them to a CSV file."`
  - `"kiro code a FastAPI backend with JWT authentication, password hashing, and SQLite user storage."`
  - `"code with kiro: create a modern responsive React counter component styled with Tailwind CSS and Framer Motion animations."`
  - `"ask kiro to write a Dockerfile and docker-compose.yml configuration for a Node.js Express server connected to PostgreSQL and Redis."`
  - `"t=kiro generate a Next.js 15 App Router landing page with hero banner, pricing cards, and testimonials using Tailwind CSS."`

---

## 8. 🏗️ 11-Stage Knowledge Base Project Pipeline

MakiAI guides software ideas through an **11-Stage Planning Pipeline** following your Knowledge Base architecture standards (`MunchBite` template):
`overview.md` ➔ `plan.md` ➔ `architecture.md` ➔ `filepath.md` ➔ `decisions.md` ➔ `progress.md` ➔ `ui.md`.

```
Stage 1: Idea Inception & Core Problem
Stage 2: Target Audience & User Stories
Stage 3: Tech Stack & Architecture Selection
Stage 4: Database Schema & Entity Relationships
Stage 5: Folder & File Structure (filepath.md)
Stage 6: API Endpoints & Route Definitions
Stage 7: UI Wireframe & Component Breakdown (ui.md)
Stage 8: State Management & Data Flow
Stage 9: Step-by-Step Implementation Roadmap (plan.md)
Stage 10: Architectural Decisions & Trade-offs (decisions.md)
Stage 11: Active Progress & Scaffolding Execution (progress.md)
```

### 🚀 Starting and Driving a Project
* **Triggers**: `new project`, `start project`, `i have a project idea`, `let's build`
* **Sample Prompts**:
  - `"I have a new project idea: a modern freelance portfolio website."`
  - `"Let's build a real-time collaborative whiteboard web app."`
  - `"Start a new project called TaskMaster."`
  - `"I want to build an AI meal planning platform using Next.js and Supabase."`
  - `"What is the current plan for TaskMaster?"`
  - `"Continue planning TaskMaster for Stage 4."`
  - `"Use Kiro to scaffold the project files based on the TaskMaster plan."`

---

## 9. 📝 Automated Homework & Research Paper Engine (`.docx`)

Generates fully styled Microsoft Word (`.docx`) reports, lab sheets, essays, and assignments following rubrics dropped into `C:\MakiSync Storage\School\Temp-Guide\`.

---

### 🔄 The 2-Step Workflow

#### Step 1: Open Guide Folder
* **Triggers**: `create my homework`, `do my homework`, `make my assignment`, `help with homework`
* **Sample Prompts**:
  - `"Hey Maki, create my homework."`
  - `"Help me with my assignment."`
  - `"Make my homework."`
  - `"Prepare my homework folder."`
* **What Maki Does**:
  - Opens `C:\MakiSync Storage\School\Temp-Guide\` in Windows File Explorer.
  - Prompts you: *"I've opened the Temp-Guide folder for you, sir. Please drop your rubric, syllabus, or template there, then tell me what to write."*

#### Step 2: Drop Rubric & Give Content Prompt
* **Sample Prompts**:
  - `"Write a 3-page research paper on Convolutional Neural Networks based on the rubric in Temp-Guide."`
  - `"Generate my Operating Systems laboratory report answering questions 1 through 5 following the template."`
  - `"Write an essay discussing ethical implications of generative AI following the guide in Temp-Guide."`
* **What Maki Does**:
  - Parses PDF, Word, or Markdown files inside `Temp-Guide`.
  - Generates a formatted `.docx` file inside `C:\MakiSync Storage\School\Assignments\<Date>\`.
  - Automatically launches the document in Microsoft Word.

---

## 10. 📂 MakiSync Storage & Intelligent File Operations

Organized file storage system located at `C:\MakiSync Storage\`:
- `School/` (Assignments, Notes, Temp-Guide)
- `Work/` (Documents, Reports)
- `Personal/` (Projects, Notes)
- `Freelance/` (Proposals, Invoices)
- `MakiAI/` (Screenshots, Photos, Recordings)

---

### 📄 1. Live File Creation & Script Writing
* **Sample Prompts**:
  - `"Create a file called index.html with a sleek dark-mode landing page in my Personal folder."`
  - `"Create a Python script named backup_sync.py in my School folder that automates folder compression."`
  - `"Write a notes document for Machine Learning exam review in my School folder."`
  - `"Create a file named styles.css with modern glassmorphism utility classes."`
  - `"Write a story about space exploration into story.txt in my Personal folder."`
  - `"Append this note to my last document: test all endpoints before deployment."`

---

### 🔍 2. Finding & Opening Recent Files
* **Sample Prompts**:
  - `"Could you open the last photo you captured in our storage?"`
  - `"Open the last screenshot."`
  - `"Open my photos folder."`
  - `"Open my screenshots folder."`
  - `"Find my recent files in School."`
  - `"Open the last document I created."`
  - `"Show files in my Freelance folder from today."`
  - `"Open my Knowledge Base folder."`
  - `"Open Downloads folder."`

---

### 🧹 3. File Organization & Auto-Sorting
* **Sample Prompts**:
  - `"Organize my Downloads folder."`
  - `"Clean up my Desktop."`
  - `"Sort files in my Documents folder."`

---

## 11. 👁️ Physical Optical Webcam Vision (World Observer)

MakiAI connects to your hardware webcam using OpenCV DirectShow (`CAP_DSHOW`) and multimodal vision AI (`gemini-3.6-flash`).

---

### 📷 Inspecting Physical Reality
* **Triggers**: `look through my camera`, `what do you see`, `describe what i'm holding`, `take a photo`, `who is behind me`
* **Sample Prompts**:
  - `"Hey Maki, look through my camera and tell me what you see."`
  - `"Look through my camera and identify what object is in my hand."`
  - `"Take a photo of me."` *(Snaps photo, saves to MakiSync Storage, and opens immediately)*
  - `"Can you read the text on the book I am holding up to the webcam?"`
  - `"Is there anyone in the background behind me?"`
  - `"Look at me and tell me what I am doing right now."`
  - `"Check the camera and tell me if my lighting is good for a video call."`
  - `"Describe what I am wearing today."`

---

## 12. 🖥️ Live Screen Vision & Visual Error Debugging

MakiAI takes high-resolution desktop screenshots and inspects code errors, UI layouts, terminal stack traces, or active browser tabs.

---

### 🔍 Screen OCR & Code Debugging
* **Triggers**: `look at my screen`, `what is on my screen`, `debug this error`, `take a screenshot`, `read my screen`
* **Sample Prompts**:
  - `"Hey Maki, look at my screen and help me debug this terminal error."`
  - `"What is currently displayed on my screen?"`
  - `"Take a screenshot."` *(Captures screen, saves to MakiSync Storage, and opens immediately)*
  - `"Take a screenshot of the active window."`
  - `"Look at this code on my screen and explain what is causing the runtime exception."`
  - `"Read the error message visible in my VS Code terminal."`
  - `"Look at my screen and give me feedback on the UI layout of this webpage."`
  - `"Summarize the document open on my screen."`

---

## 13. 🪟 Multi-Monitor Window Management & Auto-Tiling

MakiAI detects physical display coordinates and snaps, tiles, or shifts application windows across monitors.

---

### 🪟 1. Inter-Monitor Window Moving & Dragging
* **Sample Prompts**:
  - `"Move Chrome to my second monitor."`
  - `"Move VS Code to my main monitor."`
  - `"Drag this window to monitor 2."`
  - `"Shift Spotify to the other monitor."`
  - `"Put Chrome on the left screen."`
  - `"Move Discord to my secondary display."`

---

### 📐 2. Auto-Tiling & Workspace Layouts
* **Sample Prompts**:
  - `"Tile my windows."`
  - `"Tile Chrome and VS Code side by side."`
  - `"Organize my workspace."`
  - `"Maximize screens across my 2 monitors."`
  - `"Fit all active windows across my displays."`
  - `"Maximize the active window."`
  - `"Minimize all windows."`

---

## 14. 🌐 Chrome Multi-Profile Site Launcher

Opens web applications and platforms directly inside dedicated Google Chrome user profiles:
- **Personal Profile** (`Default`) ➔ YouTube, Facebook, Instagram, Netflix, Reddit, Spotify
- **School Profile** (`Profile 1`) ➔ Google Drive, Canvas, School Portal, GitHub School
- **Freelance Profile** (`Profile 2`) ➔ Upwork, Fiverr, Figma, Canva, LinkedIn
- **Work Profile** (`Profile 3`) ➔ Google Docs, Slack, Jira, Company Mail

---

### 🌐 Profile Browsing Commands
* **Sample Prompts**:
  - `"Open YouTube in my Personal profile."`
  - `"Open GitHub in my School profile."`
  - `"Open Figma in my Freelance profile."`
  - `"Open Google Docs in my Work profile."`
  - `"Open Upwork."`
  - `"Open Canva."`
  - `"Open Facebook."`
  - `"Open ChatGPT."`
  - `"Open Gemini."`

---

## 15. 🔊 Native Windows Audio, Volume & Media Controls

Direct hardware audio management with volume ducking and Spotify integration.

---

### 🔊 1. Volume Controls
* **Sample Prompts**:
  - `"Volume up"` / `"Make it louder"`
  - `"Volume down"` / `"Make it quieter"`
  - `"Increase volume by 20%"`
  - `"Decrease volume by 15%"`
  - `"Set volume to 50%"`
  - `"Turn volume to 80%"`
  - `"Max volume"` / `"Turn volume all the way up"`
  - `"Mute audio"` / `"Unmute"`

---

### 🎵 2. Media Playback & Spotify
* **Sample Prompts**:
  - `"Open Spotify."` *(Launches Spotify application)*
  - `"Play"` / `"Pause"` / `"Resume music"`
  - `"Next track"` / `"Skip song"`
  - `"Previous song"` / `"Previous track"`
  - `"Play synthwave on Spotify."`
  - `"Play lofi hip hop on Spotify."`

---

## 16. ⚡ System Health Telemetry & Power Controls

Monitors CPU usage, RAM utilization, temperature thresholds, and system power states.

---

### 📊 1. Hardware Vitals & Telemetry
* **Sample Prompts**:
  - `"How is my system health?"`
  - `"What are my system vitals?"`
  - `"What is my CPU and RAM usage right now?"`
  - `"How is my battery?"`
  - `"Is my laptop charging?"`
  - `"Check hardware status."`

---

### 🔒 2. System Power & Security
* **Sample Prompts**:
  - `"Lock PC"` / `"Lock my computer"`
  - `"Put computer to sleep"` / `"Sleep"`
  - `"Restart my PC"`
  - `"Shutdown computer"` *(Requires voice confirmation)*
  - `"Cancel shutdown"`
  - `"Brightness up"` / `"Increase brightness"`
  - `"Brightness down"` / `"Lower brightness"`
  - `"Set brightness to 70%"`

---

## 17. 🎯 High-Efficiency Power-User Workflow Combos

Combine multiple features together for maximum productivity:

### 💼 Scenario 1: The Morning Kickoff
1. **Start**: *"Good morning Maki"* ➔ Hear schedule, weather, and active notes.
2. **Setup**: *"Tile VS Code and Chrome across my monitors"* ➔ Windows arrange automatically.
3. **Music**: *"Play focus lofi on Spotify"* ➔ Music starts with automatic ducking.
4. **Plan**: *"What is the current plan for TaskMaster?"* ➔ Review active project phase.

---

### 💻 Scenario 2: Autonomous Coding Session
1. **Instruction**: *"t=kiro build a responsive Next.js pricing page with Stripe checkout cards"* ➔ Kiro builds code in background.
2. **Review**: *"Open Kiro for TaskMaster"* ➔ Visible terminal opens to watch progress.
3. **Debug**: *"Look at my screen and debug this terminal error"* ➔ Maki analyzes error and gives instant fix.

---

### 📚 Scenario 3: Homework & Research Rush
1. **Setup**: *"Create my homework"* ➔ `Temp-Guide` folder opens.
2. **Drop**: Drop assignment rubric into `Temp-Guide`.
3. **Generate**: *"Write a 3-page research paper on Transformers based on the guide in Temp-Guide"* ➔ Formatted `.docx` is created and launched in Word.
4. **Deadline**: *"Add deadline: Submit AI Paper by 11:59 PM tonight"* ➔ Logged to deadlines tracker.

---

### 📸 Scenario 4: Photo & Vision Check
1. **Capture**: *"Take a photo of me"* ➔ Snaps photo, saves to MakiSync, opens photo immediately.
2. **Inspect**: *"Look through my camera and tell me what I am holding in my hand"* ➔ Vision AI identifies object and reads text.
3. **Retrieve**: *"Could you open the last photo you captured in our storage?"* ➔ Opens photo in default viewer and selects in Explorer.

---

## 18. 🛠️ Troubleshooting, Audio Ducking & Fallback Lifecycles

### 🔄 Multi-Tier Fallback Lifecycle
1. **AI Provider Fallback**: If Groq free tier hits rate limit, Maki automatically hot-swaps to Google Gemini (`gemini-3.6-flash`) seamlessly.
2. **TTS Audio Fallback**: If ElevenLabs quota is exhausted, Maki switches to Microsoft Edge Neural TTS with zero downtime.
3. **Webcam Connection**: OpenCV utilizes `CAP_DSHOW` DirectShow on Windows with device index fallback (`0` ➔ `1` ➔ `2`) and auto-exposure warmup.
4. **Document Formatting**: Word homework generation utilizes `python-docx` with fallback to markdown text formatting.

### 💡 Golden Rules for Perfect Interaction:
- **Clean Voice Capture**: Hold **`Right Alt`** while speaking for 100% clean transcriptions without wake-word false alarms.
- **Natural Phrasing**: You can speak completely naturally. Words like `"please"`, `"could you"`, `"hey"`, and `"maki"` are automatically parsed and stripped by the router.
- **Cache Invalidation**: Whenever you store a memory or add a deadline, it is instantly available across all briefings without restarting the app!

---

## 19. 🌐 Live Web Research, Google Search & URL Reading (Bare Research)

MakiAI features a zero-dependency, multi-tier web research engine powered by standard Python and free API fallbacks (`Tavily → Serper (Google) → Exa → DuckDuckGo`):

### 🔍 Live Web Searches
Ask Maki to search the live web for breaking news, developer documentation, sport scores, or facts:
* *"Search for the latest Next.js 15 breaking changes."*
* *"Google who won the NBA game last night."*
* *"Research best practices for Supabase row level security."*
* *"Look up how to configure Tailwind CSS with Vite."*
* *"Find information about the newest Groq Whisper models."*

### 📄 Reading & Summarizing Web Pages / Documentation Links
Give Maki any URL to read and extract its content without ads or popups:
* *"Read this link: https://github.com/paulablaza/bare-research and tell me what it does."*
* *"Summarize this article: https://news.ycombinator.com/item?id=12345"*
* *"Check https://fastapi.tiangolo.com/tutorial/security/ and explain how OAuth2 works."*

### ⚡ Free & Automatic Resilience:
* **Zero Keys Needed**: If no API keys are provided in `.env`, Maki automatically uses the built-in DuckDuckGo search and standard library HTML extractor for 100% free operation.
* **Optional Superchargers**: If `TAVILY_API_KEY`, `SERPER_API_KEY`, or `FIRECRAWL_API_KEY` are provided in `.env`, Maki will automatically prioritize them for lightning-fast AI summaries.

---

## 20. 🎬 AI Video Clipping & Viral Shorts Creation (DeepClip)

MakiAI features an autonomous video moment finder and auto-cutter powered by transcript virality analysis and FFmpeg layout filters:

### 📹 Viral Shorts from YouTube Videos
Feed Maki any YouTube URL and have it extract the highest-engagement moments into 9:16 vertical shorts:
* *"Find 3 clips from https://www.youtube.com/watch?v=..."*
* *"Create 5 viral shorts from https://youtu.be/..."*
* *"Clip the best moments from this YouTube link: https://... in landscape format."*

### 🖥️ Clipping Your Local Screen Recordings
Extract the punchy highlights and delete dead air from your local screen recordings or tutorials:
* *"Clip the viral moments from my latest recording in MakiSync."*
* *"Make 3 vertical shorts from my latest screen recording."*
* *"Clip the best moments from C:\MakiSync Storage\MakiAI\Recordings\2026-09-13\demo.mp4"*

### 🎨 Available Output Layouts:
* **`vertical-blur` (Default)**: 9:16 vertical 1080x1920 with blurred background fill (optimized for **TikTok, YouTube Shorts, Instagram Reels**).
* **`vertical-black`**: 9:16 vertical with clean black letterboxing.
* **`landscape`**: 16:9 native direct slice.

### 📁 Automatic Storage & Auto-Open:
All generated clips are automatically saved to:
`C:\MakiSync Storage\MakiAI\Clips\YYYY-MM-DD\<index>_<Title>.mp4`
Maki automatically opens the Clips folder in Windows Explorer the instant the render is complete!

---

*MakiAI — Built for speed, precision, and complete autonomous operating assistance.* 🚀


