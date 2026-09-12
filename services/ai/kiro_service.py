"""
MakiAI — Kiro CLI Coding Engine Service
Integrates local Kiro CLI (Claude Sonnet 4.5 / DeepSeek 3.2 / Qwen3 Coder)
for high-performance autonomous software engineering, website building,
and code generation tasks.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict


class KiroService:
    """
    Wrapper for the local Kiro CLI.
    Enables MakiAI to delegate complex coding tasks, website scaffolding,
    and script generation directly to Kiro's coding agent.
    """

    DEFAULT_KIRO_PATHS = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Kiro-Cli" / "kiro-cli.exe",
        Path.home() / "AppData" / "Local" / "Kiro-Cli" / "kiro-cli.exe",
    ]

    def __init__(self, executable_path: Optional[str] = None):
        self.exe_path = self._locate_executable(executable_path)
        self._user_email = ""
        self._is_authenticated = False
        if self.exe_path:
            self._check_auth()

    def _locate_executable(self, custom_path: Optional[str] = None) -> Optional[Path]:
        """Find the kiro-cli executable."""
        if custom_path and Path(custom_path).exists():
            return Path(custom_path)

        # Check standard PATH
        which_path = shutil.which("kiro-cli") or shutil.which("kiro")
        if which_path and Path(which_path).exists():
            return Path(which_path)

        # Check known AppData installation paths
        for p in self.DEFAULT_KIRO_PATHS:
            if p.exists():
                return p

        return None

    def is_available(self) -> bool:
        """Check if Kiro CLI is installed and ready."""
        return self.exe_path is not None and self.exe_path.exists()

    def _check_auth(self) -> bool:
        """Verify if the user is logged in to Kiro CLI."""
        if not self.is_available():
            return False
        try:
            res = subprocess.run(
                [str(self.exe_path), "whoami"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            output = res.stdout.strip()
            if "Logged in" in output:
                self._is_authenticated = True
                email_match = re.search(r"Email:\s*([^\r\n]+)", output)
                if email_match:
                    self._user_email = email_match.group(1).strip()
                print(f"[KiroService] Kiro CLI authenticated ({self._user_email or 'active session'}).")
                return True
        except Exception as e:
            print(f"[KiroService] Auth check warning: {e}")
        self._is_authenticated = False
        return False

    def get_status(self) -> Dict[str, str]:
        """Return diagnostic status for UI and logs."""
        return {
            "available": "true" if self.is_available() else "false",
            "authenticated": "true" if self._is_authenticated else "false",
            "account": self._user_email or "Not logged in",
            "executable": str(self.exe_path) if self.exe_path else "Not found",
        }

    def _resolve_project_dir(self, project_name: str, custom_dir: Optional[str] = None) -> Path:
        """
        Resolve the source code workspace directory following the user's C:\\development structure
        and C:\\Knowledge-Base\\projects\\<Project>\\filepath.md definitions.
        """
        if custom_dir:
            return Path(custom_dir)

        # 1. Check if filepath.md defines Primary Path in Knowledge Base
        filepath_doc = Path(r"C:\Knowledge-Base\projects") / project_name / "filepath.md"
        if filepath_doc.exists():
            try:
                content = filepath_doc.read_text(encoding="utf-8", errors="ignore")
                match = re.search(r"\*\*Primary Path:\*\*\s*`([^`]+)`", content)
                if match:
                    resolved = Path(match.group(1).strip())
                    return resolved
            except Exception as e:
                print(f"[KiroService] Warning reading {filepath_doc}: {e}")

        # 2. Check existing development directories
        dev_root = Path(r"C:\development")
        if dev_root.exists():
            tech_stacks = ["NextJS", "Python", "laravel", "Springboot", "C#", "Shopify", "React Native", "CLI", "Board"]
            for stack in tech_stacks:
                candidate = dev_root / stack / project_name
                if candidate.exists():
                    return candidate

        # 3. Default to C:\development\NextJS\<project_name> for web apps, or C:\development\<project_name>
        default_dir = dev_root / "NextJS" / project_name if (dev_root / "NextJS").exists() else (dev_root / project_name)
        return default_dir

    def generate_code(
        self,
        prompt: str,
        working_dir: Optional[str] = None,
        model: str = "auto",
        timeout: int = 180,
        kb_context: str = "",
        project_name: str = "Project",
    ) -> str:
        """
        Execute a coding prompt through Kiro CLI in headless non-interactive mode.
        """
        if not self.is_available():
            return "Kiro CLI is not installed or detected on your system, sir."

        cwd = self._resolve_project_dir(project_name, working_dir)
        cwd.mkdir(parents=True, exist_ok=True)

        full_prompt = prompt.strip()
        if kb_context and len(kb_context.strip()) > 20:
            full_prompt = (
                f"{prompt}\n\n"
                f"### Knowledge Base Architecture & Specifications:\n"
                f"{kb_context.strip()}"
            )

        cmd = [
            str(self.exe_path),
            "chat",
            "--no-interactive",
            "--trust-all-tools",
            "--model",
            model,
            full_prompt,
        ]

        try:
            print(f"[KiroService] Executing coding task with Kiro CLI in {cwd} (Model: {model})...")
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            raw_out = proc.stdout if proc.stdout else proc.stderr
            cleaned = self._clean_output(raw_out)
            return cleaned or "Kiro CLI finished the task, sir."

        except subprocess.TimeoutExpired:
            return "Kiro CLI task timed out while generating the code, sir."
        except Exception as e:
            print(f"[KiroService] Execution error: {e}")
            return f"Encountered an error running Kiro CLI: {e}"

    def launch_interactive_session(
        self,
        working_dir: Optional[str] = None,
        initial_prompt: str = "",
        project_name: str = "Project",
    ) -> str:
        """
        Open a visible, interactive terminal window running Kiro CLI
        so the user can watch Kiro code and execute tools live.
        Ensures Knowledge Base plans are copied and explicitly referenced.
        """
        if not self.is_available():
            return "Kiro CLI is not installed or detected on your system, sir."

        cwd = self._resolve_project_dir(project_name, working_dir)
        cwd.mkdir(parents=True, exist_ok=True)

        # 1. Sync project specs from Knowledge Base into project directory
        kb_project_dir = Path(r"C:\Knowledge-Base\projects") / project_name
        synced_files = []
        if kb_project_dir.exists():
            for fname in ["overview.md", "PLAN.md", "plan.md", "architecture.md", "decisions.md", "ui.md", "progress.md"]:
                src = kb_project_dir / fname
                if src.exists():
                    try:
                        dest = cwd / src.name
                        shutil.copy2(src, dest)
                        synced_files.append(src.name)
                    except Exception as e:
                        print(f"[KiroService] Failed to copy {fname}: {e}")

        if synced_files:
            print(f"[KiroService] Synced Knowledge Base specs to {cwd}: {synced_files}")

        # 2. Formulate strict Knowledge Base instruction for Kiro CLI
        kb_instruction = (
            f"Read overview.md, plan.md, architecture.md, and ui.md in this directory and coding standards at C:\\Knowledge-Base\\config\\coding-standards.md. "
        )
        if initial_prompt and initial_prompt.strip():
            prompt_to_use = f"{kb_instruction}Task: {initial_prompt.strip()}"
        else:
            prompt_to_use = f"{kb_instruction}Build the {project_name} application following the architecture and product specifications."

        exe_str = str(self.exe_path)
        launcher_file = cwd / "run_kiro.bat"

        # Create clean launcher batch file to avoid shell quotation parsing issues
        with open(launcher_file, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write(f"title MakiAI - Kiro Coding Engine: {project_name}\n")
            f.write(f'cd /d "{cwd}"\n')
            f.write("echo ========================================================\n")
            f.write(f"echo        MakiAI Kiro Coding Engine: {project_name}\n")
            f.write("echo ========================================================\n")
            f.write(f"echo Working Directory: {cwd}\n")
            f.write("echo Initializing Kiro CLI interactive session with Knowledge Base...\n\n")
            clean_p = prompt_to_use.replace("\r", " ").replace("\n", " ").replace('"', '')
            f.write(f'"{exe_str}" chat "{clean_p}"\n')
            f.write("pause\n")

        try:
            subprocess.Popen(f'start "" "{launcher_file}"', shell=True)
            return f"Opening Kiro CLI in an interactive terminal for {project_name}, sir. You can watch the live coding progress now."
        except Exception as e:
            print(f"[KiroService] Failed to launch interactive terminal: {e}")
            return f"Encountered an issue opening the Kiro terminal: {e}"

    def _clean_output(self, text: str) -> str:
        """Strip Kiro CLI startup warnings, banners, and credit footers."""
        if not text:
            return ""

        # Remove "All tools are now trusted (!)..." banner
        text = re.sub(r"All tools are now trusted.*?Learn more at https://[^\r\n]+\n+", "", text, flags=re.DOTALL)

        # Remove credit usage footer "▸ Credits: ... • Time: ..."
        text = re.sub(r"▸\s*Credits:[^\r\n]+", "", text)

        # Remove ASCII ANSI color escape codes
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        text = ansi_escape.sub("", text)

        return text.strip()
