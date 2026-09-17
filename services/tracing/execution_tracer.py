"""
MakiAI — Execution Tracer
Thread-safe execution trace logger for all skills, tools, and computer actions.

Adapted from OpenJarvis Trace & Evaluation System.
Saves structured telemetry to `data/logs/execution_traces.jsonl` for debugging,
self-correction, and performance evaluation.
"""

import json
import threading
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

TRACE_LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "logs" / "execution_traces.jsonl"
_LOCK = threading.Lock()


class ExecutionTracer:
    """
    Centralized execution trace logger for MakiAI.
    """

    def __init__(self, log_path: Path = TRACE_LOG_PATH):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_trace(
        self,
        caller: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        success: bool = True,
        result_summary: str = "",
        duration_ms: float = 0.0,
        error: Optional[Exception] = None,
        error_message: Optional[str] = None,
        self_healed: bool = False,
        attempts: int = 1
    ) -> str:
        """
        Record an execution trace event into the JSONL trace log.

        Returns:
            trace_id (str): Unique identifier for this trace.
        """
        trace_id = str(uuid.uuid4())
        now_iso = datetime.now().isoformat()

        err_type = error.__class__.__name__ if error else None
        err_msg = str(error) if error else (error_message or None)
        tb_str = "".join(traceback.format_tb(error.__traceback__)) if error and error.__traceback__ else None

        # Sanitize parameters (remove non-serializable objects)
        sanitized_params = {}
        if parameters:
            for k, v in parameters.items():
                if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                    sanitized_params[k] = v
                else:
                    sanitized_params[k] = str(v)

        trace_record = {
            "trace_id": trace_id,
            "timestamp": now_iso,
            "caller": caller,
            "action": action,
            "parameters": sanitized_params,
            "success": success,
            "result_summary": result_summary[:300] if result_summary else "",
            "duration_ms": round(duration_ms, 2),
            "error_type": err_type,
            "error_message": err_msg,
            "traceback": tb_str,
            "self_healed": self_healed,
            "attempts": attempts,
        }

        with _LOCK:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(trace_record, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[ExecutionTracer] Log error: {e}")

        return trace_id

    def get_recent_traces(self, limit: int = 20, failures_only: bool = False) -> List[Dict[str, Any]]:
        """Return the most recent traces, optionally filtering for failures."""
        if not self.log_path.exists():
            return []

        traces = []
        with _LOCK:
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                record = json.loads(line)
                                if not failures_only or not record.get("success", True):
                                    traces.append(record)
                            except Exception:
                                continue
            except Exception as e:
                print(f"[ExecutionTracer] Read error: {e}")

        return traces[-limit:]

    def get_failure_patterns(self) -> Dict[str, int]:
        """Aggregate recurring error types and actions for self-calibration."""
        failures = self.get_recent_traces(limit=200, failures_only=True)
        patterns: Dict[str, int] = {}
        for f in failures:
            err_type = f.get("error_type") or "Error"
            caller = f.get("caller") or "Unknown"
            action = f.get("action") or "Unknown"
            key = f"{caller}.{action}:{err_type}"
            patterns[key] = patterns.get(key, 0) + 1
        return patterns

    def clear_traces(self) -> None:
        """Clear the trace log."""
        with _LOCK:
            if self.log_path.exists():
                self.log_path.unlink()
