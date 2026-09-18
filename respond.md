# 📋 MakiAI — Autonomous QA Diagnostic & Defect Log (`respond.md`)
*Execution Date: Friday, September 18, 2026*
*Environment: Python 3.11 with Live Gemini (`gemini-3.6-flash`), Groq (`qwen3.8-27b`), Composio v3 SDK, PyCAW, & DuckDuckGo*

---

## 🎯 Executive Summary

| Batch # | Category | Total Prompts | Passed (Initial) | Fixed & Verified | Final Pass Rate |
|---|---|---|---|---|---|
| **Batch 1** | Computer Control & Browser Launchers | 9 | 9 | 0 | **100% (9/9)** |
| **Batch 2** | Workspaces & Dynamic Routine Presets | 7 | 7 | 0 | **100% (7/7)** |
| **Batch 3** | Dynamic Identity & Persistent Memory | 6 | 6 | 0 | **100% (6/6)** |
| **Batch 4** | Daily Briefings & Schedule Awareness | 5 | 5 | 0 | **100% (5/5)** |
| **Batch 5** | Deadlines & Reminder Management | 3 | 2 | 1 (Fixed) | **100% (3/3)** |
| **Batch 6** | Academic & Web Research Tools | 2 | 1 | 1 (Fixed) | **100% (2/2)** |
| **Batch 7** | Cloud Workspaces & Developer Assistant | 4 | 3 | 1 (Fixed) | **100% (4/4)** |
| **Live Batches (A-F)** | Real Desktop OS, Vision, Files & Media | 23 | 22 | 1 (Fixed) | **100% (23/23)** |
| **Total** | **Full System QA Sweep** | **59** | **55** | **4 (All Fixed)** | **100% (59/59)** |

---

## 🛠️ Resolved Issues & Verification Audit

### 🟢 Resolved Finding 1: Named Month Deadline Parsing & Title Extraction (`B5-02`)
- **User Prompt:** `"Add a deadline for Capstone 2 Chapter 5 due on October 15 at 11:59 PM"`
- **Root Cause:** Missing named month regex in `skills/deadline_skill.py`.
- **Resolution:** Implemented named month regex parser with automatic target year resolution and title cleaning.
- **Verification Output (Live Terminal):**
  ```
  <<< MAKI: I've drafted that deadline for Capstone 2 Chapter 5 under School due on 2026-10-15, sir. Please confirm or adjust the details on your screen.
  ```
- **Status:** ✅ **100% VERIFIED & FIXED**

---

### 🟢 Resolved Finding 2: Keyword Overlap between Composio and Web Research (`B6-02`)
- **User Prompt:** `"Search the web for the latest updates on Python 3.13 features"`
- **Root Cause:** Composio router matched `"search ... updates"` before web research could run.
- **Resolution:** Restricted Composio triggers and added collision shields so `"search the web"`, `"online"`, and `"google"` route to `ResearchSkill` (DuckDuckGo).
- **Verification Output (Live Terminal):**
  ```
  <<< MAKI: Sir, Python 3.13 has introduced several significant updates. The most notable ones include a new experimental free-threaded mode that allows for better parallelism, a faster interpreter, and improved error messages...
  ```
- **Status:** ✅ **100% VERIFIED & FIXED**

---

### 🟢 Resolved Finding 3: Local File Search Interception & Performance (`B7-03`)
- **User Prompt:** `"Search my files for resume"`
- **Root Cause:**
  1. Media router checked `"resume"` audio trigger.
  2. Research router matched broad `"search"`.
  3. Slow directory scanning visited deep node_modules/appdata folders.
- **Resolution:**
  1. Excluded local file search phrases from audio resume controls.
  2. Shielded local file queries in `SkillRouter` to pass down to `ComputerRouter`.
  3. Optimized `FileManager.search()` using indexed system roots for sub-second search speeds.
- **Verification Output (Live Terminal):**
  ```
  <<< MAKI: Found 10 files matching 'resume', sir.
    • C:\Users\Maki Liones\Downloads\MakiDev Resume.pdf
    • C:\Users\Maki Liones\Downloads\MakiDev_Resume.pdf
    • C:\Users\Maki Liones\Downloads\Mark_Vencent_Juntilla_Resume_ATS.docx
  Opened the first match and its folder for you.
  ```
- **Status:** ✅ **100% VERIFIED & FIXED**

---

### 🟢 Resolved Finding 4: File Deletion Commanded Intercepted by Memory / Fast File Access (`Live Batch 5`)
- **User Prompt:** `"delete file test_del.txt"`
- **Root Cause:**
  1. MemorySkill matched `\b(forget|delete|remove|clear)\b` before computer router.
  2. Fast file access matched any file ending in `.txt` and defaulted action to `open`.
