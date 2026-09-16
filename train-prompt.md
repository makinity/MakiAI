Run a complete, rigorous end-to-end diagnostic and calibration test on MakiAI across all features and skills, exactly like our continuous training workflow.

Here are the strict guidelines to follow:

1. Real-World User Prompts:
   - Test realistic voice and text prompts based on how I naturally talk to Maki (Taglish / Filipino-English mix, casual phrasing, short commands, context follow-ups, and common Whisper speech-to-text phonetic artifacts like "magazine storage" for MakiSync, "cable", "tops", etc.).

2. Full System Coverage:
   - Routine & Schedule (GoodMorning, Today's & Tomorrow's schedule from time-management.md, GoodNight)
   - Academic & School (Homework, Deadlines, Subjects from subjects.md, Kiro school files)
   - Computer & File Control (MakiSync Storage, Knowledge Base, Screenshots, Photos, Window tiling/moving, Chrome Profile launches)
   - Media & Hardware (Spotify, YouTube search & play, System volume, Brightness, Hardware vitals, Camera/Screen vision)
   - Memory, Reminders & Composio Integrations

3. Diagnostic & Auto-Fix Workflow:
   - Identify every suboptimal response, generic fallback, routing collision, JSON leak, or awkward phrasing.
   - Record every issue found in `respond.md` with:
     * User Prompt (Voice/Text)
     * Suboptimal Response
     * Expected Response
     * Root Cause
   - Modify and fix the Python code in the codebase.
   - Re-test iteratively until 100% of test cases pass with 0 errors.
   - Update `respond.md` and `TESTING_GUIDE.md` when complete.
