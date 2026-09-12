# MakiAI — Master Prompting & Command Guide 🎙️⚡

> **Welcome to the MakiAI Mastery Guide.**  
> This comprehensive manual details every voice and text interaction mode, keyword trigger, conversational prompt, and advanced workflow available in MakiAI.

---

## 📑 Table of Contents
1. [Interaction Modes & Hotkeys](#1-interaction-modes--hotkeys)
2. [Daily Routines, Live Clock & Briefings](#2-daily-routines-live-clock--briefings)
3. [Long-Term Memory & Active Notes](#3-long-term-memory--active-notes)
4. [Deadlines & Task Management](#4-deadlines--task-management)
5. [Timed Reminders & Alarms](#5-timed-reminders--alarms)
6. [Kiro CLI Coding Engine (`t=kiro`)](#6-kiro-cli-coding-engine-tkiro)
7. [11-Stage Knowledge Base Project Pipeline](#7-11-stage-knowledge-base-project-pipeline)
8. [Automated Homework & Research Paper Engine](#8-automated-homework--research-paper-engine)
9. [Live File Creation & MakiSync Storage](#9-live-file-creation--makisync-storage)
10. [Physical Webcam Vision (World Observer)](#10-physical-webcam-vision-world-observer)
11. [Screen Vision & Visual Error Debugging](#11-screen-vision--visual-error-debugging)
12. [Multi-Monitor Window Auto-Tiling & Management](#12-multi-monitor-window-auto-tiling--management)
13. [Chrome Multi-Profile Site Launcher](#13-chrome-multi-profile-site-launcher)
14. [Native Windows Audio, Volume & Media Controls](#14-native-windows-audio-volume--media-controls)
15. [System Health, Telemetry & Power Controls](#15-system-health-telemetry--power-controls)
16. [Master Prompting Best Practices & Tips](#16-master-prompting-best-practices--tips)

---

## 1. Interaction Modes & Hotkeys

MakiAI can be controlled via three simultaneous input channels:

| Method | How to Use | Ideal For |
| :--- | :--- | :--- |
| **Push-to-Talk (PTT)** | Hold **`Right Alt`** key, speak naturally, release when done. | Fast, noise-free voice execution without saying wake words. |
| **Wake Word** | Say **`"Hey Maki, [command]"`** from anywhere in the room. | Hands-free commands while coding, reading, or away from desk. |
| **Desktop Chat UI** | Type your instruction into the input bar and press **`Enter`**. | Complex code prompts, pasting URLs, or silent typing. |

---

## 2. Daily Routines, Live Clock & Briefings

MakiAI has real-time clock synchronization (Philippine Standard Time, UTC+8) and reads your Knowledge Base schedule files (`workflows/time-management.md`, `workflows/daily.md`, `workflows/deadlines.md`, and saved memories).

### ☀️ Morning Briefing (`GoodMorningSkill`)
* **Trigger Keywords**: `good morning`, `morning briefing`, `what's my schedule today`, `show me my schedule`
* **Sample Prompts**:
  - `"Hey Maki, good morning!"`
  - `"Good morning Maki, what does my schedule look like today?"`
  - `"Give me my morning briefing."`
  - `"What's on my agenda for today?"`
* **What Maki Returns**:
  - Warm greeting with today's date & live clock time.
  - Active time block and upcoming scheduled activities.
  - Any urgent deadlines or saved meetings/notes scheduled for the day.
  - Encouraging closing thought.

---

### ⏱️ Quick Check-In & Real-Time Clock (`HelloSkill`)
* **Trigger Keywords**: `hello`, `hey`, `hi`, `what's next`, `what should i do`, `what time is it`, `current time`, `check-in`
* **Sample Prompts**:
  - `"Hey Maki, hello!"`
  - `"What should I be doing right now?"`
  - `"Hey Maki, what's the current time?"`
  - `"What's next on our schedule?"`
  - `"Quick check-in, Maki."`
* **What Maki Returns**:
  - Exact live clock time in Philippine Standard Time.
  - Current workflow block (e.g., Coding Block, Job-Hunting Block, Exercise).
  - Next upcoming transition and active notes/meetings for today.

---

### 🌙 Evening Wrap-Up (`GoodNightSkill`)
* **Trigger Keywords**: `good night`, `wrap up my day`, `end of the day`, `day wrap up`
* **Sample Prompts**:
  - `"Hey Maki, good night."`
  - `"Let's wrap up my day, Maki."`
  - `"End of the day check."`
* **What Maki Returns**:
  - Review of completed blocks.
  - Carry-over tasks logged for tomorrow.
  - Acknowledgment of pending deadlines and restful sign-off.

---

## 3. Long-Term Memory & Active Notes

Maki stores persistent key-value memories in `data/memory.json`. All saved memories are automatically injected into Maki's thinking context across sessions, restarts, and check-ins.

### 🧠 Storing Memories
* **Trigger Keywords**: `remember that`, `remember this`, `remember my`, `don't forget`
* **Sample Prompts**:
  - `"Hey Maki, remember that we have a Zoom meeting today at 8:00 PM."`
  - `"Remember that tomorrow at 1:00 PM we have an urgent deadline for the AI Ad Video."`
  - `"Don't forget that my sister's birthday is on October 15."`
  - `"Remember that my preferred coffee order is Iced Americano with oat milk."`
  - `"Remember that the Wi-Fi password for the studio is StudioKey2026."`
* **Expected Response**:
  - *"Got it. I'll remember: Zoom meeting — Zoom meeting today at 8:00 PM."*

---

### 🔍 Recalling Memories & Direct Inquiries
* **Trigger Keywords**: `what do you remember`, `recall`, `do you recall`, `what did i tell you`, or direct questions
* **Sample Prompts**:
  - `"Hey Maki, what do you remember?"`
  - `"Do we have a Zoom meeting today?"`
  - `"What meetings do we have scheduled for tonight?"`
  - `"Do you recall what I told you about tomorrow's deadline?"`
  - `"What is the studio Wi-Fi password?"`
* **Expected Response**:
  - *"Yes sir, you have a Zoom meeting scheduled for today at 8:00 PM, and an urgent deadline for the AI Ad Video tomorrow at 1:00 PM."*

---

### 🗑️ Forgetting Memories
* **Trigger Keywords**: `forget about`, `forget that`, `remove memory`, `delete memory`
* **Sample Prompts**:
  - `"Hey Maki, forget about the Zoom meeting."`
  - `"Forget that note about the Wi-Fi password."`
  - `"Remove the memory regarding the AI Ad Video."`
* **Expected Response**:
  - *"Done. I've forgotten: Zoom meeting."*

---

## 4. Deadlines & Task Management

Tracks deadlines in `C:\Knowledge-Base\workflows\deadlines.md` with priority markers (🔴 Overdue, 🚨 Today, 🟠 Tomorrow, 🟡 3 Days).

### ➕ Adding Deadlines
* **Trigger Keywords**: `add deadline`, `add a deadline`, `set deadline`, `new deadline`
* **Sample Prompts**:
  - `"Add a deadline: Machine Learning Final Project due this Friday at 11:59 PM."`
  - `"Set a deadline: Submit Upwork Freelance Proposal by tomorrow 5:00 PM."`
  - `"New deadline: Capstone documentation review due September 18."`
* **Expected Response**:
  - Updates `workflows/deadlines.md` and confirms: *"I've added the Machine Learning Final Project deadline for Friday at 11:59 PM, sir."*

---

### 📋 Viewing Deadlines
* **Trigger Keywords**: `show my deadlines`, `list deadlines`, `what are my deadlines`, `check deadlines`, `deadlines`
* **Sample Prompts**:
  - `"Hey Maki, show my deadlines."`
  - `"What are my pending deadlines?"`
  - `"List all deadlines."`
* **Expected Response**:
  - Summarizes pending items grouped by urgency.

---

### ✅ Completing Deadlines
* **Trigger Keywords**: `deadline done`, `mark deadline complete`, `finish deadline`
* **Sample Prompts**:
  - `"Deadline done: Machine Learning Final Project."`
  - `"Mark deadline complete for Upwork proposal."`
* **Expected Response**:
  - Moves entry from `## Pending` to `## Completed` in `workflows/deadlines.md`.

---

## 5. Timed Reminders & Alarms

Schedules real-time background timers and audible voice notifications.

### ⏰ Setting Reminders
* **Trigger Keywords**: `remind me at`, `remind me in`, `remind me to`, `set a reminder`
* **Sample Prompts**:
  - `"Remind me in 25 minutes to take a break."`
  - `"Remind me at 4:30 PM to submit my daily git commit."`
  - `"Set a reminder in 10 minutes to drink water."`
  - `"Remind me at 7:45 PM to prepare for the Zoom call."`

---

### 📋 Viewing & Cancelling Reminders
* **Sample Prompts**:
  - `"Show my active reminders."`
  - `"List reminders."`
  - `"Cancel reminder for drink water."`

---

## 6. Kiro CLI Coding Engine (`t=kiro`)

Maki connects directly to your authenticated **Kiro CLI** to generate complete codebases, scaffold full apps, and write production code.

### 🖥️ Mode A: Interactive Visible Terminal
*Launches a visible, live PowerShell terminal with Kiro CLI active in your project directory.*
* **Sample Prompts**:
  - `"Open Kiro"`
  - `"Launch Kiro terminal"`
  - `"Open Kiro for TaskMaster"`
  - `"Start interactive Kiro terminal to build TaskMaster"`

---

### 🤖 Mode B: Headless Direct Code Generation
*Directly triggers Kiro in the background using `--no-interactive --trust-all-tools`.*
* **Prefix Tag**: `t=kiro [instruction]` or `use kiro to [instruction]`
* **Sample Prompts**:
  - `"t=kiro build a single-file modern landing page called portfolio.html with dark mode, glowing accents, and smooth scroll animations."`
  - `"use kiro to write a Python FastAPI CRUD backend with SQLite and JWT authentication."`
  - `"kiro code a responsive React dashboard component using Tailwind CSS and Chart.js."`
  - `"code with kiro: create an automated script that organizes files in my Downloads folder by extension."`
  - `"ask kiro to write a complete Dockerfile and docker-compose setup for a Next.js 15 app with Postgres."`

---

## 7. 11-Stage Knowledge Base Project Pipeline

MakiAI guides software ideas through an **11-Stage Planning Pipeline** following your Knowledge Base architecture standards (`MunchBite` template):
`overview.md` ➔ `plan.md` ➔ `architecture.md` ➔ `filepath.md` ➔ `decisions.md` ➔ `progress.md` ➔ `ui.md`.

### 🚀 Initiating a Project
* **Trigger Keywords**: `new project`, `start project`, `i have a project idea`, `let's build`
* **Sample Prompts**:
  - `"I have a new project idea: a freelance client invoice generator."`
  - `"Let's build a real-time collaborative whiteboard app."`
  - `"Start a new project called StudyFlow."`
  - `"I want to build an AI meal planning web app using Next.js and Supabase."`

### 🔄 Project Planning Workflow:
1. **Stage 1**: Maki outlines Project Name, Target Audience, Core Problem, and Platform.
2. **Interactive Clarifications**: You answer or refine details.
3. **KB Sync**: Maki creates the structured folder under `C:\Knowledge-Base\projects\<ProjectName>\`.
4. **Execution Delegation**: Hand off the plan to Kiro CLI to scaffold and code the application.

---

## 8. Automated Homework & Research Paper Engine

Automates academic paper formatting and document generation following templates in `C:\MakiSync Storage\School\Temp-Guide\`.

### 📝 Two-Step Workflow

#### Step 1: Open the Guide Folder
* **Trigger Keywords**: `create my homework`, `do my homework`, `make my assignment`, `help with homework`
* **Sample Prompts**:
  - `"Hey Maki, create my homework."`
  - `"Help me with my assignment."`
  - `"Make my homework."`
* **What Maki Does**:
  - Opens `C:\MakiSync Storage\School\Temp-Guide\` in Windows File Explorer.
  - Tells you: *"I've opened the Temp-Guide folder for you, sir. Please drop your rubric, syllabus, or template there, then tell me what to write."*

#### Step 2: Give Instructions & Generate `.docx`
* **Sample Prompts**:
  - `"Write a 3-page research report on Convolutional Neural Networks following the rubric in Temp-Guide."`
  - `"Generate my Operating Systems lab report answering questions 1 to 5 based on the guide."`
  - `"Write an essay discussing ethical implications of generative AI following the template."`
* **What Maki Does**:
  - Reads PDF/Word/Text guides from `Temp-Guide`.
  - Generates a styled `.docx` document in `C:\MakiSync Storage\School\Assignments\<Date>\`.
  - Automatically opens the document in Microsoft Word.

---

## 9. Live File Creation & MakiSync Storage

Create files, write scripts, and organize documents directly inside your structured `C:\MakiSync Storage\` filesystem (`School\`, `Work\`, `Personal\`, `Freelance\`).

### 📄 Creating Files & Scripts
* **Sample Prompts**:
  - `"Create a file called index.html with a sleek dark-mode landing page in my Personal folder."`
  - `"Create a Python script named backup_sync.py in my School folder that automates folder compression."`
  - `"Write a notes document for Machine Learning exam review in my School folder."`
  - `"Create a file named styles.css with modern glassmorphism utility classes."`

---

### 📂 File Search & Recency Navigation
* **Sample Prompts**:
  - `"Find my recent files in School."`
  - `"Open the last document I created."`
  - `"Show files in my Freelance folder from this week."`

---

## 10. Physical Webcam Vision (World Observer)

MakiAI connects to your hardware webcam using OpenCV (`CAP_DSHOW`) and multimodal vision AI (`gemini-3.6-flash`).

### 📷 Inspecting Objects in Real-Time
* **Trigger Keywords**: `look through my camera`, `what do you see`, `describe what i'm holding`, `take a photo`
* **Sample Prompts**:
  - `"Hey Maki, look through my camera and tell me what you see."`
  - `"Look through my camera and identify what I am holding in my hand."`
  - `"Take a photo and describe the scene in front of me."`
  - `"Can you read the text on the book I am holding up to the webcam?"`
  - `"Look at my camera and tell me if my lighting is good for a video call."`
* **Expected Response**:
  - Captures a frame, analyzes visual elements, and provides a clear spoken description.

---

## 11. Screen Vision & Visual Error Debugging

MakiAI captures full-resolution desktop screenshots and inspects code errors, UI layouts, or active applications.

### 🖥️ Desktop Analysis & Debugging
* **Trigger Keywords**: `look at my screen`, `what is on my screen`, `debug this error`, `take a screenshot`
* **Sample Prompts**:
  - `"Hey Maki, look at my screen and help me debug this terminal error."`
  - `"What's currently displayed on my screen?"`
  - `"Take a screenshot and save it to my MakiSync folder."`
  - `"Look at my screen and review the design of this web page."`
  - `"Read the error message visible in my VS Code window."`

---

## 12. Multi-Monitor Window Auto-Tiling & Management

MakiAI detects physical display coordinates and snaps, tiles, or shifts application windows across monitors.

### 🪟 Window Control Commands
* **Sample Prompts**:
  - `"Snap VS Code to the left side of my main monitor."`
  - `"Move Chrome to my secondary monitor."`
  - `"Tile VS Code and Chrome side by side."`
  - `"Maximize the active window."`
  - `"Minimize all windows."`

---

## 13. Chrome Multi-Profile Site Launcher

Opens URLs and web applications inside specific Google Chrome user profiles.

### 🌐 Profile-Aware Browsing
* **Sample Prompts**:
  - `"Open YouTube in my Personal profile."`
  - `"Open GitHub in my School profile."`
  - `"Open Figma in my Freelance profile."`
  - `"Open Google Docs in my Work profile."`
  - `"Open ChatGPT."`

---

## 14. Native Windows Audio, Volume & Media Controls

Direct hardware audio management with volume ducking and Spotify/media integration.

### 🔊 Volume & Sound
* **Sample Prompts**:
  - `"Volume up"` / `"Turn the volume up by 20%"`
  - `"Volume down"` / `"Turn it down a bit"`
  - `"Mute audio"` / `"Unmute"`
  - `"Set volume to 50%"`

---

### 🎵 Media Playback
* **Sample Prompts**:
  - `"Play"` / `"Pause"`
  - `"Next track"` / `"Skip song"`
  - `"Previous song"`
  - `"Open Spotify"`

---

## 15. System Health, Telemetry & Power Controls

Monitors CPU usage, RAM utilization, temperature thresholds, and system power states.

### ⚡ System Status
* **Sample Prompts**:
  - `"How is my system health?"`
  - `"What is my CPU and RAM usage right now?"`
  - `"Check hardware telemetry."`

---

### 🔒 Power & Security
* **Sample Prompts**:
  - `"Lock PC"` / `"Lock my computer"`
  - `"Put computer to sleep"`
  - `"Restart my PC"`
  - `"Shutdown computer"` *(Requires voice confirmation)*

---

## 16. Master Prompting Best Practices & Tips

To get the highest accuracy and most natural responses from MakiAI, keep these best practices in mind:

### 💡 Top Tips:
1. **Natural Phrasing**: Speak naturally as if talking to a personal human assistant. Maki understands context, pronouns, and implied references.
2. **Explicit Skill Triggers for Accuracy**:
   - Use `"Remember that [details]"` when you want facts/events stored in long-term memory.
   - Use `"Add a deadline [task] due [date]"` when you want structured tracking in your KB deadlines file.
   - Use `"Remind me in [X minutes]"` when you need an immediate alarm/timer.
   - Use `"t=kiro [prompt]"` when you want autonomous code generation.
3. **Combining Memories & Check-ins**: Once you tell Maki to remember a meeting or task, you don't need to ask specifically about memory—simply saying `"Hello"` or `"What's my schedule?"` will automatically weave that memory into your briefing.
4. **Push-to-Talk (PTT)**: For coding sessions with loud mechanical keyboards or background music, holding **`Right Alt`** guarantees 100% clean voice transcription without false wake word activations.

---

*MakiAI — Your Autonomous AI Operating Assistant.* 🚀
