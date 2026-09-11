# MakiAI

> A Jarvis-inspired AI desktop assistant for Windows — powered by Google Gemini, ElevenLabs, and your Knowledge Base.

---

## What It Does

- 🎙️ Always-on voice activation via wake word **"Hey Maki"**
- 🔊 Responds in a Jarvis-like voice via ElevenLabs TTS
- 🧠 Powered by Google Gemini — context-aware, KB-connected
- 📚 Reads and writes your Knowledge Base (`C:\Knowledge-Base\`)
- 🖥️ Controls your PC — opens apps, browses, manages files
- 📷 Takes photos, records video, captures screenshots
- ⏰ Sets reminders and speaks them aloud when triggered
- 🧠 Remembers things across sessions
- 🎵 Controls media and system volume
- 🖼️ Animated GUI with idle, listening, thinking, and speaking states

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd MakiAI
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
copy .env.example .env
```

Edit `.env` and fill in your API keys:
- `GEMINI_API_KEY` — [Google AI Studio](https://aistudio.google.com/)
- `ELEVENLABS_API_KEY` — [ElevenLabs](https://elevenlabs.io/)
- `ELEVENLABS_VOICE_ID` — Your chosen voice ID from ElevenLabs
- `PORCUPINE_ACCESS_KEY` — [Picovoice Console](https://console.picovoice.ai/)
- `KB_PATH` — Path to your Knowledge Base (default: `C:\Knowledge-Base`)

### 5. Run

```bash
python main.py
```

---

## Project Structure

```
MakiAI/
├── main.py               # Entry point
├── core/                 # Orchestrator + state machine
├── gui/                  # PyQt6 GUI — pages, components, assets
├── services/             # All service modules (AI, voice, KB, camera, etc.)
├── skills/               # KB skill implementations
├── data/                 # Local persistent data (JSON files)
└── docs/                 # Internal documentation
```

---

## Voice Commands

| Say | Action |
|---|---|
| "Hey Maki, good morning" | Morning briefing from KB |
| "Hey Maki, good night" | Night wrap-up |
| "Hey Maki, what's next" | Quick check-in |
| "Hey Maki, add deadline [task]" | Add to KB deadlines |
| "Hey Maki, open [app]" | Launch desktop app |
| "Hey Maki, open [website]" | Open in browser |
| "Hey Maki, take a screenshot" | Capture screen |
| "Hey Maki, take a photo" | Capture from webcam |
| "Hey Maki, remind me at [time] to [task]" | Set reminder |
| "Hey Maki, remember that [info]" | Store memory |
| "Hey Maki, volume up / down / mute" | System volume |
| "Hey Maki, log out" | Log out of MakiAI |

---

## KB Documentation

Full planning docs at: `C:\Knowledge-Base\projects\MakiAI\`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| GUI | PyQt6 + rlottie-python |
| AI | Google Gemini API |
| Wake Word | Porcupine (Picovoice) |
| STT | faster-whisper |
| TTS | ElevenLabs + edge-tts fallback |
| Camera | OpenCV |
| Packaging | PyInstaller |

---

## License

Personal use only — Mark Vencent Juntilla
