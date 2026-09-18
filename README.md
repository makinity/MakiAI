<div align="center">

# 🤖 MAKI·AI (巻)
### *Next-Generation Autonomous Desktop Companion & Windows OS Orchestrator*

<p align="center">
  <a href="https://git.io/typing-svg">
    <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=20&duration=3000&pause=1000&color=00D2FF&center=true&vCenter=true&width=650&lines=Autonomous+Workspace+Provisioning+%26+Routine+Engine;Dual-Vision+Webcam+Observer+%26+Screen+OCR;Discord+Live+Voice+Calling+%26+Telegram+Mobile+Bridge;Ultra-Low+Latency+Dual-Brain+(Groq+70B+%2B+Gemini+2.5);Academic+Hub+%26+Autonomous+Word+Document+Authoring" alt="Typing SVG" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/Windows-11_Win32-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 11 Win32" />
  <img src="https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=for-the-badge&logo=fastapi&logoColor=white" alt="Groq LLaMA 3.3" />
  <img src="https://img.shields.io/badge/Google-Gemini_2.5_Flash-8E75C2?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Gemini 2.5 Flash" />
  <img src="https://img.shields.io/badge/Discord-Live_Voice_VoIP-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord Voice" />
  <img src="https://img.shields.io/badge/Telegram-24%2F7_Mobile_Remote-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Remote" />
  <img src="https://img.shields.io/badge/Voice-Edge_TTS_Ryan-00C49F?style=for-the-badge&logo=soundcharts&logoColor=white" alt="Edge TTS" />
</p>

---

</div>

## 🌌 System Architecture & Data Flow

```mermaid
flowchart TB
    subgraph Inputs["📥 Multi-Modal Sensory Ingestion"]
        WW["🎙️ Porcupine Wake Word ('Hey Maki')"]
        PTT["⌨️ Push-to-Talk ('Right Alt')"]
        DISC_IN["🎮 Discord Voice Channel / Chat"]
        TG_IN["✈️ Telegram Mobile Notes / Photos"]
        CAM["👁️ Webcam Optical Stream (OpenCV)"]
        SCR["🖥️ Dual-Screen OCR Capture"]
    end

    subgraph CoreBrain["🧠 Central Orchestrator & Dual Brain"]
        ORCH["Core Orchestrator & Intent Router"]
        CTX["Context Builder + Knowledge Base RAG"]
        GROQ["⚡ Groq LLaMA-3.3-70B (Fast Brain)"]
        GEM["🔮 Gemini 2.5 Flash (Vision & Multimodal)"]
        KB[("📚 C:/Knowledge-Base/ (Markdown DB)")]
    end

    subgraph ExecEngine["⚙️ Subsystems & Autonomous Actuators"]
        ROUTINE["🚀 Autonomous Routine & Workspace Daemon"]
        WINDOW["🪟 Win32 Multi-Monitor Auto-Tiler"]
        CHROME["🌐 Multi-Profile Chrome Launcher (Local State)"]
        DOCX["📄 Word Document Assignment Generator"]
        KIRO["💻 Kiro CLI Autonomous Coding Agent"]
        TTS["🗣️ British Ryan Neural TTS + Audio Ducking"]
        DISC_OUT["🔊 Discord Live VoIP Voice Stream"]
        TG_OUT["📲 Telegram Push Alerts & Remote Files"]
    end

    Inputs --> ORCH
    ORCH <--> CTX
    CTX <--> KB
    ORCH <--> GROQ
    ORCH <--> GEM
    ORCH --> ExecEngine
```

---

## ⚡ Key Capabilities Showcase

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>🚀 Autonomous Routine Engine</h3>
      <ul>
        <li><b>Lead-Time Provisioning:</b> Monitors schedule and provisions workspaces 15m before events.</li>
        <li><b>College Classes:</b> Launches Google Meet, Google Classroom, Facebook & VS Code for <code>BAT-600</code> & <code>ICC-600</code>.</li>
        <li><b>Client Workflows:</b> Boots dedicated client Chrome profile with Metricool, Instagram, Facebook, YouTube, & Astra AI.</li>
        <li><b>Smart Reasoning:</b> Off-schedule polite contextual reasoning when triggered manually.</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>🎯 Dual-Niche Job Hunting</h3>
      <ul>
        <li><b>AI Video Creator:</b> Multi-Profile Chrome Launch (OnlineJobs, LinkedIn, ChatGPT, Gemini, Portfolio) + Resume folder.</li>
        <li><b>Social Media Manager:</b> Multi-Profile Chrome Launch (OnlineJobs, LinkedIn, Indeed, Canva) + Resume folder.</li>
        <li><b>Interactive GUI Modal:</b> Rapid niche selection pills.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>🎮 Discord Remote Voice Bridge</h3>
      <ul>
        <li><b>Live Voice Channel Calling:</b> Joins Discord voice (<code>!call</code>) and speaks with British Ryan Neural voice.</li>
        <li><b>Full-Duplex AI Interaction:</b> Ask schedule questions, trigger routines, or request document generation directly via Discord.</li>
        <li><b>Remote Screenshot:</b> <code>!screen</code> captures dual displays and uploads directly to chat.</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>✈️ Telegram Mobile Remote</h3>
      <ul>
        <li><b>24/7 Mobile Control:</b> <code>@makiai_assistant_bot</code> for on-the-go access.</li>
        <li><b>Voice Memo Transcriptions:</b> Groq Whisper speech transcription for audio notes.</li>
        <li><b>Rubric to Word Ingestion:</b> Drop rubric photos in chat to auto-generate formatted <code>.docx</code> assignments.</li>
        <li><b>Storage Remote:</b> Search & download files from <code>C:\MakiSync Storage</code>.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>👁️ Multimodal Dual-Vision</h3>
      <ul>
        <li><b>Webcam Observer:</b> Identifies held objects, monitors posture, and tracks physical activities.</li>
        <li><b>Screen OCR Debugging:</b> Inspects terminal stack traces, UI errors, or code snippets with Gemini Vision.</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>🪟 Win32 Window Auto-Tiling</h3>
      <ul>
        <li><b>Zero-Gap Tiling:</b> Organizes desktop apps into clean side-by-side, 3-column, or 2x2 grids.</li>
        <li><b>Cross-Monitor Relocation:</b> Moves apps smoothly between primary and secondary displays.</li>
      </ul>
    </td>
  </tr>
