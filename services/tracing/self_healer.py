"""
MakiAI — Self-Healing Engine
Automatic error capture, AI-driven parameter self-correction, and retry loop.

Adapted from OpenJarvis Self-Healing and Trace Correction.
Allows tools, APIs, and action pipelines to recover from malformed parameters,
transient failures, or unexpected response formats on the fly.
"""

import json
import re
import time
import traceback
from typing import Callable, Dict, Any, Optional, Tuple

from services.tracing.execution_tracer import ExecutionTracer

SELF_HEALING_PROMPT = """You are the Self-Healing Diagnostic Engine for MakiAI.
An automated tool or API action failed with an error. Your job is to analyze the error, the failed input parameters, and the original user intent, then generate CORRECTED parameters so the action succeeds on retry.

ORIGINAL USER INTENT:
{user_intent}

ACTION NAME:
{action_name}

FAILED PARAMETERS:
{failed_params}

ERROR MESSAGE / TRACEBACK:
{error_info}

INSTRUCTIONS:
1. Identify why the action failed (e.g., malformed email, missing required field, type mismatch, wrong path format).
2. Generate corrected, valid parameters matching the tool's requirements.
3. Return ONLY a valid JSON object in the following format with no markdown commentary:

OUTPUT FORMAT:
{{
  "can_recover": true,
  "fixed_params": {{
    "param_name": "corrected_value"
  }},
  "diagnosis": "Brief 1-sentence explanation of what was fixed"
}}
"""


class SelfHealingEngine:
    """
    Executes callable actions with automated trace logging, AI parameter self-correction,
    and retry loops.
    """

    def __init__(self, tracer: Optional[ExecutionTracer] = None):
        self.tracer = tracer or ExecutionTracer()

    def execute_with_retry(
        self,
        action_fn: Callable[..., Any],
        action_name: str,
        caller: str = "agent",
        params: Optional[Dict[str, Any]] = None,
        user_intent: str = "",
        ai_service: Optional[Any] = None,
        max_retries: int = 2,
        is_success_fn: Optional[Callable[[Any], bool]] = None
    ) -> Tuple[bool, Any, str]:
        """
        Execute an action with automatic self-healing.

        Args:
            action_fn: The callable function to execute.
            action_name: Descriptive name of the action (e.g. 'send_gmail', 'file_write').
            caller: Component calling the action (e.g. 'ComposioSkill', 'FileManager').
            params: Dictionary of arguments passed to action_fn.
            user_intent: Natural language prompt or goal of the user.
            ai_service: AI service (GeminiService/GroqService) for generating fixes.
            max_retries: Maximum number of self-correction retry attempts (default 2).
            is_success_fn: Optional custom validator for return value.

        Returns:
            Tuple[bool, Any, str]: (success, result_or_none, status_message)
        """
        current_params = dict(params or {})
        last_error_str = ""
        last_exception = None
        start_total = time.perf_counter()

        for attempt in range(1, max_retries + 2):
            t0 = time.perf_counter()
            try:
                # Execute action
                result = action_fn(**current_params)
                duration = (time.perf_counter() - t0) * 1000

                # Validate result
                is_ok = True
                if is_success_fn:
                    is_ok = is_success_fn(result)
                elif isinstance(result, dict) and result.get("success") is False:
                    is_ok = False
                    last_error_str = result.get("error", "Action returned failure status.")

                if is_ok:
                    self_healed = (attempt > 1)
                    total_dur = (time.perf_counter() - start_total) * 1000
                    self.tracer.log_trace(
                        caller=caller,
                        action=action_name,
                        parameters=current_params,
                        success=True,
                        result_summary=str(result),
                        duration_ms=total_dur,
                        self_healed=self_healed,
                        attempts=attempt
                    )
                    msg = f"Action '{action_name}' succeeded" + (f" after self-healing (attempt {attempt})" if self_healed else "")
                    return True, result, msg

            except Exception as e:
                duration = (time.perf_counter() - t0) * 1000
                last_exception = e
                last_error_str = f"{e.__class__.__name__}: {str(e)}\n{traceback.format_exc()}"

            # If failed and retries remain, attempt AI self-healing
            if attempt <= max_retries and ai_service:
                print(f"[SelfHealingEngine] Action '{action_name}' failed on attempt {attempt}. Attempting self-healing...")
                fixed_params, diagnosis = self._diagnose_and_fix(
                    action_name=action_name,
                    failed_params=current_params,
                    error_info=last_error_str,
                    user_intent=user_intent,
                    ai_service=ai_service
                )

                if fixed_params:
                    print(f"[SelfHealingEngine] Diagnosis: {diagnosis}. Retrying with corrected parameters: {fixed_params}")
                    current_params.update(fixed_params)
                    continue

        # All attempts exhausted
        total_dur = (time.perf_counter() - start_total) * 1000
        self.tracer.log_trace(
            caller=caller,
            action=action_name,
            parameters=current_params,
            success=False,
            result_summary="",
            duration_ms=total_dur,
            error=last_exception,
            error_message=last_error_str,
            self_healed=False,
            attempts=max_retries + 1
        )

        fail_msg = f"I was unable to complete '{action_name}' after {max_retries + 1} attempts due to: {last_error_str.splitlines()[0] if last_error_str else 'Unknown error'}."
        return False, None, fail_msg

    def _diagnose_and_fix(
        self,
        action_name: str,
        failed_params: Dict[str, Any],
        error_info: str,
        user_intent: str,
        ai_service: Any
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Query AI to diagnose error and produce fixed parameters."""
        prompt = SELF_HEALING_PROMPT.format(
            action_name=action_name,
            failed_params=json.dumps(failed_params, indent=2, default=str),
            error_info=error_info[:1000],
            user_intent=user_intent or "Execute the requested action correctly"
        )

        try:
            raw_response = ai_service.send(prompt, "")
            if not raw_response:
                return None, ""

            clean_json = raw_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                clean_json = re.sub(r"\s*```$", "", clean_json)

            data = json.loads(clean_json.strip())
            if data.get("can_recover") and data.get("fixed_params"):
                return data["fixed_params"], data.get("diagnosis", "Parameters corrected")
            return None, data.get("diagnosis", "Cannot recover automatically")

        except Exception as e:
            print(f"[SelfHealingEngine] Diagnostic error: {e}")
            return None, str(e)