- **Resolution:**
  1. Excluded file targets (`delete file ...`, `remove file ...`) from `MemorySkill`.
  2. Excluded delete/remove verbs from `_handle_fast_file_access()`.
  3. Added `delete_file(path)` method in `FileManager` wired to `_handle_files`.
- **Verification Output (Live Terminal):**
  ```
  <<< MAKI: I've deleted 'test_del.txt' from your storage, sir.
  ```
- **Status:** ✅ **100% VERIFIED & FIXED**

---

## 🔬 Complete Batch-by-Batch Log (59/59 Passed)

### Batch 1: Computer Control & Hardware Diagnostics (9/9 Passed)
* `[B1-01]` **Prompt:** `"open facebook"`
  * **Result:** `PASS` (0.02s) — `Opening Facebook in your main profile, sir.` (Launched `Profile 4` `juntillakingmaki@gmail.com`).
* `[B1-02]` **Prompt:** `"open youtube"`
  * **Result:** `PASS` (0.01s) — `Opening YouTube in your personal profile, sir.` (Launched `Default`).
* `[B1-03]` **Prompt:** `"open github"`
  * **Result:** `PASS` (0.01s) — `Opening GitHub in your development profile, sir.` (Launched `Default`).
* `[B1-04]` **Prompt:** `"what is my battery percentage"`
  * **Result:** `PASS` (0.07s) — `Sir, your battery is at 78% and currently plugged in (charging).`
* `[B1-05]` **Prompt:** `"what is my cpu and ram usage"`
  * **Result:** `PASS` (0.11s) — `CPU utilization is at 86.3%, and RAM usage is at 94.9% (7.3 GB used out of 7.7 GB), sir.`
* `[B1-06]` **Prompt:** `"volume up"`
  * **Result:** `PASS` (0.15s) — `Volume set to 92%.`
* `[B1-07]` **Prompt:** `"volume down"`
  * **Result:** `PASS` (0.00s) — `Volume set to 82%.`
* `[B1-08]` **Prompt:** `"mute audio"`
  * **Result:** `PASS` (0.00s) — `Muted.`
* `[B1-09]` **Prompt:** `"what is my system health"`
  * **Result:** `PASS` (0.10s) — Complete hardware diagnostic summary of battery, CPU, RAM, and disk storage.

---

### Batch 2: Workspaces & Dynamic Routine Presets (7/7 Passed)
* `[B2-01]` **Prompt:** `"Prepare for my client work"`
  * **Result:** `PASS` (0.01s) — Opened Chrome Profile 66 with Astra AI, Metricool, and social dashboard links.
* `[B2-02]` **Prompt:** `"Prep for class"`
  * **Result:** `PASS` (0.03s) — Opened Google Meet, Classroom, and Facebook in Default profile.
* `[B2-03]` **Prompt:** `"Prepare for my coding session"`
  * **Result:** `PASS` (0.14s) — Launched VS Code and loaded GitHub development block.
* `[B2-04]` **Prompt:** `"Prep for AI video creator jobs"`
  * **Result:** `PASS` (0.28s) — Launched dual Chrome profiles (`Profile 4` & `Profile 36`) with OnlineJobs.ph, LinkedIn, ChatGPT, portfolio, and resume folder.
* `[B2-05]` **Prompt:** `"Prep for SMM jobs"`
  * **Result:** `PASS` (0.26s) — Launched dual Chrome profiles (`Profile 4` & `Profile 54`) with OnlineJobs.ph, Indeed, Canva portfolio, and SMM resume.
* `[B2-06]` **Prompt:** `"Prep for gaming"`
  * **Result:** `PASS` (0.30s) — Launched evening gaming and leisure workspace.
* `[B2-07]` **Prompt:** `"Prep for interview"`
  * **Result:** `PASS` (0.64s) — `It's not your scheduled interview time yet, sir, but I have prepared your meeting platform and documents so you can review ahead of time.`

---

### Batch 3: Dynamic Identity & Persistent Memory (6/6 Passed)
* `[B3-01]` **Prompt:** `"Who am I and what am I studying?"`
  * **Result:** `PASS` (0.65s) — `You are Mark Vencent L. Juntilla, who goes by Maki, and you are currently a Bachelor of Science in Information Technology student.`
* `[B3-02]` **Prompt:** `"What are my main goals and current focus areas?"`
  * **Result:** `PASS` (0.65s) — Accurately retrieved short/medium term career and academic goals from Knowledge-Base.
* `[B3-03]` **Prompt:** `"Remember that my secondary email is markjuntillava@gmail.com"`
  * **Result:** `PASS` (0.33s) — `Got it. I'll remember: secondary_email — markjuntillava@gmail.com.`
* `[B3-04]` **Prompt:** `"Tandaan mo na paborito kong IDE is Cursor and VS Code"`
  * **Result:** `PASS` (15.71s) — Bilingual Tagalog trigger extracted: `preferred_ide — Cursor and VS Code`.
