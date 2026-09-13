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

    def __init__(self, api_key: str = ""):
        # Check explicit key, os.getenv, or load directly from .env file
        key = api_key or os.getenv("COMPOSIO_API_KEY", "").strip()
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

    def execute_action(self, action_slug: str, arguments: Dict[str, Any], user_id: str = "default") -> Dict[str, Any]:
        """
        Execute a tool action via Composio.
        
        Args:
            action_slug: E.g., 'GOOGLEDOCS_CREATE_DOCUMENT', 'GOOGLECALENDAR_GET_EVENTS'
            arguments: Dict of parameters for the action.
            user_id: User identifier (default: 'default').
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Composio API key is not configured. Please add COMPOSIO_API_KEY to .env.",
            }

        try:
            try:
                result = self._client.tools.execute(
                    tool_slug=action_slug.upper().strip(),
                    user_id=user_id,
                    arguments=arguments or {},
                )
            except TypeError:
                result = self._client.tools.execute(
                    slug=action_slug.upper().strip(),
                    arguments=arguments or {},
                )
            return {
                "success": True,
                "data": result,
            }
        except Exception as e:
            err_msg = str(e)
            print(f"[ComposioService] Action execution failed ({action_slug}): {err_msg}")
            return {
                "success": False,
                "error": err_msg,
            }
