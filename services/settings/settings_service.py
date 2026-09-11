"""
MakiAI — Settings Service
Manages reading and writing of app configuration from:
  - SQLite Database: data/config.db (Primary single source of truth for credentials & keys)
  - .env file (Synchronized backup for external tools)
  - data/settings.json (UI preferences, feature toggles)

All config changes apply immediately without restarting the app and persist across restarts.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv, set_key, dotenv_values


# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_DB_FILE = DATA_DIR / "config.db"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Default settings.json values
DEFAULT_SETTINGS = {
    "theme": "dark",
    "tts_fallback": True,
    "always_on_listening": True,
    "show_transcription": True,
    "screenshot_save_path": str(Path.home() / "Pictures" / "MakiAI"),
    "camera_save_path": str(Path.home() / "Videos" / "MakiAI"),
}


class SettingsService:
    """
    Centralized config manager for MakiAI.

    Uses SQLite (data/config.db) as the primary, persistent source of truth
    for API keys and configuration, while keeping .env synchronized.
    """

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._sync_initial_env()
        self._settings = self._load_settings()

    # ─── SQLite Configuration Database ──────────────────────────────────────

    def _get_db_connection(self) -> sqlite3.Connection:
        """Create and return a connection to the config database."""
        conn = sqlite3.connect(str(CONFIG_DB_FILE))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize the SQLite config table."""
        try:
            with self._get_db_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS app_config (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
        except Exception as e:
            print(f"[SettingsService] DB init error: {e}")

    def _sync_initial_env(self) -> None:
        """
        Initial sync on startup:
        1. Read values from .env file directly (not stale os.environ).
        2. Seed SQLite with any keys that exist in .env if not already set.
        3. Load all SQLite values into os.environ with override=True.
        """
        try:
            # Read .env file directly
            env_file_values = {}
            if ENV_FILE.exists():
                env_file_values = dotenv_values(str(ENV_FILE))

            with self._get_db_connection() as conn:
                # Get existing DB keys
                cursor = conn.execute("SELECT key, value FROM app_config")
                db_values = {row["key"]: row["value"] for row in cursor.fetchall()}

                # If .env has values not in DB or DB is empty, seed from .env
                for k, v in env_file_values.items():
                    if v and (k not in db_values or not db_values[k]):
                        conn.execute("""
                            INSERT INTO app_config (key, value, updated_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                        """, (k, str(v)))
                        db_values[k] = str(v)

                conn.commit()

                # Refresh DB values and inject into os.environ
                cursor = conn.execute("SELECT key, value FROM app_config")
                for row in cursor.fetchall():
                    k, v = row["key"], row["value"]
                    if v:
                        os.environ[k] = str(v)

            # Also ensure python-dotenv loads with override
            if ENV_FILE.exists():
                load_dotenv(str(ENV_FILE), override=True)

        except Exception as e:
            print(f"[SettingsService] Initial sync error: {e}")

    # ─── Key-Value API (SQLite + .env Sync) ───────────────────────────────────

    def get_env(self, key: str, fallback: str = "") -> str:
        """
        Read a value from SQLite database first, falling back to .env / os.environ.

        Args:
            key: The config/environment variable name.
            fallback: Value to return if the key is not set.

        Returns:
            The value as a string.
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute("SELECT value FROM app_config WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row and row["value"]:
                    val = str(row["value"]).strip()
                    os.environ[key] = val
                    return val
        except Exception as e:
            print(f"[SettingsService] DB read error for [{key}]: {e}")

        # Fallback to direct .env file or os.getenv
        if ENV_FILE.exists():
            env_file_values = dotenv_values(str(ENV_FILE))
            if key in env_file_values and env_file_values[key]:
                val = str(env_file_values[key]).strip()
                self.set_env(key, val)  # Save to SQLite for next time
                return val

        return os.getenv(key, fallback)

    def set_env(self, key: str, value: str) -> bool:
        """
        Write or update a key in SQLite Database AND sync to .env file.
        Applies immediately to os.environ so all services receive the update.

        Args:
            key: The environment variable name.
            value: The new value.

        Returns:
            True on success, False on failure.
        """
        value_str = str(value).strip()
        success = True

        # 1. Save to SQLite Database (Single Source of Truth)
        try:
            with self._get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO app_config (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """, (key, value_str))
                conn.commit()
        except Exception as e:
            print(f"[SettingsService] Failed to save [{key}] to SQLite: {e}")
            success = False

        # 2. Apply to current process memory
        os.environ[key] = value_str

        # 3. Synchronize to .env file
        try:
            if not ENV_FILE.exists():
                ENV_FILE.touch()
            set_key(str(ENV_FILE), key, value_str)
            print(f"[SettingsService] Saved [{key}] to SQLite Database & synchronized .env")
        except Exception as e:
            print(f"[SettingsService] Failed to sync .env [{key}]: {e}")

        return success

    def get_all_env(self) -> dict[str, str]:
        """Return all configuration key-values stored in SQLite."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute("SELECT key, value FROM app_config ORDER BY key")
                return {row["key"]: row["value"] for row in cursor.fetchall()}
        except Exception as e:
            print(f"[SettingsService] Failed to fetch all config: {e}")
            return {}

    # ─── Convenience env getters ─────────────────────────────────────────────

    def get_gemini_api_key(self) -> str:
        return self.get_env("GEMINI_API_KEY")

    def get_groq_api_key(self) -> str:
        return self.get_env("GROQ_API_KEY")

    def get_elevenlabs_api_key(self) -> str:
        return self.get_env("ELEVENLABS_API_KEY")

    def get_elevenlabs_voice_id(self) -> str:
        return self.get_env("ELEVENLABS_VOICE_ID")

    def get_porcupine_access_key(self) -> str:
        return self.get_env("PORCUPINE_ACCESS_KEY")

    def get_wake_word(self) -> str:
        return self.get_env("WAKE_WORD", "Hey Maki")

    def get_kb_path(self) -> str:
        return self.get_env("KB_PATH", r"C:\Knowledge-Base")

    def get_app_name(self) -> str:
        return self.get_env("APP_NAME", "MakiAI")

    def is_debug(self) -> bool:
        return self.get_env("DEBUG", "false").lower() == "true"

    # ─── Settings JSON (UI Toggles & Preferences) ────────────────────────────

    def get(self, key: str, fallback: Any = None) -> Any:
        """
        Read a value from settings.json.
        """
        return self._settings.get(key, fallback)

    def set(self, key: str, value: Any) -> bool:
        """
        Write a value to settings.json and persist it.
        """
        self._settings[key] = value
        return self._save_settings()

    def get_all(self) -> dict:
        """Return a copy of all current settings."""
        return dict(self._settings)

    def reset_to_defaults(self) -> bool:
        """Reset settings.json to default values."""
        self._settings = dict(DEFAULT_SETTINGS)
        return self._save_settings()

    # ─── Internal Settings JSON ──────────────────────────────────────────────

    def _load_settings(self) -> dict:
        """Load settings.json from disk, seeding with defaults if missing."""
        if not SETTINGS_FILE.exists():
            self._settings = dict(DEFAULT_SETTINGS)
            self._save_settings()
            return dict(DEFAULT_SETTINGS)
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                merged = {**DEFAULT_SETTINGS, **loaded}
                return merged
        except (json.JSONDecodeError, OSError) as e:
            print(f"[SettingsService] Failed to load settings.json: {e}")
            return dict(DEFAULT_SETTINGS)

    def _save_settings(self) -> bool:
        """Persist current settings to settings.json."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
            return True
        except OSError as e:
            print(f"[SettingsService] Failed to save settings.json: {e}")
            return False