* `[B3-05]` **Prompt:** `"What do you remember about my secondary email?"`
  * **Result:** `PASS` (42.08s) — `I recall your secondary email is markjuntillava@gmail.com, sir.`
* `[B3-06]` **Prompt:** `"Forget my secondary email"`
  * **Result:** `PASS` (53.96s) — `Done, sir. I've forgotten: fact about 'secondary', secondary_email.`

---

### Batch 4: Daily Briefings & Schedule Awareness (5/5 Passed)
* `[B4-01]` **Prompt:** `"Good morning Maki"`
  * **Result:** `PASS` (5.70s) — Time-aware Friday morning briefing with active job hunting and upcoming coding blocks.
* `[B4-02]` **Prompt:** `"What is my agenda for today?"`
  * **Result:** `PASS` (18.75s) — Full chronological schedule breakdown for Friday.
* `[B4-03]` **Prompt:** `"Ano schedule ko today?"`
  * **Result:** `PASS` (41.00s) — Bilingual Tagalog query accurately routed to daily schedule engine.
* `[B4-04]` **Prompt:** `"What time is it right now?"`
  * **Result:** `PASS` (66.27s) — `It is 11:54 AM on Friday, September 18, 2026, sir.`
* `[B4-05]` **Prompt:** `"Good night Maki, wrap up my day"`
  * **Result:** `PASS` (29.81s) — Night wrap-up briefing with Saturday preview and reflection inquiry.

---

### Batch 5: Deadlines & Reminder Management (3/3 Passed)
* `[B5-01]` **Prompt:** `"What are my upcoming deadlines?"`
  * **Result:** `PASS` (2.69s) — Listed active deadlines: ICC 600 activity tree, Capstone 2 Chapter 4, and Capstone 2 Chapter 5.
* `[B5-02]` **Prompt:** `"Add a deadline for Capstone 2 Chapter 5 due on October 15 at 11:59 PM"`
  * **Result:** `PASS` (0.01s) — Formatted deadline for `2026-10-15` with UI modal confirmation.
* `[B5-03]` **Prompt:** `"Show my active reminders"`
  * **Result:** `PASS` (29.11s) — Reported active reminder for 3:00 PM client message and upcoming interviews.

---

### Batch 6: Academic & Web Research Tools (2/2 Passed)
* `[B6-01]` **Prompt:** `"Help me with my assignment in BAT-600"`
  * **Result:** `PASS` (0.02s) — Opened `Temp-Guide` folder for assignment template & rubric drop-in.
* `[B6-02]` **Prompt:** `"Search the web for the latest updates on Python 3.13 features"`
  * **Result:** `PASS` (1.45s) — Fulfill via DuckDuckGo fallback and delivered a comprehensive feature summary.

---

### Batch 7: Cloud Workspaces & Developer Assistant (4/4 Passed)
* `[B7-01]` **Prompt:** `"Check my latest emails on Gmail"`
  * **Result:** `PASS` (1.72s) — Live Composio query fetched latest email from Twine Team and offered to draft a reply.
* `[B7-02]` **Prompt:** `"Check my messages on Facebook"`
  * **Result:** `PASS` (7.22s) — Live Composio query fetched latest message from Mark Liones Juntilla on MakiSync Page.
* `[B7-03]` **Prompt:** `"Search my files for resume"`
  * **Result:** `PASS` (0.43s) — Returned indexed PDF and DOCX resume files and revealed them in File Explorer.
* `[B7-04]` **Prompt:** `"kiro create a python script that prints hello world"`
  * **Result:** `PASS` (7.20s) — Headless Kiro CLI generated python script output.

---

### Live Batch Execution: Physical Windows, Camera Vision, & File Operations (23/23 Passed)
* **Window Dragging & Inter-Monitor Transfer:** 4/4 Passed (Moved windows to monitor 2, back to monitor 1, auto-tiled 50/50 split).
* **Optical Webcam Capture & Screen Vision:** 3/3 Passed (Captured webcam photo to `C:\MakiSync Storage\MakiAI\Photos\2026-09-18\photo_20260918_120126.jpg`, analyzed environment with Gemini Vision).
* **Desktop App Management:** 4/4 Passed (Launched and terminated Notepad, opened screenshots directory).
* **Media & Volume Control:** 4/4 Passed (Opened YouTube Default profile, set volume to 60%, muted and unmuted via PyCAW).
* **Filesystem Lifecycle:** 4/4 Passed (Created `notes.txt`, created `test_del.txt`, deleted `test_del.txt`, revealed in Explorer).
* **Routines, Workspaces & Memory:** 4/4 Passed (Morning briefing, client profile 66 launch, bilingual memory store/recall).