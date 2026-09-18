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
   - Reads user schedule & active time-block from Knowledge Base (`KBReader`).
   - Checks active reminders and memory entries for today.
4. **TTS Spoken Output**: Edge TTS speaks current time block and upcoming events.
5. **State Machine**: Transitions to **Active Conversation Session** (45s listening window) for direct follow-up commands without wake words.

### 🔹 Command #2
* **Spoken Phrase:** `"Can you add a schedule for tomorrow at 9:00 PM that we have a meeting via Zoom?"`
* **Audio Input:** User Voice Recording (`.wav`)
* **Extracted Payload:** `"add a schedule for tomorrow at 9:00 PM that we have a meeting via Zoom"`
* **Status:** ✅ **Optimal & Routed**

#### ⚙️ Internal Execution Flow:
1. **Audio Capture & STT**: Transcribed via Groq Whisper (`whisper-large-v3-turbo`).
2. **Skill Routing**: Matches `SkillRouter` ➔ **`ReminderSkill`** (`skills/reminder_skill.py`).
3. **Execution**:
   - `ReminderSkill._add()` parses `"tomorrow at 9:00 PM"` and message `"Zoom meeting"`.
   - Schedules reminder in `ReminderService` and saves to `data/reminders.json`.
4. **TTS Spoken Confirmation**: Edge TTS speaks: *"Got it. I'll remind you about the Zoom meeting tomorrow at 9:00 PM."*
5. **Scheduled Trigger**: Tomorrow at 21:00, MakiAI speaks: *"Sir, this is your reminder: Zoom meeting."*
