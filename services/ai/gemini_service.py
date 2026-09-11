"""
MakiAI — AI Service
Supports both Groq and Google Gemini as AI providers.

Provider priority:
  1. Groq (if GROQ_API_KEY is set) — faster, more reliable free tier
  2. Gemini (if GEMINI_API_KEY is set) — fallback

Groq free tier: llama-3.3-70b-versatile — fast, high quality
Gemini free tier: gemini-3.6-flash

The active provider is selected at startup based on which key is available.
Can be hot-swapped via update_api_key().
"""

from typing import Optional


MAX_HISTORY_TURNS = 20


class GeminiService:
    """
    AI service for MakiAI — supports Groq and Gemini.
    Named GeminiService for backward compatibility with existing code.
    """

    # Models to try in order — first available wins
    GROQ_MODELS = [
        "llama-3.1-8b-instant",       # Free tier, fastest
        "llama-3.3-70b-versatile",    # Free tier, best quality
        "llama3-8b-8192",             # Legacy free tier
        "llama3-groq-8b-8192-tool-use-preview",  # Tool-use preview
        "openai/gpt-oss-20b",         # Paid fallback
    ]

    def __init__(self, api_key: str = "", groq_api_key: str = ""):
        """
        Args:
            api_key:      Gemini API key (GEMINI_API_KEY in .env)
            groq_api_key: Groq API key (GROQ_API_KEY in .env)
        """
        self._gemini_key = api_key
        self._groq_key = groq_api_key
        self._history: list[dict] = []
        self._initialized = False
        self._provider = None       # "groq" or "gemini"
        self._groq_model = None     # Active Groq model

        # Groq client
        self._groq_client = None
        # Gemini client
        self._gemini_client = None

        self._initialize()

    # ─── Init ────────────────────────────────────────────────────────────────

    def _initialize(self) -> None:
        """Try Groq first, fall back to Gemini."""
        # Try Groq
        if self._groq_key and self._groq_key not in ("", "your_groq_api_key_here"):
            if self._init_groq(self._groq_key):
                return

        # Try Gemini
        if self._gemini_key and self._gemini_key not in ("", "your_gemini_api_key_here"):
            if self._init_gemini(self._gemini_key):
                return

        print("[AIService] No valid API key found. Running in stub mode.")

    def _init_groq(self, api_key: str) -> bool:
        try:
            from groq import Groq
            self._groq_client = Groq(api_key=api_key)

            # Auto-detect first working model
            self._groq_model = self._detect_groq_model()
            if not self._groq_model:
                print("[AIService] No working Groq model found.")
                return False

            self._provider = "groq"
            self._initialized = True
            print(f"[AIService] Initialized with Groq ({self._groq_model}).")
            return True
        except Exception as e:
            print(f"[AIService] Groq init failed: {e}")
            return False

    def _detect_groq_model(self) -> str | None:
        """Try each model in GROQ_MODELS and return the first working one."""
        for model in self.GROQ_MODELS:
            try:
                self._groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=5,
                )
                print(f"[AIService] Groq model working: {model}")
                return model
            except Exception as e:
                err = str(e).lower()
                if "decommission" in err or "not found" in err or "404" in err:
                    print(f"[AIService] Groq model unavailable: {model}")
                    continue
                # Other errors (auth, rate limit) — stop trying
                print(f"[AIService] Groq error on {model}: {e}")
                break
        return None

    def _init_gemini(self, api_key: str) -> bool:
        try:
            from google import genai
            self._gemini_client = genai.Client(api_key=api_key)
            self._provider = "gemini"
            self._initialized = True
            print("[AIService] Initialized with Gemini (gemini-3.6-flash).")
            return True
        except Exception as e:
            print(f"[AIService] Gemini init failed: {e}")
            return False

    def update_api_key(self, new_key: str, provider: str = "auto") -> None:
        """
        Hot-swap API key. provider: "groq", "gemini", or "auto".
        """
        self._history = []
        if provider == "groq" or (provider == "auto" and new_key.startswith("gsk_")):
            self._groq_key = new_key
        else:
            self._gemini_key = new_key
        self._initialize()

    # ─── Core Send ────────────────────────────────────────────────────────────

    def send(self, user_text: str, system_context: str = "") -> str:
        """
        Send a message and return the AI response.

        Args:
            user_text:      The user's voice/text command.
            system_context: KB context injected as system prompt.

        Returns:
            AI response string.
        """
        if not self._initialized:
            return self._stub_response(user_text)

        if self._provider == "groq":
            return self._send_groq(user_text, system_context)
        elif self._provider == "gemini":
            return self._send_gemini(user_text, system_context)

        return self._stub_response(user_text)

    def _send_groq(self, user_text: str, system_context: str) -> str:
        """Send via Groq API with streaming for faster response."""
        try:
            messages = []
            system_prompt = system_context if system_context else """You are MakiAI, a personal AI assistant for Mark Vencent Juntilla inspired by Jarvis from Iron Man. Always address the user as 'sir'. Be warm, conversational, and natural. Keep responses concise. No markdown or bullet points. Just clear natural English.

You have full access to:
- C:\\Knowledge Base\\ — sir's schedule, deadlines, projects, preferences
- C:\\MakiSync Storage\\ — organized file storage (School, Work, Personal, Freelance, MakiAI with Screenshots/Photos/Recordings in date folders)
You CAN search, open, and manage files in these locations."""
            messages.append({"role": "system", "content": system_prompt})

            for turn in self._history[-(MAX_HISTORY_TURNS * 2):]:
                role = "user" if turn["role"] == "user" else "assistant"
                messages.append({"role": role, "content": turn["text"]})

            messages.append({"role": "user", "content": user_text})

            # Use streaming for faster perceived response
            stream = self._groq_client.chat.completions.create(
                model=self._groq_model,
                messages=messages,
                max_tokens=800,       # Increased for KB-heavy responses
                temperature=0.7,
                stream=True,
            )

            answer = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    answer += delta

            answer = answer.strip()
            if not answer:
                print(f"[AIService] Groq returned empty response for: {user_text[:50]}")
                return ""
            self._add_to_history("user", user_text)
            self._add_to_history("model", answer)
            return answer

        except Exception as e:
            error_str = str(e).lower()
            print(f"[AIService] Groq error: {e}")
            if "rate" in error_str or "429" in error_str:
                return "I'm being rate limited. Give me a moment and try again."
            if "auth" in error_str or "invalid" in error_str or "401" in error_str:
                return "My Groq API key seems invalid. Please check your settings."
            if self._gemini_client:
                print("[AIService] Groq failed — trying Gemini fallback.")
                return self._send_gemini(user_text, system_context)
            return "I had trouble thinking. Please try again."

    def _send_gemini(self, user_text: str, system_context: str) -> str:
        """Send via Gemini API."""
        try:
            full_prompt = f"{system_context}\n\n---\n\nUser: {user_text}" if system_context else user_text

            response = self._gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=full_prompt,
            )

            answer = response.text.strip()
            self._add_to_history("user", user_text)
            self._add_to_history("model", answer)
            return answer

        except Exception as e:
            error_str = str(e).lower()
            print(f"[AIService] Gemini error: {e}")
            if "quota" in error_str or "rate" in error_str:
                return "I've hit my quota. Please try again in a moment."
            if "503" in error_str or "unavailable" in error_str:
                return "The AI service is busy right now. Please try again shortly."
            if "404" in error_str or "not found" in error_str:
                return "The AI model isn't available. Please check your API key settings."
            return "I had trouble thinking. Please try again."

    def send_with_image(self, user_text: str, image_path: str, system_context: str = "") -> str:
        """Send a message with an image for visual analysis (Gemini Vision)."""
        if not self._initialized:
            return self._stub_response(user_text)

        # Only Gemini supports vision currently
        if self._gemini_client:
            try:
                import PIL.Image
                image = PIL.Image.open(image_path)
                prompt = f"{system_context}\n\nUser: {user_text}" if system_context else user_text
                response = self._gemini_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[prompt, image],
                )
                return response.text.strip()
            except Exception as e:
                print(f"[AIService] Vision error: {e}")
                return "I couldn't analyze that image. Please try again."

        return "Image analysis requires Gemini. Please add a Gemini API key in settings."

    # ─── History ─────────────────────────────────────────────────────────────

    def clear_history(self) -> None:
        self._history = []

    def get_history(self) -> list[dict]:
        return list(self._history)

    def _add_to_history(self, role: str, text: str) -> None:
        self._history.append({"role": role, "text": text})
        if len(self._history) > MAX_HISTORY_TURNS * 2:
            self._history = self._history[-(MAX_HISTORY_TURNS * 2):]

    def _stub_response(self, user_text: str) -> str:
        print(f"[AIService] Stub — no API key configured.")
        return "I'm not connected yet. Please add a Groq or Gemini API key in your .env file."

    @property
    def is_ready(self) -> bool:
        return self._initialized

    @property
    def active_provider(self) -> str:
        return self._provider or "none"

