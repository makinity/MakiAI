"""
MakiAI — Self-Healing Execution Trace & Resiliency Service
Inspired by OpenJarvis execution trace loops.

Logs all tool/skill execution errors and provides automated self-healing / self-correction
turns when a tool or command fails.
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRACE_LOG_PATH = PROJECT_ROOT / "data" / "logs" / "execution_traces.jsonl"
_TRACE_LOCK = threading.Lock()


class ExecutionTraceService:
    """
    Self-healing trace monitor and error feedback loop for MakiAI.
    """

    def __init__(self, log_path: Path = TRACE_LOG_PATH):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_trace(
        self,
        command: str,
        handler: str,
        success: bool,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Asynchronously log an execution trace event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "handler": handler,
            "success": success,
            "error": error,
            "duration_ms": round(duration_ms, 2),
            "metadata": metadata or {}
        }

        def _worker():
            try:
                with _TRACE_LOCK:
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[ExecutionTrace] Failed to write trace: {e}")

        threading.Thread(target=_worker, daemon=True, name="TraceLogger").start()

    def get_recent_failures(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the most recent tool execution failures."""
        if not self.log_path.exists():
            return []

        failures = []
        try:
            with _TRACE_LOCK:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                if not data.get("success"):
                                    failures.append(data)
                            except Exception:
                                pass
            return failures[-limit:]
        except Exception:
            return []

    def self_heal(self, command: str, handler: str, error_msg: str, ai_service) -> str:
        """
        Self-healing error recovery loop:
        Feeds the exact failure trace to the AI brain to produce an intelligent,
        conversational self-correction or diagnostic explanation for the user.
        """
        self.log_trace(command=command, handler=handler, success=False, error=error_msg)

        if not ai_service:
            return f"I encountered an issue executing that command, sir: {error_msg}."

        system_prompt = (
            "You are MakiAI — a hyper-intelligent, polite personal AI assistant for sir. "
            "A system tool or command encountered an error during execution. "
            "Analyze the error trace and provide a concise, spoken self-corrected explanation "
            "or practical alternative directly to sir. Do not mention technical stack traces or internal code."
        )

        user_prompt = (
            f"User Command: \"{command}\"\n"
            f"Failed Handler: {handler}\n"
            f"Error Detail: {error_msg}\n\n"
            f"Please provide a helpful, natural spoken response explaining what happened and what sir can do next."
        )

        try:
            response = ai_service.send(user_prompt, system_prompt)
            return response.strip()
        except Exception as e:
            return f"Sir, I ran into a minor issue while running '{command}': {error_msg}."
