"""
MakiAI — Cloud Apps & SaaS Workspace Skill (composio_skill.py)
Powered by Composio (ComposioHQ/composio).

Capabilities:
  1. Google Docs: Create documents, read document contents, append text.
  2. Google Calendar: Check upcoming events, create meetings and appointments.
  3. Gmail: Check unread messages, draft and send emails.
  4. Notion / Trello: Create pages, manage task cards, query databases.
  5. GitHub: Create issues, search repositories.
  6. Zero-OAuth Setup: 1-Click web auth links for any disconnected cloud app.
"""

import os
import re
import json
from typing import Optional, Tuple, Dict, Any

from skills.base_skill import BaseSkill
from services.cloud.composio_service import ComposioService


class ComposioSkill(BaseSkill):
    """
    Cloud app and SaaS workspace integration engine for MakiAI.
    """

    SKILL_ID = "composio"
    REQUIRED_FILES = [
        "user/profile.md",
        "system/capabilities.md",
    ]

    def __init__(self, gemini_service, context_builder, kb_reader, kb_writer, composio_service: Optional[ComposioService] = None):
        super().__init__(gemini_service, context_builder, kb_reader, kb_writer)
        self.composio = composio_service or ComposioService()

    def execute(self, text: str) -> str:
        """
        Main execution flow:
          1. Check if Composio API key is present.
          2. Parse user intent into Composio action & parameters.
          3. Execute via Composio.
          4. Format response as natural conversational Maki dialogue.
        """
        clean_text = text.strip()
        print(f"[ComposioSkill] Processing cloud request: '{clean_text}'")

        # Step 1: Check configuration
        if not self.composio.is_configured():
            return (
                "Sir, your Composio Cloud integration is ready, but requires a free API key to communicate with Google Workspace and cloud apps.\n\n"
                "To enable it:\n"
                "1. Get your free key at https://app.composio.dev\n"
                "2. Add COMPOSIO_API_KEY=your_key to your .env file."
            )

        # Step 2: Determine App and Action using AI
        plan = self._plan_cloud_action(clean_text)
        if not plan or not plan.get("action"):
            return "I couldn't determine which cloud action to take for that request, sir. Could you clarify if you'd like to use Google Docs, Calendar, Gmail, or Notion?"

        action_slug = plan.get("action", "")
        arguments = plan.get("arguments", {})
        app_name = plan.get("app", "google")

        # Normalize common action slug aliases
        if action_slug in ("GMAIL_SEND_MAIL", "GMAIL_SEND_MESSAGE", "GMAIL_SEND"):
            action_slug = "GMAIL_SEND_EMAIL"
        if action_slug in ("GMAIL_CHECK_EMAILS", "GMAIL_GET_EMAILS", "GMAIL_LIST_EMAIL"):
            action_slug = "GMAIL_FETCH_EMAILS"

        # Normalize argument aliases
        if "to" in arguments and "recipient_email" not in arguments:
            arguments["recipient_email"] = arguments.pop("to")
        if "message" in arguments and "body" not in arguments:
            arguments["body"] = arguments.pop("message")

        print(f"[ComposioSkill] Executing cloud action: {action_slug} with args: {arguments}")

        # Step 3: Execute Action
        result = self.composio.execute_action(action_slug, arguments)

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            err_lower = error_msg.lower()

            # 1. Invalid API Key error
            if "invalid api key" in err_lower or "apikey_invalidapikey" in err_lower or "401" in err_lower:
                return (
                    "Sir, your Composio API key appears to be invalid or expired.\n"
                    "Please grab a new API key from https://dashboard.composio.dev/settings/api-keys and update COMPOSIO_API_KEY in your .env file."
                )

            # 2. Account not connected yet
            if "not connected" in err_lower or "unauthorized" in err_lower or "no connected account" in err_lower or "connectedaccountnotfound" in err_lower or "no active connection" in err_lower:
                auth_url = self.composio.get_auth_url(app_name)
                return (
                    f"Sir, your {app_name.capitalize()} account is not connected yet in Composio.\n"
                    f"Please click here to connect your account: {auth_url}"
                )

            # Clean any verbose JSON errors
            msg_match = re.search(r"'message':\s*'([^']+)'", error_msg)
            if msg_match:
                clean_err = msg_match.group(1)
            else:
                clean_err = re.sub(r"\{.*?\}", "", error_msg).strip()
                if not clean_err:
                    clean_err = error_msg[:120]
            return f"I had trouble executing the {app_name.capitalize()} action, sir: {clean_err}"

        # Step 4: Summarize Result
        return self._summarize_result(clean_text, result.get("data", {}), app_name)

    def _plan_cloud_action(self, user_prompt: str) -> Dict[str, Any]:
        """Use AI to translate natural language into Composio action slug and arguments."""
        system_prompt = """You are MakiAI's Cloud Workspace Planner.
Translate the user's request into a Composio action slug and parameter JSON.

Supported Common Apps & Action Slugs:
- Google Docs: GOOGLEDOCS_CREATE_DOCUMENT, GOOGLEDOCS_GET_DOCUMENT, GOOGLEDOCS_INSERT_TEXT
- Google Calendar: GOOGLECALENDAR_FIND_EVENTS, GOOGLECALENDAR_CREATE_EVENT, GOOGLECALENDAR_LIST_EVENTS
- Gmail: GMAIL_LIST_MESSAGES, GMAIL_SEND_MAIL, GMAIL_CREATE_DRAFT
- Notion: NOTION_CREATE_NOTION_PAGE, NOTION_SEARCH_NOTION_PAGE
- Trello: TRELLO_CREATE_CARD, TRELLO_GET_BOARDS
- GitHub: GITHUB_CREATE_ISSUE, GITHUB_SEARCH_REPOSITORIES

RULES:
1. Return ONLY a valid JSON object:
{
  "app": "googledocs" | "googlecalendar" | "gmail" | "notion" | "trello" | "github",
  "action": "ACTION_SLUG",
  "arguments": { ... }
}
2. Do not include markdown code block quotes around the JSON if possible, or use standard ```json.
3. Fill required arguments intelligently based on the user's prompt."""

        response = self.gemini.send(user_prompt, system_prompt)
        return self._extract_json(response)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON from AI response."""
        if not text:
            return {}
        try:
            # Check for ```json block
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))

            # Check for raw JSON {}
            match_raw = re.search(r"(\{.*\})", text, re.DOTALL)
            if match_raw:
                return json.loads(match_raw.group(1))

            return json.loads(text.strip())
        except Exception:
            return {}

    def _summarize_result(self, user_prompt: str, result_data: Any, app_name: str) -> str:
        """Generate a natural conversational response confirming the cloud action."""
        str_data = str(result_data)
        if len(str_data) > 1000:
            str_data = str_data[:950] + "..."

        summary_prompt = f"""The cloud action for {app_name} was successfully executed.
User Request: {user_prompt}
Cloud Result Data:
{str_data}

Summarize what was completed in 1-2 natural, polite sentences as Maki (AI assistant).
Address the user as 'sir'. Do NOT output <think> tags."""

        summary = self.gemini.send(summary_prompt, "You are Maki, a high-tech AI personal assistant. Summarize cloud results concisely.")
        if not summary or not summary.strip():
            summary = f"I've completed your {app_name.capitalize()} request successfully, sir."

        # Extra safety check against reasoning tags
        summary = re.sub(r"<(?:think|thought)>.*?</(?:think|thought)>", "", summary, flags=re.DOTALL | re.IGNORECASE).strip()
        summary = re.sub(r"</?(?:think|thought)>", "", summary, flags=re.IGNORECASE).strip()

        return summary