</table>

---

## 📂 Project Structure

```text
MakiAI/
├── main.py                     # Main application entry point & lifecycle manager
├── config/                     # Configuration definitions
│   └── routines.json           # Scheduled classes, client blocks & job-hunting presets
├── core/                       # Central system orchestration
│   ├── orchestrator.py         # Intent dispatching, skill execution & LLM fallbacks
│   └── state_manager.py        # System state tracking (idle, listening, thinking, speaking)
├── gui/                        # Desktop & Web user interface
│   ├── ui_bridge.py            # Python-to-WebUI interactive modal bridge
│   ├── web_ui/                 # HTML5/JS Glassmorphic Dashboard & Modal Forms
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
│   ├── remote/                 # Telegram & Discord 24/7 Mobile/Desktop Voice & Remote Bridges
│   │   ├── discord_service.py  # Discord.py voice channel calling & live audio stream
│   │   └── telegram_service.py # Telegram bot, voice notes & document ingestion
│   ├── routines/               # Autonomous routine monitoring daemon & workspace launcher
│   ├── storage/                # MakiSync storage path handlers & utilities
│   └── voice/                  # Porcupine wake word, STT, Edge-TTS & audio ducking
├── skills/                     # High-level domain capabilities
│   ├── routine_skill.py        # On-demand workspace preparation & modal triggers
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

<details>
<summary><b>🛠️ Step-by-Step Installation & Setup (Click to Expand)</b></summary>

### 1. Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version `3.11` or higher
- **FFmpeg**: Installed and accessible in Windows `PATH` (for Discord voice streaming)
- **Microphone & Webcam**: For wake word, voice, and optical vision

### 2. Clone the Repository
```bash
git clone https://github.com/makinity/MakiAI.git
cd MakiAI
```

### 3. Virtual Environment Setup
```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
pip install "discord.py[voice]"
```

### 5. Configure Environment Variables (`.env`)
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

# Remote Bridges
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USER_ID=...
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
DISCORD_VOICE_CHANNEL_ID=...
DISCORD_TEXT_CHANNEL_ID=...
```

### 6. Run MakiAI
```bash
python main.py
```
</details>

---

## 🗣️ Voice Commands & Remote Triggers Reference

<details>
<summary><b>🎙️ Full Voice & Remote Commands Table (Click to Expand)</b></summary>

| Category | Example Command / Prompt | Expected Action |
|---|---|---|
| **🎯 Job Hunting (Interactive)** | *"Maki, let's hunt a job"* | Prompts for niche selection and displays GUI modal |
| **📹 Job Hunting (AI Video)** | *"Hunt for AI video creator jobs"* | Opens dual Chrome profiles (OnlineJobs, LinkedIn, ChatGPT, Gemini, Portfolio) + AI Video Resume folder |
| **📱 Job Hunting (SMM)** | *"Let's hunt for SMM jobs"* | Opens dual Chrome profiles (OnlineJobs, LinkedIn, Indeed, Canva) + SMM Resume folder |
| **🎓 Online Class Prep** | *"Prep for class"* / *"Prep for online class"* | Detects schedule and opens Google Meet, Google Classroom, Facebook & VS Code |
| **💼 Client Work Prep** | *"Prep for client work"* / *"Prep for work"* | Opens client Chrome profile with Metricool and social platforms |
| **🎮 Discord Voice Calling** | `!call` / `!join` / `!say [text]` | MakiAI enters Discord voice channel and streams speech |
| **✈️ Telegram Remote** | `/screenshot`, `/camera`, `/browse` | Snaps PC screens/webcam or downloads files to mobile |
| **📅 Schedule & Agenda** | *"Good morning Maki"* / *"Ano schedule ko today?"* | Reads today's time-table from `time-management.md` |
| **🌅 Tomorrow Preview** | *"What is my schedule tomorrow?"* / *"Ano schedule ko bukas?"* | Previews upcoming activities for the next calendar day |
| **💻 Autonomous Coding** | *"Open Kiro for TaskMaster"* | Spawns Kiro CLI in target project directory |
| **📝 Academic & Homework** | *"Create my homework based on rubric in Temp-Guide"* | Generates styled `.docx` in Assignments folder |
| **👁️ Vision (Webcam)** | *"What am I holding in my hand?"* | Inspects webcam feed and describes the object |
| **🖥️ Vision (Screen)** | *"Look at my screen and explain this error"* | Performs screen capture and OCR debugging |
| **🪟 Window Layout** | *"Organize my workspace"* / *"Tile my windows"* | Snaps apps into multi-monitor grid/split layouts |
| **📊 Hardware Vitals** | *"What are my system vitals?"* / *"How is my battery?"* | Reports CPU, RAM %, and battery charge status |

</details>

---

<div align="center">
  <sub>Built with ❤️ by <b>Mark Vencent Juntilla</b> · Personal & Proprietary Development</sub>
</div>
