"""
MakiAI — Composio Cloud & Workspace Service (composio_service.py)
Connects MakiAI to 500+ cloud tools (Google Docs, Calendar, Gmail, Notion, GitHub, etc.)
with zero manual OAuth configuration.
"""

import os
import json
from typing import Optional, Dict, Any, List


class ComposioService:
    """
    Cloud & SaaS integration manager for MakiAI powered by Composio.
    """

    def __init__(self, api_key: Any = ""):
        # Check explicit key, settings object, os.getenv, or load directly from .env file
        key = ""
        if isinstance(api_key, str):
            key = api_key.strip()
        elif hasattr(api_key, "get"):
            key = str(api_key.get("composio_api_key", "") or "").strip()

        if not key:
            key = os.getenv("COMPOSIO_API_KEY", "").strip()

        if not key:
            try:
                from dotenv import dotenv_values
                from pathlib import Path
                env_path = Path(__file__).resolve().parents[2] / ".env"
                if env_path.exists():
                    env_vals = dotenv_values(env_path)
                    key = (env_vals.get("COMPOSIO_API_KEY") or "").strip()
            except Exception:
                pass

        self.api_key = key
        self._client = None
        self._initialized = False

        if self.api_key:
            self._init_client()
        else:
            print("[ComposioService] No COMPOSIO_API_KEY found. Running in setup-guide mode.")

    def _init_client(self) -> bool:
        """Initialize the Composio client (v3 client)."""
        try:
            try:
                from composio_client import Composio
            except ImportError:
                import sys
                py311_site = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\Lib\site-packages")
                if os.path.exists(py311_site) and py311_site not in sys.path:
                    sys.path.append(py311_site)
                try:
                    from composio_client import Composio
                except ImportError:
                    from composio import Composio

            self._client = Composio(api_key=self.api_key)
            self._initialized = True
            print("[ComposioService] Initialized successfully with Composio v3 SDK.")
            return True
        except ImportError:
            print("[ComposioService] composio-client not installed.")
            return False
        except Exception as e:
            print(f"[ComposioService] Init error: {e}")
            return False

    def is_configured(self) -> bool:
        """Check if Composio is authenticated and ready."""
        return self._initialized and self._client is not None

    def update_api_key(self, new_key: str) -> bool:
        """Update API key at runtime."""
        self.api_key = new_key.strip()
        return self._init_client()

    def get_connected_accounts(self) -> List[Dict[str, Any]]:
        """Fetch all currently connected integrations."""
        if not self.is_configured():
            return []
        try:
            accounts = self._client.connected_accounts.list()
            # Handle list response
            results = []
            if hasattr(accounts, "items"):
                for item in accounts.items:
                    results.append({
                        "id": getattr(item, "id", ""),
                        "app": getattr(item, "appName", getattr(item, "app", "")),
                        "status": getattr(item, "status", "CONNECTED"),
                    })
            elif isinstance(accounts, list):
                for item in accounts:
                    results.append({
                        "id": getattr(item, "id", str(item)),
                        "app": getattr(item, "appName", getattr(item, "app", "unknown")),
                        "status": getattr(item, "status", "CONNECTED"),
                    })
            return results
        except Exception as e:
            print(f"[ComposioService] Error fetching connected accounts: {e}")
            return []

    def get_auth_url(self, app_name: str, user_id: str = "default") -> str:
        """Generate a direct 1-click OAuth connection URL for an app toolkit."""
        clean_name = app_name.lower().replace(" ", "").replace("_", "")
        app_map = {
            "googledocs": "googledocs",
            "googlecalendar": "googlecalendar",
            "gmail": "gmail",
            "notion": "notion",
            "github": "github",
            "trello": "trello",
            "spotify": "spotify",
            "discord": "discord",
        }
        toolkit_slug = app_map.get(clean_name, clean_name)

        if self.is_configured():
            try:
                # 1. Search for existing auth config for this toolkit
                configs = self._client.auth_configs.list()
                items = getattr(configs, "items", []) or []
                auth_config_id = None
                for cfg in items:
                    tk = getattr(cfg, "toolkit", None)
                    slug = getattr(tk, "slug", "") if tk else ""
                    if slug == toolkit_slug or toolkit_slug in getattr(cfg, "name", "").lower():
                        auth_config_id = getattr(cfg, "id", None)
                        break

                # 2. Generate 1-click OAuth link
                if auth_config_id:
                    link_res = self._client.link.create(
                        auth_config_id=auth_config_id,
                        user_id=user_id,
                    )
                    redirect_url = getattr(link_res, "redirect_url", None)
                    if redirect_url:
                        return redirect_url
            except Exception as e:
                print(f"[ComposioService] Link generation notice: {e}")

        return f"https://dashboard.composio.dev/toolkits/{toolkit_slug}"

    def _get_active_entity_for_tool(self, tool_slug: str) -> Optional[str]:
        """Find the active user_id / entity_id for a given tool slug from connected accounts."""
        try:
            accounts = self._client.connected_accounts.list()
            items = getattr(accounts, "items", accounts) or []
            tool_prefix = tool_slug.split("_")[0].lower()
            
            # Map tool prefixes to toolkits
            prefix_map = {
                "facebook": "facebook",
                "messenger": "facebook",
                "gmail": "gmail",
                "googlecalendar": "googlecalendar",
                "googledocs": "googledocs",
                "googlesheets": "googlesheets",
                "notion": "notion",
                "trello": "trello",
                "github": "github",
            }
            target_tk = prefix_map.get(tool_prefix, tool_prefix)

            # First match matching toolkit and ACTIVE status
            for a in items:
                tk = getattr(a, "toolkit", None)
                tk_slug = getattr(tk, "slug", "") if tk else getattr(a, "appName", "")
                st = getattr(a, "status", "")
                if (tk_slug == target_tk or target_tk in str(tk_slug).lower()) and st in ("ACTIVE", "CONNECTED", ""):
                    uid = getattr(a, "user_id", getattr(a, "userId", getattr(a, "entity_id", getattr(a, "entityId", None))))
                    if uid:
                        return uid

            # Fallback to any active user_id if present
            for a in items:
                st = getattr(a, "status", "")
                if st in ("ACTIVE", "CONNECTED", ""):
                    uid = getattr(a, "user_id", getattr(a, "userId", getattr(a, "entity_id", getattr(a, "entityId", None))))
                    if uid and uid != "default":
                        return uid
        except Exception:
            pass
        return None

    def execute_action(self, action_slug: str, arguments: Dict[str, Any], user_id: str = "default") -> Dict[str, Any]:
        """
        Execute a tool action via Composio.
        
        Args:
            action_slug: E.g., 'GOOGLEDOCS_CREATE_DOCUMENT', 'GOOGLECALENDAR_GET_EVENTS', 'FACEBOOK_GET_PAGE_CONVERSATIONS'
            arguments: Dict of parameters for the action.
            user_id: User identifier (default: 'default').
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Composio API key is not configured. Please add COMPOSIO_API_KEY to .env.",
            }

        slug_clean = action_slug.upper().strip()

        # Attempt 1: Execute with provided user_id
        try:
            try:
                result = self._client.tools.execute(
                    tool_slug=slug_clean,
                    user_id=user_id,
                    arguments=arguments or {},
                )
            except TypeError:
                result = self._client.tools.execute(
                    slug=slug_clean,
                    arguments=arguments or {},
                )

            # Check if response payload itself indicates an error
            if hasattr(result, "successful") and not result.successful:
                # If error is missing connected account on default entity, try active entity
                err_str = str(getattr(result, "error", ""))
                if "No connected account found" in err_str or "ActionExecute_ConnectedAccountNotFound" in err_str:
                    fallback_uid = self._get_active_entity_for_tool(slug_clean)
                    if fallback_uid and fallback_uid != user_id:
                        result = self._client.tools.execute(
                            tool_slug=slug_clean,
                            user_id=fallback_uid,
                            arguments=arguments or {},
                        )

            return {
                "success": getattr(result, "successful", True),
                "data": getattr(result, "data", result),
                "error": getattr(result, "error", None) if not getattr(result, "successful", True) else None,
            }
        except Exception as e:
            err_msg = str(e)
            # If 404 connected account on default entity, try fallback entity
            if ("No connected account found" in err_msg or "ActionExecute_ConnectedAccountNotFound" in err_msg) and user_id == "default":
                fallback_uid = self._get_active_entity_for_tool(slug_clean)
                if fallback_uid:
                    try:
                        result = self._client.tools.execute(
                            tool_slug=slug_clean,
                            user_id=fallback_uid,
                            arguments=arguments or {},
                        )
                        return {
                            "success": getattr(result, "successful", True),
                            "data": getattr(result, "data", result),
                            "error": getattr(result, "error", None) if not getattr(result, "successful", True) else None,
                        }
                    except Exception as retry_e:
                        err_msg = str(retry_e)

            print(f"[ComposioService] Action execution failed ({slug_clean}): {err_msg}")
            return {
                "success": False,
                "error": err_msg,
            }

    def send_facebook_messenger_message(self, recipient_id: str, message_text: str, page_name: str = "MakiSync") -> Dict[str, Any]:
        """
        Send a direct message reply to a user on Facebook Messenger using the Page Access Token.
        """
        try:
            import requests
            pages_res = self.execute_action("FACEBOOK_LIST_MANAGED_PAGES", {})
            if not pages_res.get("success"):
                return {"success": False, "error": "Could not retrieve Facebook managed pages"}

            pages_data = pages_res.get("data", {})
            p_list = pages_data.get("data", []) if isinstance(pages_data, dict) else []
            target_page = None
            for p in p_list:
                if isinstance(p, dict):
                    if page_name.lower() in p.get("name", "").lower():
                        target_page = p
                        break
            if not target_page and p_list and isinstance(p_list[0], dict):
                target_page = p_list[0]

            if not target_page:
                return {"success": False, "error": "No managed Facebook Page found"}

            token = target_page.get("access_token")
            page_id = target_page.get("id")
            if not token or not page_id:
                return {"success": False, "error": "Page access token or ID missing"}

            url = f"https://graph.facebook.com/v23.0/{page_id}/messages"
            payload = {
                "recipient": {"id": recipient_id},
                "message": {"text": message_text},
                "messaging_type": "RESPONSE"
            }
            headers = {"Authorization": f"Bearer {token}"}
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                res_json = r.json()
                return {"success": True, "data": res_json, "recipient_id": recipient_id}
            else:
                err_body = r.text
                return {"success": False, "error": f"Graph API Error ({r.status_code}): {err_body}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
