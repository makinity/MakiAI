# 🤖 MakiAI

> **A Jarvis-inspired, multi-modal AI desktop assistant for Windows** — powered by Groq (Llama-3.3 70B), Google Gemini 2.5 Flash, Neural Edge-TTS, Kiro CLI autonomous coding engine, and deep Knowledge Base integration.

---

## 🌟 Overview

**MakiAI** is a personalized desktop companion designed for high-productivity development, academic workflows, multi-monitor window management, and hands-free computer control. It bridges low-latency conversational AI with native Windows operating system automation, webcam physical vision, screen debugging, and project scaffolding.

---

## ✨ Key Capabilities

### ⚡ 1. Autonomous Coding & Terminal Engine (`t=kiro`)
- **Kiro CLI Integration**: Spawns visible or headless instances of `kiro-cli` (Claude Sonnet 4.5 / DeepSeek 3.2 / Qwen3 Coder) to write full-stack code, scripts, and applications on command.
- **Interactive Workspace**: Opens terminal sessions directly in your active development directories (`C:\development\...`).

### 🏗️ 2. 11-Stage Project Planning & Scaffolding
- **Standardized Architecture**: Reads Knowledge Base coding guidelines (`config/coding-standards.md`, `architecture.md`) and conducts structured planning sessions (Idea, Tech Stack, Database, API, Milestones).
- **Auto-Documentation**: Generates all 7 standardized specification documents into `C:\Knowledge-Base\projects\<name>\`.

### 📅 3. Real-Time Routine & Schedule Intelligence (English & Tagalog)
- **Time-Block Aware**: Synchronized with `workflows/time-management.md` and Philippine Standard Time (UTC+8) to report current active blocks and daily agendas.
- **Bilingual Briefings**: Fluent in English, Tagalog, and Taglish (*"Ano schedule ko today?"*, *"Anong agenda ko bukas?"*).
- **Night Wrap-Up & Morning Briefing**: Summarizes accomplishments and prepares tomorrow's tasks.

### 📝 4. Academic Hub & Automated Homework Generation
- **Rubric-Based Document Authoring**: Reads templates dropped into `C:\MakiSync Storage\School\Temp-Guide\` and formats complete multi-page `.docx` assignments, lab reports, or essays into `C:\MakiSync Storage\School\Assignments\<Date>\`.
- **Deadlines Tracking**: View, add, and complete academic milestones in `workflows/deadlines.md`.

### 👁️ 5. Multimodal Dual-Vision (Webcam + Screen)
- **Physical World Observer**: Uses your webcam to identify held objects, recognize activities, check posture, and monitor surroundings in real-time.
- **Screen Vision & Error Debugging**: Captures active displays to analyze terminal stack traces, UI errors, or code snippets with Gemini Vision OCR.

### 🪟 6. Multi-Monitor Window Management & Auto-Tiling
- **Smart Window Tiling**: Organizes desktop apps into clean side-by-side, 3-column, or 2x2 grid layouts without overlaps or gaps.
- **Multi-Monitor Relocation**: Moves applications seamlessly between primary and secondary displays (*"Move Chrome to my second monitor"*).

### 🌐 7. Chrome Multi-Profile Site Launcher
- **Profile-Aware Launching**: Directly targets dedicated Google Chrome user profiles (Personal, Work, Developer) for YouTube, GitHub, Facebook, Canva, and custom web apps.

### 📁 8. Smart Storage & Whisper Normalization
- **Phonetic STT Correction**: Automatically normalizes speech-to-text artifacts (e.g., *"magazine storage"* or *"cable storage"* ➔ `C:\MakiSync Storage\MakiAI\Screenshots`).
- **File Organization**: Cleans and sorts folders by file type and searches Knowledge Base documents.

### 🔊 9. Neural Voice Engine & System Telemetry
- **Calibrated British Neural Voice**: High-fidelity, natural speech (`en-GB-RyanNeural`) with intelligent audio ducking during speech output.
- **Hardware Telemetry**: Real-time battery life, CPU/RAM utilization, brightness, volume scaling, and power state controls (lock, sleep, shutdown).

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Core & OS** | Python 3.11+, Windows Win32 API, `psutil`, `pycaw`, `pygetwindow` |
| **GUI & Visuals** | PyQt6, Custom Dark/Glassmorphism Theme, Dynamic Activity Indicators |
| **Primary AI Inference** | Groq API (`llama-3.3-70b-versatile` — ultra-low latency) |
| **Multimodal & Fallback AI**| Google Gemini API (`gemini-2.5-flash`, `gemini-2.5-flash-lite`) |
| **Speech-to-Text (STT)** | `faster-whisper` (OpenAI Whisper local quantization) |
| **Text-to-Speech (TTS)** | `edge-tts` (Neural Voices), ElevenLabs API, Pygame Audio Mixer |
| **Wake Word Engine** | Picovoice Porcupine (`"Hey Maki"`) + Push-to-Talk (`Right Alt`) |
| **Autonomous Coding** | Kiro CLI (`kiro-cli.exe`), Claude 3.5 Sonnet / DeepSeek V3 / Qwen Coder |
| **Computer Vision** | OpenCV (`cv2`), PIL, Gemini Multimodal Vision API |
| **Cloud & Integrations** | Composio API (GitHub, Notion, Google Calendar, Discord) |

---

## 📂 Project Structure

```
MakiAI/
├── main.py                     # Main application entry point & lifecycle manager
├── core/                       # Central system orchestration
│   ├── orchestrator.py         # Intent dispatching, skill execution & LLM fallbacks
│   └── state_manager.py        # System state tracking (idle, listening, thinking, speaking)
├── gui/                        # PyQt6 desktop user interface
│   ├── app.py                  # Main window layout and sidebar controls
│   ├── components/             # Reusable UI widgets (chat bubbles, status indicators)
│   └── styles/                 # Dark glassmorphism QSS styling
├── services/                   # Modular subsystem services
│   ├── ai/                     # Groq & Gemini API clients, Context Builder
│   ├── browser/                # Chrome profile management & web automation
│   ├── camera/                 # Webcam capture & screenshot handlers
│   ├── cloud/                  # Composio & third-party integrations
│   ├── computer/               # Window manager, auto-tiler, system health & app launcher
│   ├── kb/                     # Knowledge Base indexer, reader, writer & router
│   ├── media/                  # Spotify & native Windows media controls
│   ├── memory/                 # Multi-session memory persistence
│   ├── reminder/               # Background task scheduler & notifications
│   ├── storage/                # MakiSync storage path handlers & utilities
│   └── voice/                  # Porcupine wake word, STT, Edge-TTS & audio ducking
├── skills/                     # High-level domain capabilities
│   ├── goodmorning_skill.py    # Morning routine & daily schedule briefing
│   ├── goodnight_skill.py      # Evening wrap-up & tomorrow preview
│   ├── deadline_skill.py       # Deadlines tracking & milestone logging
│   ├── homework_skill.py       # School document & assignment authoring
│   ├── new_project_skill.py    # 11-stage project planning lifecycle
│   ├── research_skill.py       # Live internet search & synthesis
│   ├── memory_skill.py         # Personal preference storage & retrieval
│   └── interpreter_skill.py    # Local code execution & math engine
└── data/                       # Local JSON databases (memory, reminders, config)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version `3.11` or higher
- **Git**: Installed and configured
- **Microphone & Webcam**: For voice and optical vision features

