# MakiAI — Complete Feature & Prompt Testing Guide 🚀

This testing guide provides a comprehensive list of all features, capabilities, and exact sample voice/text prompts built into **MakiAI**.

You can test these commands by:
1. **Push-to-Talk (PTT)**: Hold the **`Right Alt`** key while speaking, then release to execute.
2. **Wake Word**: Say **`"Hey Maki, [command]"`** or speak direct commands.
3. **Desktop Chat UI**: Type any command directly into the input bar.
4. **Automated Diagnostic Suite**: Run `python scratch/test_all_commands.py` to test the full 65-command matrix.

---

## Table of Contents
1. [⚡ Kiro CLI Coding Engine (`t=kiro`)](#1--kiro-cli-coding-engine-tkiro)
2. [🏗️ Project Planning & 11-Stage Scaffolding](#2-️-project-planning--11-stage-scaffolding)
3. [📅 Real-Time Daily Schedule & Briefings (English & Tagalog)](#3--real-time-daily-schedule--briefings-english--tagalog)
4. [⏳ Deadlines Management (English & Tagalog)](#4--deadlines-management-english--tagalog)
5. [⏰ Reminders, Alarms & Calendar Inquiries](#5--reminders-alarms--calendar-inquiries)
6. [📝 Automated Homework & Research Paper Generation](#6--automated-homework--research-paper-generation)
7. [🔍 Web Research & Live Synthesis](#7--web-research--live-synthesis)
8. [🧠 Long-Term Memory & Personal Preferences](#8--long-term-memory--personal-preferences)
9. [📄 Live File Creation & Generative Code Writing](#9--live-file-creation--generative-code-writing)
10. [🧹 Intelligent File Organization & Search](#10--intelligent-file-organization--search)
11. [👁️ Physical Webcam Vision (World Observer)](#11-️-physical-webcam-vision-world-observer)
12. [🖥️ Screen Vision & Visual Error Debugging](#12-️-screen-vision--visual-error-debugging)
13. [🪟 Multi-Monitor Workspace Auto-Tiling & Dragging](#13--multi-monitor-workspace-auto-tiling--dragging)
14. [🌐 Chrome Multi-Profile Site Launcher](#14--chrome-multi-profile-site-launcher)
15. [🔊 Native Windows Audio, Ducking & Volume Scaling](#15--native-windows-audio-ducking--volume-scaling)
16. [⚡ System Health, Power & Telemetry](#16--system-health-power--telemetry)
17. [🎵 Media Playback Controls](#17--media-playback-controls)
18. [📷 Camera & Screenshot Utilities](#18--camera--screenshot-utilities)

---

## 1. ⚡ Kiro CLI Coding Engine (`t=kiro`)
*MakiAI connects directly to your authenticated local **Kiro CLI** (`kiro-cli.exe` with Claude Sonnet 4.5 / DeepSeek 3.2 / Qwen3 Coder) to autonomously generate code, scaffold projects, and write software.*

### Sample Prompts to Test:
- **Interactive Visible Terminal**:
  - `"Open Kiro"` or `"Launch Kiro terminal"`
  - `"Open Kiro for TaskMaster"`
  - `"Launch Kiro in terminal to build TaskMaster"`
- **Direct Voice/Text Code Generation**:
  - `"t=kiro build a complete single-file task management website called taskmaster.html with dark mode and localStorage saving"`
  - `"use kiro to write a python script for automated web scraping with BeautifulSoup"`
  - `"kiro code a FastAPI authentication backend with JWT tokens"`
  - `"code with kiro: create a responsive React counter component with Tailwind"`
  - `"ask kiro to write a Dockerfile and docker-compose setup for Node.js and PostgreSQL"`

### Expected Behavior:
- **Interactive Mode**: Automatically opens a new, visible PowerShell window with Kiro CLI running in your project directory (`C:\development\NextJS\TaskMaster\`) so you can watch Kiro code live.
- **Headless Mode**: Executes in background mode (`--no-interactive --trust-all-tools`) and outputs the generated code directly in the MakiAI chat.

---

## 2. 🏗️ Project Planning & 11-Stage Scaffolding
*MakiAI reads your Knowledge Base coding standards (`config/coding-standards.md`, `web-development/architecture.md`, `folder-structure.md`) and kicks off the official 11-stage project planning lifecycle.*

### Sample Prompts to Test:
- `"I have a new project idea called FitTrack"`
- `"May bago akong project na naisip"`
- `"Let's build a real estate listing web application using Next.js and Tailwind."`
- `"What is the current plan for TaskMaster?"`
- `"Continue building TaskMaster based on the saved plan."`
- **Cancellation & Flow Control**:
  - Say `"cancel"`, `"stop"`, or `"quit"` at any point during planning to cancel the session and return to normal mode.

### Expected Behavior:
- Initiates Stage 1 (Requirements & Idea Clarification).
- Guides through Tech Stack, Database, Folder Structure, API Contracts, UI Tokens, and Milestones.
- At Stage 11, generates all 7 Knowledge Base specification documents in `C:\Knowledge-Base\projects\<name>\` following the MunchBite standard.

---

## 3. 📅 Real-Time Daily Schedule & Briefings (English & Tagalog)
*Time-aware schedule intelligence synced with `workflows/time-management.md` and Philippine Standard Time (UTC+8).*

### Sample Prompts to Test:
- **Morning & Daily Briefing**:
  - `"Good morning Maki"`
  - `"What is my schedule today?"`
  - `"What's my agenda for the day?"`
  - `"Ano schedule ko today?"`
  - `"Anong agenda ko ngayon?"`
- **Active Time Block Check**:
  - `"What should I be doing right now?"`
  - `"What's next on my schedule?"`
  - `"Anong oras na?"` / `"What time is it right now?"`
- **Tomorrow's Schedule**:
  - `"What is my schedule tomorrow?"`
  - `"Ano schedule ko bukas?"`
  - `"Show my upcoming schedule."`
- **Night Wrap-Up**:
  - `"Good night"` / `"Matutulog na ako"`

### Expected Behavior:
- Calculates current live clock time and accurately reports the current activity block from `time-management.md`.
- For tomorrow queries, shifts calculation to `target_date = now + 1 day` and briefs tomorrow's routine without confusing it with today's live block.

---

## 4. ⏳ Deadlines Management (English & Tagalog)
*View, add, and complete deadlines in `workflows/deadlines.md`.*

### Sample Prompts to Test:
- `"Show my deadlines"`
- `"What are my deadlines this week?"`
- `"May deadline ba ako this week?"`
- `"Do I have any deadlines coming up?"`
- `"Add deadline Capstone Chapter 4 by Friday"`
- `"Mark deadline Capstone Chapter 4 as done"`

### Expected Behavior:
- Deadlines are parsed, updated in `workflows/deadlines.md`, and confirmed verbally with updated counts.

---

## 5. ⏰ Reminders, Alarms & Calendar Inquiries
*Add, query, and cancel reminders in `data/reminders.json` with timezone awareness.*

### Sample Prompts to Test:
- **Setting Reminders**:
  - `"Remind me at 3 PM to message the client"`
  - `"Remind me in 30 minutes to drink water"`
  - `"Paalala mamayang 5pm mag workout"`
- **Listing & Checking Reminders / Calendar**:
  - `"Show my reminders"`
  - `"Do I have any scheduled meetings?"`
  - `"Do I have a schedule on October 1?"`
  - `"Can you check if I have meetings tomorrow?"`
- **Canceling**:
  - `"Cancel reminder drink water"`

### Expected Behavior:
- Schedules alarms in `ReminderService` and speaks natural relative time confirmation (e.g. *"Got it, sir. I have added mag workout for 5:00 PM tomorrow."*).

---

## 6. 📝 Automated Homework & Research Paper Generation
*Automates document formatting and generation following templates dropped into your `Temp-Guide` folder.*

### How to Test (Two-Step Workflow):
1. **Step 1 — Open Guide Folder**:
   - `"Create my homework"`
   - `"Gawa tayo ng homework"`
   - `"Help me finish my homework assignment"`
   *(MakiAI will open `C:\MakiSync Storage\School\Temp-Guide\` in File Explorer)*
2. **Step 2 — Drop your Rubric/Template into `Temp-Guide`, then say**:
   - `"Write a 3-page research paper on Transformer neural networks based on the rubric in Temp-Guide."`
   - `"Generate my operating systems laboratory report following the format guide."`

### Expected Behavior:
- Reads guides in `Temp-Guide`, generates styled `.docx` in `C:\MakiSync Storage\School\Assignments\<Date>\`, and opens the completed file.

---

## 7. 🔍 Web Research & Live Synthesis
*Real-time internet search and synthesis using DuckDuckGo and Groq.*

### Sample Prompts to Test:
- `"Search online for latest Next.js 15 features"`
- `"Research about deep learning transformer models"`
- `"Mag research ka tungkol sa quantum computing"`

---

## 8. 🧠 Long-Term Memory & Personal Preferences
*Persistent memory stored in `data/memory.json`.*

### Sample Prompts to Test:
- `"Remember that my secondary email is mark.dev@gmail.com"`
- `"What is my secondary email?"`
- `"What do you remember about my secondary email?"`
- `"Forget about my secondary email"`
- `"Remember my dog's name is Cooper"`
- `"What is my dog's name?"`
- `"Who is Mark Vencent Juntilla?"`
- `"What tech stack do I use for NextJS projects?"`
- `"Kamusta ka Maki?"`

---

## 9. 📄 Live File Creation & Generative Code Writing
*Generates and populates code or documents inside `C:\MakiSync Storage\`.*

### Sample Prompts to Test:
- `"Create a file called index.html for a sleek dark-mode landing page."`
- `"Create a Python script named backup_sync.py in my School folder that automates folder compression."`
- `"Write a notes document for my Machine Learning exam review in my School folder."`
- `"Create a file named styles.css with modern glassmorphism utility classes."`

---

## 10. 🧹 Intelligent File Organization & Search
*Organizes files by type and locates documents.*

### Sample Prompts to Test:
- `"Organize my Downloads folder."`
- `"Find all PDF files in my Documents."`
- `"Search for my resume in MakiSync."`
- `"Open my Downloads folder."`
- `"Open Knowledge Base folder."`

---

## 11. 👁️ Physical Webcam Vision (World Observer)
*Observes real-world activities, posture, and held objects via laptop webcam.*

### Sample Prompts to Test:
- `"What am I holding in my hand?"` *(Hold up your phone, pen, coffee cup, or keycard)*
- `"Look at me and tell me what I am doing."`
- `"Is there anyone in the background behind me?"`
- `"Look through the webcam and describe what you see."`

---

## 12. 🖥️ Screen Vision & Visual Error Debugging
*Captures desktop display for visual OCR and code inspection.*

### Sample Prompts to Test:
- `"Look at my screen and tell me what is causing this error."`
- `"What is on my screen right now?"`
- `"Look at this code and explain what is wrong."`
- `"Debug this terminal crash on my screen."`

---

## 13. 🪟 Multi-Monitor Workspace Auto-Tiling & Dragging
*Manages multi-display window tiling without gaps or overlaps.*

### Sample Prompts to Test:
- `"Organize my workspace."` *(IDE full screen on main monitor + Chrome/Explorer 50/50 on second monitor)*
- `"Tile my windows."`
- `"Move Chrome to my second monitor."`
- `"Relocate VS Code to the main monitor."`

---

## 14. 🌐 Chrome Multi-Profile Site Launcher
*Directly opens designated Google Chrome profiles without collision.*

### Sample Prompts to Test:
- `"Open Facebook"` or `"Launch FB"`
- `"Open GitHub"`
- `"Open YouTube"`
- `"Go to Canva"`
- `"Open Google Chrome"`

---

## 15. 🔊 Native Windows Audio, Ducking & Volume Scaling
*Volume control with auto-ducking during speech.*

### Sample Prompts to Test:
- `"Set the volume to maximum."`
- `"Set volume to 65%."`
- `"Volume down"` / `"Volume up"`
- `"Mute volume"` / `"Unmute audio"`

---

## 16. ⚡ System Health, Power & Telemetry
*Hardware introspection and Windows power management.*

### Sample Prompts to Test:
- `"Check system health"`
- `"What are my system vitals?"`
- `"How is my battery?"`
- `"Lock the computer"`
- `"Set brightness to 80%"`
- `"Sleep the PC"`

---

## 17. 🎵 Media Playback Controls
*Native Windows media key simulation for Spotify, YouTube, and media players.*

### Sample Prompts to Test:
- `"Pause music."` / `"Resume playback."`
- `"Next track."` / `"Skip song."`
- `"Previous track."`

---

## 18. 📷 Camera & Screenshot Utilities
*Capture photos and screenshots saved into dated folders.*

### Sample Prompts to Test:
- `"Take a screenshot."`
- `"Take a photo."`
- `"Open screenshots folder."`
- `"Open photos folder."`

---

*Verified with 100% test pass rate on Tuesday, September 15, 2026.*
