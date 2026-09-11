# MakiAI — Changelog

## v1.0.0 — 2026-09-11

### Initial Release

**Core Features**
- Always-on wake word detection ("Hey Maki") via SpeechRecognition
- Conversational mode — wake once, talk freely, auto-sleeps after 30s idle
- Jarvis-like voice output via ElevenLabs API (Edge TTS fallback)
- AI brain powered by Groq (llama) with Google Gemini fallback
- Knowledge Base integration — reads/writes C:\Knowledge-Base\

**KB Skills (voice-activated)**
- Good Morning briefing from KB schedule
- Good Night wrap-up with carryover update
- Hello / check-in with time-aware schedule
- Deadline tracking (add, list, complete)
- Reminder scheduling with voice alerts
- Cross-session memory (remember, recall, forget)
- New project planning trigger

**Computer Control**
- Open desktop apps and websites by name
- Volume control (up, down, mute, set level)
- System control (shutdown, restart, sleep, lock)
- File management (organize, search folders)
- Media control (play/pause, next/prev track, Spotify)

**Camera & Media**
- Take photos (saves to Pictures/MakiAI)
- Start/stop video recording (saves to Videos/MakiAI)
- Screenshots — full screen and active window
- Open photos/recordings folders in File Explorer

**Reminders & Memory**
- APScheduler-based reminder system (persists across restarts)
- Windows toast notifications when reminders fire
- Long-term memory store (memory.json)

**GUI**
- PyQt6 dark HUD with animated states (idle, listening, thinking, speaking)
- Frameless draggable window
- Real-time transcription bar
- Conversation chat log with thread-safe updates
- Settings page — change API keys, voice, wake word without restart
- Export conversation log (.txt or .md)

**Security**
- bcrypt password hashing for one-time login
- Persistent session with manual logout
- All API keys in .env — never hardcoded