### 2. Clone the Repository
```bash
git clone https://github.com/makinity/MakiAI.git
cd MakiAI
```

### 3. Set Up Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```

Open `.env` and fill in your keys:
```ini
# Primary AI Engine (Groq - Fast inference)
GROQ_API_KEY=gsk_...

# Vision & Fallback AI (Google Gemini)
GEMINI_API_KEY=AIzaSy...

# Wake Word (Picovoice)
PORCUPINE_ACCESS_KEY=...
WAKE_WORD=Hey Maki

# Local Knowledge Base & Storage Paths
KB_PATH=C:\Knowledge-Base
MAKI_SYNC_PATH=C:\MakiSync Storage

# Voice / TTS Settings
TTS_VOICE=en-GB-RyanNeural
TTS_PITCH=-8Hz
TTS_RATE=+2%
```

### 6. Run MakiAI
```bash
python main.py
```

---

## 🎙️ Interaction Modes

1. **Wake Word**: Say **`"Hey Maki, [command]"`** for hands-free operation.
2. **Push-to-Talk (PTT)**: Hold the **`Right Alt`** key while speaking, then release to execute instantly.
3. **Desktop Chat UI**: Click the chat bar at the bottom of the MakiAI window to type commands directly.

---

## 🗣️ Common Voice Commands Reference

| Category | Example Voice Prompt | Expected Action |
|---|---|---|
| **Schedule & Routine** | *"Good morning Maki"* / *"Ano schedule ko today?"* | Reads today's time-table from `time-management.md` |
| **Tomorrow's Plan** | *"What is my schedule tomorrow?"* / *"Ano schedule ko bukas?"* | Previews upcoming activities for the next calendar day |
| **Autonomous Coding** | *"Open Kiro for TaskMaster"* | Spawns Kiro CLI in target project directory |
| **Headless Code Gen** | `"t=kiro create a python script for scraping"` | Generates code via Kiro CLI in background |
| **Project Planning** | *"I have a new project idea called FitTrack"* | Launches 11-stage project architecture interview |
| **Academic & Homework**| *"Create my homework based on rubric in Temp-Guide"* | Generates styled `.docx` in Assignments folder |
| **Deadlines** | *"Show my deadlines"* / *"Add deadline Chapter 4 by Friday"* | Manages academic tasks in `deadlines.md` |
| **Vision (Webcam)** | *"What am I holding in my hand?"* | Inspects webcam feed and describes the object |
| **Vision (Screen)** | *"Look at my screen and explain this error"* | Performs screen capture and OCR debugging |
| **Window Layout** | *"Organize my workspace"* / *"Tile my windows"* | Snaps apps into multi-monitor grid/split layouts |
| **Window Dragging** | *"Move Chrome to my second monitor"* | Moves target window across display bounds |
| **Chrome Profiles** | *"Open GitHub"* / *"Open Facebook"* / *"Go to Canva"* | Opens web platform in assigned Chrome profile |
| **MakiSync Search** | *"Open the captured image in magazine storage"* | Opens latest screenshot from `MakiSync Storage` |
| **System Hardware** | *"What are my system vitals?"* / *"How is my battery?"* | Reports CPU, RAM %, and battery charge status |
| **Media Controls** | *"Play Bruno Mars on YouTube"* / *"Pause music"* | Streams media via YouTube / native media keys |
| **Volume Scaling** | *"Set volume to 75%"* / *"Mute audio"* | Adjusts Windows master audio level |
| **Memory** | *"Remember that my client meeting is on Zoom"* | Stores persistent note in `memory.json` |

---

## 🧪 Testing & Diagnostics

MakiAI includes a comprehensive diagnostic suite to test intent routing, LLM context generation, and speech normalization:

```bash
# Run the complete 65+ command diagnostic matrix
python scratch/test_all_commands.py
```

All test outcomes, edge cases, and Whisper phonetic adjustments are tracked in [`respond.md`](respond.md) and [`TESTING_GUIDE.md`](TESTING_GUIDE.md).

---

## 📜 License

Personal use and proprietary development — **Mark Vencent Juntilla**.
