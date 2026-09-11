"""
MakiAI — Auth Service
Handles one-time password setup, bcrypt hashing, session persistence,
and login state across app restarts.
"""

import os
import json
import bcrypt
from pathlib import Path


# Path to the auth data file
AUTH_FILE = Path(__file__).resolve().parents[2] / "data" / "auth.dat"


class AuthService:
    """
    Manages MakiAI authentication.

    - First launch: user sets a password, stored as a bcrypt hash.
    - Subsequent launches: auto-login if session flag is active.
    - Manual logout clears the session flag.
    - No multi-user, no registration flow.
    """

    def __init__(self):
        AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._auth_data = self._load()

    # ─── Public API ──────────────────────────────────────────────────────────

    def is_first_launch(self) -> bool:
        """
        Returns True if no password has been set yet.
        Triggers the first-launch setup screen.
        """
        return not self._auth_data.get("password_hash")

    def setup_password(self, password: str) -> bool:
        """
        Hash and store the password on first launch.

        Args:
            password: The plain-text password chosen by the user.

        Returns:
            True on success, False if password is empty.
        """
        if not password or not password.strip():
            return False

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        self._auth_data["password_hash"] = hashed.decode("utf-8")
        self._auth_data["session_active"] = True
        self._save()
        return True

    def verify_password(self, password: str) -> bool:
        """
        Verify a plain-text password against the stored hash.

        Args:
            password: The plain-text password to check.

        Returns:
            True if correct, False otherwise.
        """
        stored_hash = self._auth_data.get("password_hash", "")
        if not stored_hash:
            return False

        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                stored_hash.encode("utf-8")
            )
        except Exception as e:
            print(f"[AuthService] Password verify error: {e}")
            return False

    def is_logged_in(self) -> bool:
        """
        Returns True if a session is currently active.
        Used on startup to decide whether to skip the login screen.
        """
        return bool(self._auth_data.get("session_active", False))

    def login(self, password: str) -> bool:
        """
        Verify password and activate session if correct.

        Args:
            password: Plain-text password entered by the user.

        Returns:
            True if login succeeded, False otherwise.
        """
        if self.verify_password(password):
            self._auth_data["session_active"] = True
            self._save()
            return True
        return False

    def logout(self) -> None:
        """
        Clear the active session. Next app launch will require login.
        """
        self._auth_data["session_active"] = False
        self._save()
        print("[AuthService] Session cleared — logged out.")

    # ─── Internal ────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        """Load auth data from disk. Returns empty dict if file doesn't exist."""
        if not AUTH_FILE.exists():
            return {}
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[AuthService] Failed to load auth data: {e}")
            return {}

    def _save(self) -> None:
        """Persist auth data to disk."""
        try:
            with open(AUTH_FILE, "w", encoding="utf-8") as f:
                json.dump(self._auth_data, f, indent=2)
        except OSError as e:
            print(f"[AuthService] Failed to save auth data: {e}")
