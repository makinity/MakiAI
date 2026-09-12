# MakiAI — Complete Feature & Prompt Testing Guide 🚀

This testing guide provides a comprehensive list of all features, capabilities, and exact sample voice/text prompts built into **MakiAI**. 

You can test these commands by:
1. **Push-to-Talk (PTT)**: Hold the **`Right Alt`** key while speaking, then release to execute.
2. **Wake Word**: Say **`"Hey Maki, [command]"`** or speak direct commands.
3. **Desktop Chat UI**: Type any command directly into the input bar.

---

## Table of Contents
1. [⚡ Kiro CLI Coding Engine (`t=kiro`)](#1--kiro-cli-coding-engine-tkiro)
2. [🏗️ Project Planning & Scaffolding (11-Stage Pipeline)](#2-️-project-planning--scaffolding-11-stage-pipeline)
3. [📝 Automated Homework & Research Paper Generation](#3--automated-homework--research-paper-generation)
4. [📄 Live File Creation & Generative Code Writing](#4--live-file-creation--generative-code-writing)
5. [🧹 Intelligent File Organization & Search](#5--intelligent-file-organization--search)
6. [🧠 Knowledge Base Memory, Reminders & Personal Briefings](#6--knowledge-base-memory-reminders--personal-briefings)
7. [👁️ Physical Webcam Vision (World Observer)](#7-️-physical-webcam-vision-world-observer)
8. [🔍 Screen Vision & Visual Error Debugging](#8--screen-vision--visual-error-debugging)
9. [🪟 Multi-Monitor Workspace Auto-Tiling & Dragging](#9--multi-monitor-workspace-auto-tiling--dragging)
10. [🌐 Chrome Multi-Profile Site Launcher](#10--chrome-multi-profile-site-launcher)
11. [🔊 Native Windows Audio, Ducking & Volume Scaling](#11--native-windows-audio-ducking--volume-scaling)
12. [⚡ System Health & Hardware Telemetry](#12--system-health--hardware-telemetry)
13. [🔒 System Power, Brightness & Lock Controls](#13--system-power-brightness--lock-controls)
14. [🎵 Media Playback Controls](#14--media-playback-controls)
15. [📷 Camera & Screenshot Utilities](#15--camera--screenshot-utilities)

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
- **Interactive Mode**: Automatically opens a new, visible PowerShell window with Kiro CLI running in your project directory (`C:\Users\Maki Liones\MakiSync Storage\Personal\TaskMaster\`) so you can watch Kiro code live.
- **Background Mode**: Executes in headless mode (`--no-interactive --trust-all-tools`) and outputs the generated code directly in the MakiAI chat.

---

## 1. 🏗️ Project Planning & Scaffolding (11-Stage Pipeline)
*MakiAI reads your Knowledge Base coding standards (`config/coding-standards.md`, `web-development/architecture.md`, `folder-structure.md`) and kicks off Stage 1 of the official project planning process.*

### Sample Prompts to Test:
- `"I have a new project idea: a modern freelance portfolio website."`
- `"Let's build a real estate listing web application using Next.js and Tailwind."`
- `"What is the current plan for TaskMaster?"`
- `"Continue building TaskMaster based on the saved plan."`
- `"Use Kiro to generate the TaskMaster website based on the Knowledge Base plan."`
- `"Start a new project called TaskMaster."`

### Expected Behavior:
- MakiAI analyzes the idea against your Knowledge Base architecture.
- Outlines **Stage 1 of 11** (Project Name, Target Users, Core Problem, Platform, and Clarifying Questions).

---

## 2. 📝 Automated Homework & Research Paper Generation
*Automates document formatting and generation following templates dropped into your `Temp-Guide` folder.*

### How to Test (Two-Step Workflow):
1. **Step 1 — Open the Guide Folder**:
   - `"Create my homework"`
   - `"Make my assignment"`
   - `"Help me with my homework"`
   *(MakiAI will automatically open `C:\MakiSync Storage\School\Temp-Guide\` in File Explorer)*
2. **Step 2 — Drop your Rubric/Template into `Temp-Guide`, then say**:
   - `"Write a 3-page research paper on Transformer neural networks based on the rubric in Temp-Guide."`
   - `"Generate my operating systems laboratory report following the format guide."`

### Expected Behavior:
- MakiAI reads the rubric/guide in `Temp-Guide`.
- Generates a fully styled `.docx` Word document inside `C:\MakiSync Storage\School\Assignments\<Date>\` and launches it for you.

---

## 3. 📄 Live File Creation & Generative Code Writing
*Generates and populates code, markup, or notes directly inside your organized `C:\MakiSync Storage\` system.*

### Sample Prompts to Test:
- `"Create a file called index.html for a sleek dark-mode landing page."`
- `"Create a Python script named backup_sync.py in my School folder that automates folder compression."`
- `"Write a notes document for my Machine Learning exam review in my School folder."`
- `"Create a file named styles.css with modern glassmorphism utility classes."`
- `"Append this note to my last document: remember to test all endpoints before deployment."`

### Expected Behavior:
- File is created in the appropriate `MakiSync Storage` directory with generated contents.
- MakiAI confirms creation and opens the file in your default editor.

---

## 4. 🧹 Intelligent File Organization & Search
*Sorts messy directories into categorized subfolders (PDFs, Images, Code, Videos, Archives) and finds documents.*

### Sample Prompts to Test:
- `"Organize my Downloads folder."`
- `"Find all PDF files in my Documents."`
- `"Search for my resume in MakiSync."`
- `"Open my Downloads folder."`
- `"Open my Screenshots folder."`
- `"Open my Knowledge Base folder."`

### Expected Behavior:
- Scans target folder, classifies every file by extension, moves them into clean subdirectories, and opens the folder.

---

## 5. 🧠 Knowledge Base Memory, Reminders & Personal Briefings
*Personal assistant features tied directly to `C:\Knowledge Base\`.*

### Sample Prompts to Test:
- `"Good morning Maki."` *(Delivers daily briefing, schedule, and deadline summary)*
- `"Remember that my capstone project defense is on November 20 at 10 AM."`
- `"Remember that my preferred tech stack is React with TypeScript and FastAPI."`
- `"What do you remember about my preferences?"`
- `"Remind me to submit my research proposal in 2 hours."`
- `"What are my upcoming deadlines this week?"`
- `"What are my active reminders?"`
- `"Who is Mark Vencent Juntilla?"`

### Expected Behavior:
- Persistent memory updates saved to `C:\Knowledge Base\`.
- Timers and reminders scheduled via the background scheduler daemon.

---

## 6. 👁️ Physical Webcam Vision (World Observer)
*Uses your laptop's physical webcam to observe your real-world activity, posture, and held objects.*

### Sample Prompts to Test:
- `"What am I holding in my hand?"` *(Hold up your phone, pen, coffee cup, or keycard)*
- `"Look at me and tell me what I am doing."`
- `"Is there anyone in the background behind me?"`
- `"What object is in front of the camera?"`
- `"Look through the webcam and describe what you see."`

### Expected Behavior:
- Activates webcam for ~0.3s, flushes auto-exposure buffers, encodes base64 frame, releases camera hardware immediately, and provides spoken multimodal vision analysis.

---

## 7. 🔍 Screen Vision & Visual Error Debugging
*Captures your live desktop monitor for visual OCR, code comprehension, and error debugging.*

### Sample Prompts to Test:
- `"Look at my screen and tell me what is causing this error."`
- `"What is on my screen right now?"`
- `"Look at this code and explain what is wrong."`
- `"Debug this terminal crash on my screen."`
- `"Summarize the article on my screen."`

### Expected Behavior:
- Grabs active display screen, sends it to `gemini-3.6-flash` multimodal endpoint, and explains the visual context.

---

## 8. 🪟 Multi-Monitor Workspace Auto-Tiling & Dragging
*Manages windows across dual displays with zero overlap, developer-first priority, and no gaps.*

### Sample Prompts to Test:
- `"Organize my workspace."` *(Snaps IDE 100% full screen on primary display + Chrome & File Explorer 50/50 on secondary display)*
- `"Tile my windows."`
- `"Move Chrome to my second monitor."`
- `"Relocate VS Code to the main monitor."`
- `"Put this window on the left screen."`

### Expected Behavior:
- Evaluates monitor geometries, classifies active apps (IDE vs Reference Browser vs Explorer), restores and sizes windows with pixel-exact precision (`MoveWindow`).

---

## 9. 🌐 Chrome Multi-Profile Site Launcher
*Launches specific web applications directly in their designated Google Chrome profiles.*

### Sample Prompts to Test:
- `"Open Facebook"` or `"Launch FB"`
- `"Open GitHub"`
- `"Go to Canva"`
- `"Open Google Classroom"`
- `"Open LinkedIn"`
- `"Launch TikTok"`
- `"Open YouTube"`
- `"Open Gemini"`

### Expected Behavior:
- Inspects Chrome `Local State`, targets the correct profile directory (`Default`, `Profile 1`, `Profile 2`, etc.), and launches the URL directly into that profile.

---

## 10. 🔊 Native Windows Audio, Ducking & Volume Scaling
*Full Windows Core Audio control with auto-ducking during speech.*

### Sample Prompts to Test:
- `"Set the volume to maximum."`
- `"Set volume to 65%."`
- `"Turn the volume down."`
- `"Volume up by 20."`
- `"Mute audio."` / `"Unmute audio."`
- `"Set volume to minimum."`

### Expected Behavior:
- pycaw scales master volume scalar with unmuting.
- Background media auto-ducks to 24% when Maki speaks and restores smoothly to previous level upon completion.

---

## 11. ⚡ System Health & Hardware Telemetry
*Hardware introspection and battery diagnostics.*

### Sample Prompts to Test:
- `"What are my system vitals?"`
- `"How is my battery?"`
- `"What is my CPU and RAM usage?"`
- `"Check system health."`

### Expected Behavior:
- Reads `psutil` battery percentage, charging state, CPU utilization, and RAM allocation.

---

## 12. 🔒 System Power, Brightness & Lock Controls
*Windows power management and display brightness.*

### Sample Prompts to Test:
- `"Lock the computer."`
- `"Increase brightness."`
- `"Set brightness to 80%."`
- `"Lower brightness."`
- `"Sleep the PC."`

### Expected Behavior:
- Calls native Windows APIs (`LockWorkStation`, WMI brightness, etc.).

---

## 13. 🎵 Media Playback Controls
*Native Windows media key simulation for Spotify, YouTube, and media players.*

### Sample Prompts to Test:
- `"Pause music."` / `"Resume playback."`
- `"Next track."` / `"Skip song."`
- `"Previous track."`

---

## 14. 📷 Camera & Screenshot Utilities
*Quick media capture saved into organized date folders.*

### Sample Prompts to Test:
- `"Take a photo."`
- `"Capture a screenshot."`
- `"Open photos folder."`
- `"Open screenshots folder."`
- `"Open recordings folder."`

---

*Generated for MakiAI Testing & Verification.*
