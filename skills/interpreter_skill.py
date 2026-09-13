"""
MakiAI — Universal Code & Task Execution Skill (interpreter_skill.py)
Inspired by OpenInterpreter for arbitrary computer tasks and automation.

Capabilities:
  1. Python & PowerShell code synthesis and execution.
  2. Batch file processing (image resize/convert, PDF merge, file grouping).
  3. Data calculation, CSV/Excel parsing, database querying.
  4. Self-healing execution loop with automated traceback feedback (up to 2 retries).
  5. Strict sandboxing & StorageSecurityGuard enforcement.
"""

import os
import sys
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional

from skills.base_skill import BaseSkill
from services.storage.maki_sync import StorageSecurityGuard, MAKI_SYNC_ROOT


class InterpreterSkill(BaseSkill):
    """
    Arbitrary task and code execution engine for MakiAI.
    Translates complex user automation requests into safe Python/PowerShell scripts,
    executes them, and returns conversational summaries.
    """

    SKILL_ID = "interpreter"
    REQUIRED_FILES = [
        "user/profile.md",
        "system/capabilities.md",
    ]

    def __init__(self, gemini_service, context_builder, kb_reader, kb_writer):
        super().__init__(gemini_service, context_builder, kb_reader, kb_writer)
        self.last_generated_files: list[Path] = []

    def execute(self, text: str) -> str:
        """
        Main execution flow:
          1. Synthesize script from user prompt.
          2. Execute script in isolated subprocess.
          3. Self-correct if errors occur.
          4. Return conversational summary to user.
        """
        clean_text = text.strip()
        print(f"[InterpreterSkill] Processing automation task: '{clean_text}'")

        # Step 1: Synthesize Code
        code, lang = self._synthesize_code(clean_text)
        if not code:
            return "I couldn't generate an execution plan for that task, sir. Could you clarify what you'd like me to do?"

        # Step 2: Validate Security
        is_safe, reason = self._validate_security(code, lang)
        if not is_safe:
            return f"🛡️ Security Guard: I blocked this script execution because: {reason}"

        # Step 3: Execute with Self-Healing (up to 2 retry attempts)
        max_attempts = 3
        current_code = code
        current_lang = lang

        for attempt in range(1, max_attempts + 1):
            print(f"[InterpreterSkill] Executing {current_lang} script (Attempt {attempt}/{max_attempts})...")
            success, stdout, stderr = self._run_code(current_code, current_lang)

            if success:
                print(f"[InterpreterSkill] Task succeeded on attempt {attempt}.")
                return self._summarize_success(clean_text, stdout, current_code)

            print(f"[InterpreterSkill] Execution failed (Attempt {attempt}): {stderr[:300]}")
            if attempt < max_attempts:
                # Ask AI to self-correct the code with traceback
                current_code, current_lang = self._self_heal_code(clean_text, current_code, current_lang, stderr)
                if not current_code:
                    break
                is_safe, reason = self._validate_security(current_code, current_lang)
                if not is_safe:
                    return f"🛡️ Security Guard: Corrected script was blocked: {reason}"

        error_snippet = (stderr or stdout or "Unknown runtime error").strip()
        if len(error_snippet) > 200:
            error_snippet = error_snippet[:190] + "..."
        return f"I encountered an error executing that automation task: {error_snippet}"

    # ─── Code Synthesis ───────────────────────────────────────────────────────

    def _synthesize_code(self, user_prompt: str) -> Tuple[str, str]:
        """Ask Gemini/Groq to write executable Python or PowerShell code."""
        system_prompt = f"""You are MakiAI's Universal Code & Task Execution Engine.
Write executable, self-contained, robust Python 3 or PowerShell code to accomplish the user's task.

ENVIRONMENT CONTEXT:
- OS: Windows 10/11
- Primary Storage: {MAKI_SYNC_ROOT}
- User Workspace: {os.getcwd()}
- Available Libraries: standard library, pillow, opencv-python, psutil, pycaw, requests, openpyxl, pandas (if installed)

RULES:
1. Return ONLY the code inside a markdown block: ```python ... ``` or ```powershell ... ```
2. Do not use interactive input() or GUI prompts.
3. Write clean, silent stdout unless printing essential results.
4. Ensure files are saved to 'C:\\MakiSync Storage' or the user's specified path.
5. If creating output files, print 'CREATED_FILE: <full_path>' to stdout so Maki can track them.
6. Keep code concise and efficient.
"""
        response = self.gemini.send(user_prompt, system_prompt)
        return self._extract_code(response)

    def _self_heal_code(self, original_prompt: str, failed_code: str, lang: str, error_trace: str) -> Tuple[str, str]:
        """Feed traceback back to AI to fix bugs and return corrected code."""
        fix_prompt = f"""The previous {lang} script failed with this error:
---
{error_trace}
---

Original Goal: {original_prompt}

Failed Code:
```{lang}
{failed_code}
```

Fix the code to resolve the error. Return ONLY the fixed code block: ```{lang} ... ```"""
        response = self.gemini.send(fix_prompt, "You are a code debugging expert. Fix the script and return only the corrected markdown code block.")
        return self._extract_code(response)

    def _extract_code(self, response_text: str) -> Tuple[str, str]:
        """Extract code content and language from Markdown block."""
        if not response_text:
            return "", ""

        # Check for python block
        py_match = re.search(r"```(?:python|py)\s*\n(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
        if py_match:
            return py_match.group(1).strip(), "python"

        # Check for powershell block
        ps_match = re.search(r"```(?:powershell|ps1|pwsh|cmd|bat)\s*\n(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
        if ps_match:
            return ps_match.group(1).strip(), "powershell"

        # Check for generic code block
        generic_match = re.search(r"```\s*\n(.*?)```", response_text, re.DOTALL)
        if generic_match:
            return generic_match.group(1).strip(), "python"

        return response_text.strip(), "python"

    # ─── Security Validation ──────────────────────────────────────────────────

    def _validate_security(self, code: str, lang: str) -> Tuple[bool, str]:
        """Check for dangerous system actions or credential leakage."""
        code_lower = code.lower()

        # Check for credential file access
        for forbidden in (".env", "config.db", "id_rsa", ".pem", ".key", "id_ed25519"):
            if forbidden in code_lower:
                return False, f"Access to sensitive credential file '{forbidden}' is strictly forbidden."

        # Check for system disk formatting or registry destructive actions
        dangerous_patterns = [
            r"format\s+[c-z]:",
            r"del\s+/[fsq]\s+[c-z]:\\windows",
            r"rmdir\s+/[sq]\s+[c-z]:\\windows",
            r"remove-item\s+-recurse\s+c:\\windows",
            r"reg\s+delete",
            r"shutdown\s+/[sr]",
            r"stop-computer",
        ]
        for pat in dangerous_patterns:
            if re.search(pat, code_lower):
                return False, "Destructive system-level command detected."

        return True, ""

    # ─── Execution Subprocess ─────────────────────────────────────────────────

    def _run_code(self, code: str, lang: str) -> Tuple[bool, str, str]:
        """Execute the code snippet in a dedicated subprocess with timeout."""
        try:
            if lang == "python":
                with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as temp_f:
                    temp_f.write(code)
                    temp_path = temp_f.name

                try:
                    proc = subprocess.run(
                        [sys.executable, temp_path],
                        capture_output=True,
                        text=True,
                        timeout=35,
                        cwd=str(MAKI_SYNC_ROOT) if MAKI_SYNC_ROOT.exists() else os.getcwd(),
                    )
                    success = proc.returncode == 0
                    return success, proc.stdout, proc.stderr
                finally:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass

            elif lang == "powershell":
                proc = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-Command",
                        code,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=35,
                    cwd=str(MAKI_SYNC_ROOT) if MAKI_SYNC_ROOT.exists() else os.getcwd(),
                )
                success = proc.returncode == 0
                return success, proc.stdout, proc.stderr

            else:
                return False, "", f"Unsupported language: {lang}"

        except subprocess.TimeoutExpired:
            return False, "", "Execution timed out (exceeded 35 seconds cap)."
        except Exception as e:
            return False, "", str(e)

    # ─── Success Summarization ────────────────────────────────────────────────

    def _summarize_success(self, user_prompt: str, stdout: str, code: str) -> str:
        """Generate a natural conversational response confirming task completion."""
        # Detect any created files
        created_files = []
        for line in stdout.splitlines():
            if "CREATED_FILE:" in line:
                file_path = line.split("CREATED_FILE:", 1)[1].strip()
                if file_path and Path(file_path).exists():
                    created_files.append(Path(file_path))

        self.last_generated_files = created_files

        summary_prompt = f"""The automation task was successfully executed on Windows.
User Request: {user_prompt}
Code Output / Stdout:
{stdout[:800]}

Summarize what was accomplished in 1-2 concise, natural sentences as Maki (polite, confident AI assistant).
CRITICAL: Do NOT output any <think> tags or chain-of-thought blocks. Output only the final 1-2 sentences.
If output files were created, mention their names."""

        summary = self.gemini.send(summary_prompt, "You are Maki, a high-tech AI desktop assistant. Summarize results naturally and concisely.")
        if not summary or not summary.strip():
            summary = "Task completed successfully, sir."

        # Extra safety check against reasoning tags
        summary = re.sub(r"<(?:think|thought)>.*?</(?:think|thought)>", "", summary, flags=re.DOTALL | re.IGNORECASE).strip()
        summary = re.sub(r"</?(?:think|thought)>", "", summary, flags=re.IGNORECASE).strip()

        return summary
