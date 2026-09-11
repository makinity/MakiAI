"""
MakiAI — Settings Service
Manages reading and writing of app configuration from:
  - .env file (API keys, wake word, KB path)
  - data/settings.json (UI preferences, feature toggles)

All config changes apply immediately without restarting the app.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv, set_key, dotenv_values


# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
SETTINGS_FILE = PROJECT_ROOT / "data" / "settings.json"

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

    Reads from both .env (secrets, API keys) and settings.json (preferences).
    Writes back to both files when settings are updated via the Settings UI.
    """

    def __init__(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        load_dotenv(ENV_FILE)
        self._settings = self._load_settings()

    # ─── ENV (.env) ──────────────────────────────────────────────────────────

    def get_env(self, key: str, fallback: str = "") -> str:
        """
        Read a value from the .env file.

        Args:
            key: The environment variable name (e.g. GEMINI_API_KEY).
            fallback: Value to return if the key is not set.

        Returns:
            The value as a string.
        """
        return os.getenv(key, fallback)

    def set_env(self, key: str, value: str) -> bool:
        """
        Write or update a key in the .env file.
        Reloads the environment so changes take effect immediately.

        Args:
            key: The environment variable name.
            value: The new value.

        Returns:
            True on success, False on failure.
        """
        try:
            if not ENV_FILE.exists():
                ENV_FILE.touch()
            set_key(str(ENV_FILE), key, value)
            os.environ[key] = value  # Apply immediately to current process
            print(f"[SettingsService] .env updated: {key}")
            return True
        except Exception as e:
            print(f"[SettingsService] Failed to update .env [{key}]: {e}")
            return False

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

    # ─── Settings JSON ───────────────────────────────────────────────────────

    def get(self, key: str, fallback=None):
        """
        Read a value from settings.json.

        Args:
            key: The setting key (e.g. 'theme', 'tts_fallback').
            fallback: Value to return if key is not found.

        Returns:
            The setting value, or fallback.
        """
        return self._settings.get(key, fallback)

    def set(self, key: str, value) -> bool:
        """
        Write a value to settings.json and persist it.

        Args:
            key: The setting key.
            value: The new value.

        Returns:
            True on success, False on failure.
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

    # ─── Internal ────────────────────────────────────────────────────────────

    def _load_settings(self) -> dict:
        """Load settings.json from disk, seeding with defaults if missing."""
        if not SETTINGS_FILE.exists():
            self._settings = dict(DEFAULT_SETTINGS)
            self._save_settings()
            return dict(DEFAULT_SETTINGS)
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Merge with defaults so new keys are always present
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
