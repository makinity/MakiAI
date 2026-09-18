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
        self.ui_bridge = None
        self._cached_emails = []
        self._cached_messages = []
        self._last_context_app = "gmail"

    def set_ui_bridge(self, ui_bridge) -> None:
        """Connect UI bridge to trigger interactive Gmail composer modal."""
        self.ui_bridge = ui_bridge

    def execute(self, text: str) -> str:
        """
        Main execution flow:
          1. Check if Composio API key is present.
          2. Check for interactive follow-ups ("read it", "reply").
          3. Parse user intent into Composio action & parameters.
          4. If email drafting, open interactive modal on UI.
          5. Execute via Composio or summarize.
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

        # Step 1.5: Direct follow-up handling
        p_lower = clean_text.lower()
        is_read_followup = (
            any(w in p_lower for w in ("read", "open", "tell me what it says", "what does it say", "what did they say", "what is in", "what is the email", "what is the message", "what i meant is read"))
            and any(w in p_lower for w in ("it", "email", "emails", "gmail", "message", "messages", "inbox", "body", "details", "that", "latest"))
        ) or any(phrase in p_lower for phrase in (
            "read it", "i want you to read it", "please read it", "read the latest", "read latest message",
            "read the message", "read the email", "read the latest message", "what does it say", "what does it say?", "read latest"
        ))

        if is_read_followup and not any(w in p_lower for w in ("reply", "respond", "send", "draft", "write")):
            return self._handle_read_followup(clean_text)

        # Step 1.6: Facebook Post / Comment Deletion & Editing Direct Interceptions
        if any(w in p_lower for w in ("facebook", "fb", "makisync", "page", "post", "comment")):
            # Delete post
            if any(w in p_lower for w in ("delete", "remove")) and any(w in p_lower for w in ("post", "posts")):
                del_res = self.composio.delete_facebook_post()
                if del_res.get("success"):
                    return "I've successfully deleted the latest post on your MakiSync Facebook page, sir."
                return f"I had trouble deleting the post, sir: {del_res.get('error', 'Please check permissions')}"

            # Delete comment
            if any(w in p_lower for w in ("delete", "remove")) and any(w in p_lower for w in ("comment", "comments")):
                del_comm = self.composio.delete_facebook_comment()
                if del_comm.get("success"):
                    return "I've successfully deleted the latest comment from your Facebook post, sir."
                return f"I had trouble deleting the comment, sir: {del_comm.get('error', 'No comments found')}"

            # Edit comment
            if any(w in p_lower for w in ("edit", "update", "change")) and any(w in p_lower for w in ("comment", "comments")):
                new_msg = re.sub(r"^.*?(?:to\s+say|saying|say|to|with)\s+", "", clean_text, flags=re.IGNORECASE).strip(" '\"\t\n\r.")
                if new_msg:
                    edit_res = self.composio.edit_facebook_comment(new_msg)
                    if edit_res.get("success"):
                        return f"I've updated the comment on your Facebook post to: \"{new_msg}\", sir."
                    return f"I had trouble updating the comment, sir: {edit_res.get('error', 'No comments found')}"

            # Create comment
            if any(w in p_lower for w in ("comment on", "add a comment", "post a comment", "leave a comment")):
                comm_msg = re.sub(r"^.*?(?:saying|say|with|that)\s+", "", clean_text, flags=re.IGNORECASE).strip(" '\"\t\n\r.")
                if comm_msg:
                    add_comm = self.composio.create_facebook_comment(comm_msg)
                    if add_comm.get("success"):
                        return f"I've posted your comment \"{comm_msg}\" on your latest Facebook post, sir."
                    return f"I had trouble adding the comment, sir: {add_comm.get('error')}"

        is_reply_followup = any(w in p_lower for w in ("reply", "respond", "replying", "send it directly")) or bool(re.search(r"\b(?:draft|write|compose|send)\s+(?:a\s+)?(?:reply|response)\b", p_lower))
        if is_reply_followup:
            return self._handle_reply_followup(clean_text)

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
        if action_slug in ("GMAIL_CHECK_EMAILS", "GMAIL_GET_EMAILS", "GMAIL_LIST_EMAIL", "GMAIL_LIST_MESSAGES", "GMAIL_GET_MESSAGE", "GMAIL_GET_LATEST_MESSAGE", "GMAIL_FETCH_MESSAGES", "GMAIL_READ_EMAIL", "GMAIL_READ_MESSAGE"):
            action_slug = "GMAIL_FETCH_EMAILS"
        if action_slug in ("FACEBOOK_PAGE_GET_MESSAGES", "FACEBOOK_PAGE_LIST_CONVERSATIONS", "MESSENGER_GET_MESSAGES", "FACEBOOK_GET_MESSAGES", "FACEBOOK_CHECK_MESSAGES"):
            action_slug = "FACEBOOK_GET_PAGE_CONVERSATIONS"
        if action_slug in ("FACEBOOK_CREATE_PAGE_POST", "FACEBOOK_POST"):
            action_slug = "FACEBOOK_CREATE_POST"
        if action_slug == "FACEBOOK_CREATE_COMMENT" and not arguments.get("object_id"):
            action_slug = "FACEBOOK_CREATE_POST"

        # Normalize argument aliases
        if "to" in arguments and "recipient_email" not in arguments:
            arguments["recipient_email"] = arguments.pop("to")
        if "message" in arguments and "body" not in arguments and "GMAIL" in action_slug:
            arguments["body"] = arguments.pop("message")
        if "maxResults" in arguments and "max_results" not in arguments:
            arguments["max_results"] = arguments.pop("maxResults")
        if action_slug == "GMAIL_FETCH_EMAILS" and "messageId" in arguments:
            arguments.pop("messageId", None)

        # Step 2.5: If email composition / send and UI bridge connected, trigger Modal
        if action_slug in ("GMAIL_SEND_EMAIL", "GMAIL_CREATE_DRAFT") and hasattr(self, "ui_bridge") and self.ui_bridge:
            import time
            draft = {
                "id": f"mail_{int(time.time())}",
                "to": arguments.get("recipient_email", ""),
                "subject": arguments.get("subject", "Project Update"),
                "body": arguments.get("body", clean_text),
            }
            self.ui_bridge.set_active_modal("composio_email", draft)
            return f"I've drafted your email to {draft['to'] or 'the recipient'}, sir. Please review or edit the message on your screen before sending."

        # Step 2.6: Auto-resolve Facebook page_id if missing or string name
        if action_slug.startswith("FACEBOOK_") and action_slug != "FACEBOOK_LIST_MANAGED_PAGES":
            page_id = str(arguments.get("page_id", "")).strip()
            if not page_id or not page_id.isdigit():
                pages_res = self.composio.execute_action("FACEBOOK_LIST_MANAGED_PAGES", {})
                if pages_res.get("success"):
                    pages_data = pages_res.get("data", {})
                    p_list = pages_data.get("data", []) if isinstance(pages_data, dict) else []
                    target_pid = None
                    # Search by name or default to first managed page
                    for p in p_list:
                        if isinstance(p, dict):
                            p_name = p.get("name", "").lower()
                            if "makisync" in p_name or (page_id and page_id.lower() in p_name):
                                target_pid = str(p.get("id"))
                                break
                    if not target_pid and p_list and isinstance(p_list[0], dict):
                        target_pid = str(p_list[0].get("id"))
                    if target_pid:
                        arguments["page_id"] = target_pid

        print(f"[ComposioSkill] Executing cloud action: {action_slug} with args: {arguments}")

        # Step 3: Execute Action with Self-Healing Engine
        def _call_composio(**kw):
            return self.composio.execute_action(action_slug, kw)

        is_ok, result, status_msg = self.self_healer.execute_with_retry(
            action_fn=_call_composio,
            action_name=action_slug,
            caller="ComposioSkill",
            params=arguments,
            user_intent=clean_text,
            ai_service=self.gemini,
            max_retries=2,
            is_success_fn=lambda r: bool(isinstance(r, dict) and r.get("success", False))
        )

        if not result:
            result = {"success": False, "error": status_msg}

        # Step 3.5: If page conversations retrieved, fetch latest messages details
        if result.get("success") and action_slug == "FACEBOOK_GET_PAGE_CONVERSATIONS":
            self._last_context_app = "facebook"
            conv_data = result.get("data", {})
            convs = conv_data.get("data", []) if isinstance(conv_data, dict) else []
            if convs and isinstance(convs[0], dict):
                top_conv_id = convs[0].get("id")
                page_id = arguments.get("page_id")
                if top_conv_id and page_id:
                    msg_res = self.composio.execute_action(
                        "FACEBOOK_GET_CONVERSATION_MESSAGES",
                        {"page_id": page_id, "conversation_id": top_conv_id}
                    )
                    if msg_res.get("success"):
                        raw_msgs = msg_res.get("data", {}).get("data", [])
                        # Ensure newest messages come first (Graph API created_time descending)
                        raw_msgs.sort(key=lambda m: m.get("created_time", ""), reverse=True)
                        self._cached_messages = raw_msgs
                        incoming = [m for m in self._cached_messages if str(m.get("from", {}).get("id")) != "1129268013603196" and m.get("from", {}).get("name") != "MakiSync"]
                        self._cached_incoming_messages = incoming
                        result["data"] = {
                            "conversations": convs[:3],
                            "latest_messages": incoming[:5] if incoming else self._cached_messages[:5],
                            "all_messages": self._cached_messages[:5],
                        }

        if result.get("success") and action_slug == "GMAIL_FETCH_EMAILS":
            self._last_context_app = "gmail"
            self._cached_emails = result.get("data", {}).get("messages", [])

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
- Gmail: GMAIL_LIST_MESSAGES, GMAIL_SEND_EMAIL, GMAIL_CREATE_DRAFT, GMAIL_FETCH_EMAILS
- Facebook Page / Messenger: FACEBOOK_GET_PAGE_CONVERSATIONS, FACEBOOK_GET_PAGE_POSTS, FACEBOOK_CREATE_POST, FACEBOOK_CREATE_PHOTO_POST, FACEBOOK_CREATE_COMMENT, FACEBOOK_LIST_MANAGED_PAGES
- Notion: NOTION_CREATE_NOTION_PAGE, NOTION_SEARCH_NOTION_PAGE
- Trello: TRELLO_CREATE_CARD, TRELLO_GET_BOARDS
- GitHub: GITHUB_CREATE_ISSUE, GITHUB_SEARCH_REPOSITORIES

RULES:
1. Return ONLY a valid JSON object:
{
  "app": "googledocs" | "googlecalendar" | "gmail" | "facebook" | "messenger" | "notion" | "trello" | "github",
  "action": "ACTION_SLUG",
  "arguments": { ... }
}
2. For Facebook posts, put the text content in arguments: {"message": "..."}.
3. For Facebook messages or inbox checks, use action: "FACEBOOK_GET_PAGE_CONVERSATIONS".
4. Do not include markdown code block quotes around the JSON if possible, or use standard ```json.
5. Fill required arguments intelligently based on the user's prompt."""

        response = self.gemini.send(user_prompt, system_prompt)
        extracted = self._extract_json(response)
        if extracted and extracted.get("action"):
            return extracted

        # Deterministic Heuristic Fallbacks (if LLM is offline or in stub mode)
        p_lower = user_prompt.lower()
        if any(w in p_lower for w in ("makisync", "facebook", "fb", "messenger")):
            if any(w in p_lower for w in ("post", "publish", "create post", "share")) and not any(w in p_lower for w in ("what", "read", "check", "get")):
                post_text = re.sub(r"^.*?(?:post|saying|say)\s+", "", user_prompt, flags=re.IGNORECASE).strip(" '\"\t\n\r")
                return {"app": "facebook", "action": "FACEBOOK_CREATE_POST", "arguments": {"message": post_text or user_prompt, "page_id": "MakiSync"}}
            if any(w in p_lower for w in ("say", "said", "message", "messages", "inbox", "conversation", "conversations", "unread", "chat", "check", "read", "view", "visitor", "user", "who")):
                return {"app": "facebook", "action": "FACEBOOK_GET_PAGE_CONVERSATIONS", "arguments": {"page_id": "MakiSync"}}
            if any(w in p_lower for w in ("post", "posts", "feed", "timeline")):
                return {"app": "facebook", "action": "FACEBOOK_GET_PAGE_POSTS", "arguments": {"page_id": "MakiSync"}}

        if any(w in p_lower for w in ("gmail", "email", "emails", "inbox", "mail")):
            has_to_email = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", user_prompt))
            if any(w in p_lower for w in ("send", "write", "draft", "compose", "sample", "test email", "create")) or has_to_email:
                email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", user_prompt)
                to_addr = email_match.group(0) if email_match else ""
                subj_match = re.search(r"\babout\s+(.+)$", user_prompt, re.IGNORECASE)
                subj = subj_match.group(1).strip() if subj_match else "MakiAI Update"
                
                # Clean prompt to create meaningful body if user didn't write a full letter
                app_name = os.getenv("APP_NAME", "MakiAI")
                user_name = os.getenv("USER_NAME", "User")
                clean_body = re.sub(r"^(?:draft|send|write|compose|sample)\s+(?:an?\s+)?(?:test\s+)?(?:email|gmail|message)\s+(?:to\s+[\w\.-]+@[\w\.-]+\.\w+\s*)?(?:about\s+[^,\.]+)?", "", user_prompt, flags=re.IGNORECASE).strip(" '\"\t\n\r:-")
                body_content = clean_body if len(clean_body) > 10 else f"Hello,\n\nThis is a sample update sent via {app_name}.\n\nBest regards,\n{user_name}"

                return {
                    "app": "gmail",
                    "action": "GMAIL_SEND_EMAIL",
                    "arguments": {
                        "recipient_email": to_addr,
                        "subject": subj,
                        "body": body_content
                    }
                }
            return {"app": "gmail", "action": "GMAIL_FETCH_EMAILS", "arguments": {}}

        if any(w in p_lower for w in ("calendar", "gcal", "meeting", "events")):
            return {"app": "googlecalendar", "action": "GOOGLECALENDAR_FIND_EVENTS", "arguments": {}}

        return {}

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

    def _handle_read_followup(self, user_prompt: str) -> str:
        """Read the full content / body of the latest email or Facebook message."""
        p_lower = user_prompt.lower()
        if any(w in p_lower for w in ("facebook", "messenger", "fb", "page", "makisync")):
            target_app = "facebook"
        elif any(w in p_lower for w in ("gmail", "email", "emails", "inbox", "mail")):
            target_app = "gmail"
        else:
            target_app = self._last_context_app

        if target_app == "facebook":
            if not getattr(self, "_cached_incoming_messages", None) and not self._cached_messages:
                self.execute("check messages on MakiSync")
            incoming = getattr(self, "_cached_incoming_messages", []) or [m for m in self._cached_messages if str(m.get("from", {}).get("id")) != "1129268013603196" and m.get("from", {}).get("name") != "MakiSync"]
            if incoming:
                incoming.sort(key=lambda m: m.get("created_time", ""), reverse=True)
                top_m = incoming[0]
                sender = top_m.get("from", {}).get("name", "User")
                msg = top_m.get("message", "").strip()
                if "http" in msg:
                    return f"Sir, the latest message from {sender} contains a shared link. Would you like me to open it or draft a reply?"
                elif msg:
                    return f"Sir, the latest message from {sender} says: \"{msg}\". Would you like me to draft a response?"
            return "Sir, I checked your MakiSync Page inbox, but there are no recent incoming messages to read."

        # Gmail
        self._last_context_app = "gmail"
        # Check if user mentioned a specific person or query (e.g., "from Todd", "Lee Cyril", "latest")
        sender_query = ""
        query_match = re.search(r"(?:from|by)\s+([a-zA-Z0-9_\-,\s]+)", p_lower)
        if query_match and not any(w in query_match.group(1).lower() for w in ("gmail", "email", "inbox", "google")):
            sender_query = query_match.group(1).strip()

        # If cache empty or specific query requested, fetch fresh
        if not self._cached_emails or sender_query:
            fetch_args = {"max_results": 3}
            if sender_query:
                fetch_args["query"] = f"from:{sender_query}"
            res = self.composio.execute_action("GMAIL_FETCH_EMAILS", fetch_args)
            if res.get("success"):
                fresh_emails = res.get("data", {}).get("messages", [])
                if fresh_emails:
                    self._cached_emails = fresh_emails

        if self._cached_emails:
            top_m = self._cached_emails[0]
            sender = re.sub(r"<.*?>", "", top_m.get("sender") or top_m.get("from", "Unknown")).strip()
            clean_sender = re.sub(r"[^\x00-\x7F]+", "", sender).strip() or "a contact"
            subj = top_m.get("subject", "No subject")
            clean_subj = re.sub(r"[^\x00-\x7F]+", "", subj).strip() or "an update"
            
            # Extract body or preview
            preview_body = ""
            if isinstance(top_m.get("preview"), dict):
                preview_body = top_m.get("preview", {}).get("body", "")
            elif isinstance(top_m.get("body"), str):
                preview_body = top_m.get("body", "")
            elif top_m.get("snippet"):
                preview_body = top_m.get("snippet", "")

            # Clean HTML / whitespace / emojis
            import html
            clean_body = html.unescape(preview_body)
            clean_body = re.sub(r"<[^>]+>", " ", clean_body)
            clean_body = re.sub(r"https?://[^\s]+", "", clean_body)
            clean_body = re.sub(r"[^\x00-\x7F]+", "", clean_body)
            clean_body = " ".join(clean_body.split())
            if len(clean_body) > 240:
                clean_body = clean_body[:230] + "..."

            if clean_body:
                return f"Sir, the email from {clean_sender} regarding \"{clean_subj}\" reads: \"{clean_body}\". Would you like me to draft a reply or open the email composer?"
            else:
                return f"Sir, the email from {clean_sender} is regarding \"{clean_subj}\". Would you like me to compose a reply?"

        return "Sir, I checked your Gmail inbox, but there are no recent emails to read."

    def _handle_reply_followup(self, user_prompt: str) -> str:
        """Handle drafting or directly sending a reply to the recent email or Facebook post/message."""
        p_lower = user_prompt.lower()
        
        # Determine target app
        if any(w in p_lower for w in ("facebook", "messenger", "fb", "page", "makisync")):
            target_app = "facebook"
        elif any(w in p_lower for w in ("gmail", "email", "emails", "inbox", "mail")):
            target_app = "gmail"
        else:
            target_app = self._last_context_app

        # Cleanly extract message text if user specified one
        clean_msg = re.sub(r"^(?:send\s+(?:a\s+)?reply(?:\s+(?:saying|with|that|to|a))?|reply(?:\s+(?:saying|with|that|to|a))?|just\s+reply(?:\s+(?:saying|with|that|to|a))?|post(?:\s+saying)?|saying|just\s+say)\s+", "", user_prompt, flags=re.IGNORECASE).strip(" '\"\t\n\r.")
        clean_msg = re.sub(r"^(?:saying|with|that|a|an)\s+", "", clean_msg, flags=re.IGNORECASE).strip(" '\"\t\n\r.")
        extracted_message = clean_msg if clean_msg and clean_msg.lower() not in ("reply", "response", "to this email", "to that email", "to this message", "draft a reply", "draft a reply to this email") else ""

        # Handle Gmail Reply
        if target_app == "gmail":
            if not self._cached_emails:
                res = self.composio.execute_action("GMAIL_FETCH_EMAILS", {"max_results": 1})
                if res.get("success"):
                    self._cached_emails = res.get("data", {}).get("messages", [])

            if self._cached_emails:
                top_m = self._cached_emails[0]
                raw_sender = top_m.get("sender") or top_m.get("from", "")
                match = re.search(r"<([^>]+)>", raw_sender)
                to_email = match.group(1) if match else raw_sender.strip()
                subject = "Re: " + re.sub(r"^Re:\s*", "", top_m.get("subject", "Update"), flags=re.IGNORECASE)

                # Direct send requested if explicit message text provided and not asking to draft
                if extracted_message and not any(w in p_lower for w in ("draft", "open composer", "open draft", "compose")):
                    body = extracted_message
                    send_res = self.composio.execute_action("GMAIL_SEND_EMAIL", {
                        "recipient_email": to_email,
                        "subject": subject,
                        "body": body
                    })
                    if send_res.get("success"):
                        clean_sender = re.sub(r"<.*?>", "", raw_sender).strip()
                        return f"I've sent your reply directly to {clean_sender} saying: \"{body}\", sir."
                    else:
                        return f"I had trouble sending the email: {send_res.get('error', 'Please check connection')}"

                # Open interactive email composer modal
                if hasattr(self, "ui_bridge") and self.ui_bridge:
                    import time
                    draft = {
                        "id": f"reply_{int(time.time())}",
                        "to": to_email,
                        "subject": subject,
                        "body": extracted_message or "Hi, thank you for reaching out. ",
                    }
                    self.ui_bridge.set_active_modal("composio_email", draft)
                    return f"I've opened the email composer to reply to {to_email}, sir. Please review or edit the draft on your screen."
                return f"I'm ready to draft a reply to {to_email}, sir. What would you like to say?"

        # Handle Facebook Page Post / Messenger Reply
        if target_app == "facebook":
            msg_to_post = extracted_message or "Hello world"

            # Check if we should reply in Messenger conversation or post to page timeline
            recipient_id = None
            recipient_name = "the user"
            if self._cached_messages:
                for m in self._cached_messages:
                    sender_id = str(m.get("from", {}).get("id", ""))
                    if sender_id and sender_id != "1129268013603196":
                        recipient_id = sender_id
                        recipient_name = m.get("from", {}).get("name", "the user")
                        break

            # If recipient found in conversation, send directly in Messenger
            if recipient_id and not any(w in p_lower for w in ("post on page", "timeline", "public post", "feed")):
                send_msg_res = self.composio.send_facebook_messenger_message(recipient_id, msg_to_post, "MakiSync")
                if send_msg_res.get("success"):
                    return f"I've sent your reply \"{msg_to_post}\" directly to {recipient_name} on Facebook Messenger, sir."
                else:
                    print(f"[ComposioSkill] Messenger send notice: {send_msg_res.get('error')}")

            # Fallback / timeline post
            post_res = self.composio.execute_action("FACEBOOK_CREATE_POST", {
                "page_id": "1129268013603196",
                "message": msg_to_post
            })
            if post_res.get("success"):
                return f"I've published your response \"{msg_to_post}\" to your MakiSync Page, sir."
            else:
                return f"I had trouble replying to Facebook: {post_res.get('error', 'Please check connection')}"

        return "Sir, which message or email would you like me to reply to?"

    def _summarize_result(self, user_prompt: str, result_data: Any, app_name: str) -> str:
        """Generate a smooth, conversational executive response for both speech (TTS) and UI."""
        # 1. Build a human-friendly narrative context from the raw data
        context_lines = []

        if isinstance(result_data, dict):
            # Case A: Facebook / Messenger messages
            if "latest_messages" in result_data or "conversations" in result_data:
                latest_msgs = result_data.get("latest_messages", [])
                convs = result_data.get("conversations", [])
                if latest_msgs:
                    top_m = latest_msgs[0]
                    top_sender = top_m.get("from", {}).get("name", "User")
                    top_msg = top_m.get("message", "").strip() or "(attachment/link)"
                    context_lines.append(f"THE LATEST AND MOST RECENT MESSAGE RECEIVED FROM THE USER (NEWEST) IS: \"{top_msg}\" from {top_sender}.")
                    if len(latest_msgs) > 1:
                        context_lines.append("Earlier message history:")
                        for m in latest_msgs[1:4]:
                            sender = m.get("from", {}).get("name", "User")
                            content = m.get("message", "").strip()
                            if "http" in content:
                                content = "shared a link"
                            elif not content:
                                content = "sent an attachment"
                            context_lines.append(f"- From {sender}: \"{content}\"")
                elif convs:
                    for c in convs[:3]:
                        participants = [p.get("name") for p in c.get("participants", {}).get("data", []) if p.get("name") != "MakiSync"]
                        p_name = ", ".join(participants) if participants else "a visitor"
                        context_lines.append(f"- Active conversation with {p_name}")
                else:
                    context_lines.append("No new messages found in the inbox.")

            # Case B: Gmail messages / fetch
            elif "messages" in result_data:
                msgs = result_data.get("messages", [])
                count = len(msgs)
                if count > 0:
                    top_m = msgs[0]
                    sender = re.sub(r"<.*?>", "", top_m.get("sender") or top_m.get("from", "Unknown sender")).strip()
                    subj = top_m.get("subject", "No subject")
                    preview = ""
                    if isinstance(top_m.get("preview"), dict):
                        preview = top_m.get("preview", {}).get("body", "")
                    elif isinstance(top_m.get("body"), str):
                        preview = top_m.get("body", "")
                    elif top_m.get("snippet"):
                        preview = top_m.get("snippet", "")
                    clean_prev = re.sub(r"[^\x00-\x7F]+", "", preview).strip()
                    if len(clean_prev) > 180:
                        clean_prev = clean_prev[:170] + "..."
                    context_lines.append(f"Found {count} email(s) in Gmail.")
                    context_lines.append(f"THE LATEST / NEWEST EMAIL is from {sender}, Subject: \"{subj}\". Body preview: \"{clean_prev}\".")
                    if count > 1:
                        context_lines.append("Other recent emails in inbox:")
                        for m in msgs[1:4]:
                            s = re.sub(r"<.*?>", "", m.get("sender") or m.get("from", "Unknown")).strip()
                            su = m.get("subject", "No subject")
                            context_lines.append(f"- From {s}: \"{su}\"")
                else:
                    context_lines.append("Gmail inbox has no new emails.")

            # Case C: Facebook Post created
            elif "id" in result_data and ("post" in user_prompt.lower() or "publish" in user_prompt.lower()):
                context_lines.append(f"Successfully published new post on MakiSync (Post ID: {result_data.get('id')}).")

        # If no custom structured parsing, fallback to clean text
        if not context_lines:
            raw_str = str(result_data)
            clean_str = re.sub(r"https?://[^\s]+", "[link]", raw_str)
            if len(clean_str) > 600:
                clean_str = clean_str[:580] + "..."
            context_lines.append(clean_str)

        narrative_data = "\n".join(context_lines)

        system_prompt = """You are Maki, a highly sophisticated, polite, intelligent AI personal assistant.
Your goal is to brief the user (address him respectfully as 'sir') with the result of his cloud/social request in a completely natural, conversational voice.

CRITICAL RULES:
1. Speak as if talking to him directly out loud. Keep your answer smooth, warm, and concise (1-3 conversational sentences).
2. Never read raw URLs, JSON, asterisks, bullet dashes, or technical IDs out loud. Never output JSON schemas.
3. For Facebook/Messenger messages: Tell him who the LATEST / NEWEST message was from and quote or mention what they said directly (focus strictly on the latest message provided). Ask if he'd like to reply.
4. For Gmail/Emails: State how many emails arrived and mention the latest sender and subject naturally. If the user asked you to read the message, read the body preview naturally. Ask if he would like you to reply.
5. For Posts: Confirm the post is live on the page in a confident, executive tone.
6. Do NOT output any <think> tags or reasoning. Output only the spoken conversational message."""

        summary_request = f"User Request: {user_prompt}\n\nRetrieved Data:\n{narrative_data}"

        summary = self.gemini.send(summary_request, system_prompt)
        
        # Clean reasoning tags if any
        if summary:
            summary = re.sub(r"<(?:think|thought)>.*?</(?:think|thought)>", "", summary, flags=re.DOTALL | re.IGNORECASE).strip()
            summary = re.sub(r"</?(?:think|thought)>", "", summary, flags=re.IGNORECASE).strip()
            is_raw_json = bool(re.search(r"^\s*\{.*\}\s*$", summary, re.DOTALL)) or any(k in summary for k in ('"app":', '"action":', '"arguments":', '```json'))
            is_stub = any(phrase in summary.lower() for phrase in ("not connected yet", "stub", "no api key", "please add a groq or gemini", "error code: 429", "rate limit"))
            if not is_raw_json and not is_stub and summary:
                return summary

        # Fallback Heuristic Conversational Response (if AI model unavailable or rate limited)
        if "facebook" in app_name.lower() or "messenger" in app_name.lower() or "makisync" in user_prompt.lower():
            if isinstance(result_data, dict) and "latest_messages" in result_data:
                latest_msgs = result_data.get("latest_messages", [])
                incoming = [m for m in latest_msgs if str(m.get("from", {}).get("id")) != "1129268013603196" and m.get("from", {}).get("name") != "MakiSync"]
                if incoming:
                    top_m = incoming[0]
                    sender = top_m.get("from", {}).get("name", "a visitor")
                    msg = top_m.get("message", "").strip()
                    if "http" in msg:
                        return f"Sir, you have a recent message on your MakiSync Page from {sender}, who shared a link. Would you like me to open it or draft a reply?"
                    elif msg:
                        return f"Sir, the latest message on your Facebook page is from {sender}, saying \"{msg}.\" Would you like to reply?"
            return "Sir, I've checked your MakiSync Page inbox. There are no urgent unread messages at the moment."

        if "gmail" in app_name.lower() or "email" in user_prompt.lower():
            if isinstance(result_data, dict) and "messages" in result_data:
                msgs = result_data.get("messages", [])
                if msgs:
                    top_m = msgs[0]
                    sender = re.sub(r"<.*?>", "", top_m.get("sender") or top_m.get("from", "Unknown")).strip()
                    subj = top_m.get("subject", "an update")
                    preview = ""
                    if isinstance(top_m.get("preview"), dict):
                        preview = top_m.get("preview", {}).get("body", "")
                    elif isinstance(top_m.get("body"), str):
                        preview = top_m.get("body", "")
                    elif top_m.get("snippet"):
                        preview = top_m.get("snippet", "")
                    clean_prev = re.sub(r"[^\x00-\x7F]+", "", preview).strip()
                    if len(clean_prev) > 200:
                        clean_prev = clean_prev[:190] + "..."

                    # Clean emojis and special symbols
                    clean_subj = re.sub(r"[^\x00-\x7F]+", "", subj).strip() or "a recent message"
                    clean_sender = re.sub(r"[^\x00-\x7F]+", "", sender).strip() or "a contact"
                    
                    if any(w in user_prompt.lower() for w in ("read", "body", "content", "what does it say", "what did they say")):
                        if clean_prev:
                            return f"Sir, the email from {clean_sender} regarding \"{clean_subj}\" reads: \"{clean_prev}\". Would you like me to draft a reply or open the email composer?"
                        return f"Sir, the email from {clean_sender} is regarding \"{clean_subj}\". Would you like me to compose a reply?"

                    email_str = "1 recent email" if len(msgs) == 1 else f"{len(msgs)} recent emails"
                    return f"Sir, I found {email_str} in your Gmail inbox. The latest is from {clean_sender} regarding \"{clean_subj}\". Would you like me to read the full body or draft a reply?"
            return "Sir, I've checked your Gmail inbox. Everything is up to date."

        return f"I've completed your {app_name.capitalize()} request successfully, sir."
