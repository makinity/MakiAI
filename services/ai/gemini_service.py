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
import re


MAX_HISTORY_TURNS = 20


class GeminiService:
    """
    AI service for MakiAI — supports Groq and Gemini.
    Named GeminiService for backward compatibility with existing code.
    """

    # Models to try in order — first available wins
    GROQ_MODELS = [
        "openai/gpt-oss-120b",
        "groq/compound",
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
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
        """Initialize available providers (Groq and Gemini fallback)."""
        gemini_ok = False
        groq_ok = False

        # Init Gemini
        if self._gemini_key and self._gemini_key not in ("", "your_gemini_api_key_here"):
            gemini_ok = self._init_gemini(self._gemini_key)

        # Init Groq
        if self._groq_key and self._groq_key not in ("", "your_groq_api_key_here"):
            groq_ok = self._init_groq(self._groq_key)

        if groq_ok:
            self._provider = "groq"
            self._initialized = True
        elif gemini_ok:
            self._provider = "gemini"
            self._initialized = True
        else:
            self._provider = None
            self._initialized = False
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
            import logging
            logging.getLogger("google.genai").setLevel(logging.ERROR)
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

    def _clean_response(self, text: str) -> str:
        """Strip internal thinking/reasoning tags and tokens from model responses."""
        if not text:
            return ""

        # 1. Strip complete <think>...</think> or <thought>...</thought> blocks
        cleaned = re.sub(r"<(?:think|thought)>.*?</(?:think|thought)>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

        # 2. If the model put the entire answer INSIDE the <think> tag, extract the draft/response
        if not cleaned:
            marker_match = re.search(
                r"(?:(?:\*\*Draft[^\n]*\*\*|\*\*Final Response[^\n]*\*\*|\*\*Response[^\n]*\*\*|Draft:)\s*)(.*?)(?:</(?:think|thought)>|$)",
                text,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if marker_match:
                cleaned = marker_match.group(1).strip()
            else:
                # Remove all think tags and return whatever text remains
                cleaned = re.sub(r"</?(?:think|thought)>", "", text, flags=re.IGNORECASE).strip()

        # 3. In case of unclosed <think> tag where the model outputs reasoning and then the answer
        if re.search(r"<(?:think|thought)>", cleaned, re.IGNORECASE):
            marker_match = re.search(
                r"(?:(?:\*\*Draft[^\n]*\*\*|\*\*Final Response[^\n]*\*\*|\*\*Response[^\n]*\*\*|Draft:)\s*)(.*)",
                cleaned,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if marker_match:
                cleaned = marker_match.group(1)
            else:
                trimmed = re.sub(r"<(?:think|thought)>.*", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
                if trimmed.strip():
                    cleaned = trimmed
                else:
                    cleaned = re.sub(r"<(?:think|thought)>", "", text, flags=re.IGNORECASE)

        # 4. Clean any stray closing tags
        cleaned = re.sub(r"</(?:think|thought)>", "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _send_groq(self, user_text: str, system_context: str) -> str:
        """Send via Groq API with streaming for faster response and model rotation on 429."""
        messages = []
        base_prompt = system_context if system_context else """You are MakiAI, a personal AI assistant for Mark Vencent Juntilla inspired by Jarvis from Iron Man. Always address the user as 'sir'. Be warm, conversational, and natural. Keep responses concise. No markdown or bullet points. Just clear natural English.

You have full access to:
- C:\\Knowledge Base\\ — sir's schedule, deadlines, projects, preferences
- C:\\MakiSync Storage\\ — organized file storage (School, Work, Personal, Freelance, MakiAI with Screenshots/Photos/Recordings in date folders)
You CAN search, open, and manage files in these locations."""
        
        system_prompt = f"{base_prompt}\n\nIMPORTANT: Do NOT output any <think> or internal reasoning tags. Provide only the direct final response."
        messages.append({"role": "system", "content": system_prompt})

        for turn in self._history[-(MAX_HISTORY_TURNS * 2):]:
            role = "user" if turn["role"] == "user" else "assistant"
            messages.append({"role": role, "content": turn["text"]})

        messages.append({"role": "user", "content": user_text})

        # Try active model, rotate if rate limited
        candidate_models = [self._groq_model] + [m for m in self.GROQ_MODELS if m != self._groq_model]

        for model_name in candidate_models:
            try:
                stream = self._groq_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=800,
                    temperature=0.7,
                    stream=True,
                )

                answer = ""
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        answer += delta

                answer = self._clean_response(answer)

                if answer:
                    self._groq_model = model_name
                    self._add_to_history("user", user_text)
                    self._add_to_history("model", answer)
                    return answer

            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                    print(f"[AIService] Groq model '{model_name}' hit rate limit. Trying alternate model...")
                    continue
                else:
                    print(f"[AIService] Groq error on {model_name}: {e}")
                    break

        # Fallback to Gemini if all Groq models fail or are rate limited
        if self._gemini_client:
            print("[AIService] Groq unavailable — using Gemini fallback.")
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

            answer = self._clean_response(response.text.strip()) if response.text else ""
            if not answer:
                answer = "I'm here, sir."
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

    def send_with_image(self, user_text: str, image_input, system_context: str = "") -> str:
        """
        Send a message with an image for visual analysis (Gemini Vision or Groq Vision).

        Args:
            user_text: The user's query or prompt about the image/screen.
            image_input: Filepath (str/Path), PIL.Image.Image instance, or raw bytes.
            system_context: Optional system prompt context.
        """
        if not self._initialized:
            return self._stub_response(user_text)

        import io
        import base64
        from PIL import Image

        # Convert input to PIL Image
        pil_img = None
        if isinstance(image_input, Image.Image):
            pil_img = image_input
        elif isinstance(image_input, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, (str, Path)):
            pil_img = Image.open(str(image_input))

        if not pil_img:
            return "I couldn't process the screen capture image, sir."

        # Ensure RGB format
        if pil_img.mode in ("RGBA", "P"):
            pil_img = pil_img.convert("RGB")

        # System prompt
        prompt = (
            f"{system_context}\n\nUser Question about Screen: {user_text}"
            if system_context else
            f"You are MakiAI, personal AI assistant for Mark Vencent Juntilla. Address the user as 'sir'.\n"
            f"Analyze the attached computer screen capture and answer the user's question directly:\n"
            f"User Question: {user_text}\n"
            f"Be concise, clear, and direct. If analyzing code or an error, state the cause and fix clearly. Avoid excessive markdown."
        )

        # 1. Try Gemini Vision first (if available)
        if self._gemini_client:
            try:
                # Resize if excessively large to maintain sub-second latency
                max_dim = 1600
                if max(pil_img.width, pil_img.height) > max_dim:
                    ratio = max_dim / max(pil_img.width, pil_img.height)
                    pil_img = pil_img.resize((int(pil_img.width * ratio), int(pil_img.height * ratio)), Image.LANCZOS)

                response = self._gemini_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[prompt, pil_img],
                )
                answer = self._clean_response(response.text.strip()) if response.text else "I analyzed the camera frame, sir, but couldn't generate a clear description."
                print(f"[AIService] Vision response: {answer}")
                self._add_to_history("user", f"[Vision]: {user_text}")
                self._add_to_history("model", answer)
                return answer
            except Exception as e:
                print(f"[AIService] Gemini Vision error: {e}")
                # Fall through to try Groq vision if available

        # 2. Try Groq Vision fallback
        if self._groq_client:
            try:
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=85)
                b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
                data_url = f"data:image/jpeg;base64,{b64_data}"

                vision_models = ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]
                for model in vision_models:
                    try:
                        response = self._groq_client.chat.completions.create(
                            model=model,
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": prompt},
                                        {"type": "image_url", "image_url": {"url": data_url}},
                                    ],
                                }
                            ],
                            max_tokens=600,
                            temperature=0.4,
                        )
                        raw_ans = response.choices[0].message.content or ""
                        answer = self._clean_response(raw_ans.strip())
                        self._add_to_history("user", f"[Screen Vision]: {user_text}")
                        self._add_to_history("model", answer)
                        return answer
                    except Exception as err:
                        print(f"[AIService] Groq model {model} vision error: {err}")
                        continue
            except Exception as e:
                print(f"[AIService] Groq Vision error: {e}")

        return "I'm unable to analyze your screen right now. Please ensure your Gemini or Groq API key has vision capability enabled in settings."

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

