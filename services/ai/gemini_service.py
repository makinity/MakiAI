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

import os
import re
from typing import Optional


MAX_HISTORY_TURNS = 20


class GeminiService:
    """
    AI service for MakiAI — supports Groq and Gemini.
    Named GeminiService for backward compatibility with existing code.
    """

    GROQ_MODELS = [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
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
                    max_tokens=20,
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

    def send(self, user_text: str, system_context: str = "", **kwargs) -> str:
        """
        Send a message and return the AI response.

        Args:
            user_text:      The user's voice/text command.
            system_context: KB context injected as system prompt.

        Returns:
            AI response string.
        """
        if not system_context and "system_instruction" in kwargs:
            system_context = kwargs["system_instruction"]

        if not self._initialized:
            return self._stub_response(user_text)

        if self._provider == "groq" or (self._groq_client and not self._gemini_client):
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
        if not cleaned or re.search(r"<(?:think|thought)>", cleaned, re.IGNORECASE):
            marker_match = re.search(
                r"(?:(?:\*\*Draft[^\n]*\*\*|\*\*Final Response[^\n]*\*\*|\*\*Response[^\n]*\*\*|Draft:|\*\*Spoken Response[^\n]*\*\*)\s*)(.*?)(?:</(?:think|thought)>|$)",
                text,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if marker_match:
                cleaned = marker_match.group(1).strip()
            else:
                # Remove all think tags and return whatever text remains
                cleaned = re.sub(r"</?(?:think|thought)>", "", text, flags=re.IGNORECASE).strip()

        # 3. Clean any stray closing tags
        cleaned = re.sub(r"</(?:think|thought)>", "", cleaned, flags=re.IGNORECASE)

        # 4. Look for explicit response headers on their own line or markdown block
        resp_match = re.search(
            r"(?:^|\n)(?:#{1,4}\s*|\*{1,2}|)(?:Final\s+Response|Spoken\s+Response|Draft\s+Response|My\s+Response|Direct\s+Response|Spoken|Reply)(?:\*{1,2}|)\s*[:\-*]+\s*([\s\S]+)$",
            cleaned,
            flags=re.IGNORECASE
        )
        if resp_match:
            cand = resp_match.group(1).strip()
            if cand and not re.match(r"^(?:Here'?s a thinking|1\.\s*\*\*Analyze|Let's analyze)", cand, re.IGNORECASE):
                cleaned = cand

        # 5. Check for 'Here's a thinking process:' or 'Thinking Process:' or numbered analysis breakdown
        thinking_match = re.search(
            r"(?:^|\b)(?:Here'?s (?:a |the )?thinking process:?|Thinking Process:?|\*\*Thinking Process:\*\*|Let'?s analyze\b|1\.\s*\*\*(?:Analyze|Deconstruct|Context|Understand)[^\*]*\*\*)",
            cleaned,
            flags=re.IGNORECASE
        )
        if thinking_match:
            # If there are separate paragraphs, find the final conversational paragraph
            paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
            valid_paras = []
            for p in paragraphs:
                if re.match(r"^(?:Here'?s (?:a |the )?thinking|Thinking Process|Let'?s analyze|\d+\.\s*\*\*|[-*•]\s*(?:User says|Translation|Meaning|This is in|Location:))", p, re.IGNORECASE):
                    continue
                if not re.search(r"\b(?:Analyze User Input|Formulate Response|Zamboangueño|Specifically Zamboangueño)\b", p, re.IGNORECASE):
                    valid_paras.append(p)

            if valid_paras:
                cleaned = valid_paras[-1]
            else:
                lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
                valid_lines = [
                    l for l in lines
                    if not re.match(r"^(?:Here'?s|\d+\.|\*\*|[-*•]|Translation|Full meaning|Meaning|Context|User says|Tone:)", l, re.IGNORECASE)
                    and not re.search(r"\b(?:Analyze User Input|Formulate Response|Zamboangueño)\b", l, re.IGNORECASE)
                ]
                if valid_lines:
                    cleaned = valid_lines[-1]
                else:
                    quote_matches = re.findall(r'"([^"]{5,})"', cleaned)
                    meaning_match = re.search(r'(?:Full meaning|Translation|Meaning):\s*"([^"]+)"', cleaned, re.IGNORECASE)
                    if meaning_match:
                        cleaned = f"Mukhang sinabi ninyo sir: '{meaning_match.group(1)}'. Opo sir!"
                    elif quote_matches:
                        last_quote = quote_matches[-1]
                        if not any(last_quote.lower().startswith(x) for x in ["kila lamu", "http", "location:", "user says"]):
                            cleaned = f"Mukhang sinabi ninyo sir: '{last_quote}'. Opo sir!"
                        else:
                            cleaned = "Naintindihan ko po sir. Kamusta po kayo?"
                    else:
                        cleaned = "Naintindihan ko po sir, handa po akong tumulong."

        # 6. Clean meta-planning / third-person monologue headers (e.g. "The user is asking for... I need to...")
        meta_pattern = r"^(?:The user is (?:asking|saying|requesting)|I need to (?:check|respond|answer)|Let'?s check|AI model running|As an AI|I should respond|The prompt says)\b"
        if re.search(meta_pattern, cleaned, re.IGNORECASE):
            draft_match = re.search(
                r"(?:(?:I will say|I should say|My response:|Response:|Draft:|\*\*Draft[^\n]*\*\*|\*\*Response[^\n]*\*\*)\s*)(.*)",
                cleaned,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if draft_match:
                cleaned = draft_match.group(1).strip()
            else:
                paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
                candidate_p = [p for p in paragraphs if not re.match(r"^(?:The user|I need to|Let's check|Wait,|AI model|As an AI|I should)\b", p, re.IGNORECASE)]
                if candidate_p:
                    cleaned = candidate_p[-1]
                else:
                    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
                    valid_s = [
                        s for s in sentences
                        if not re.search(r"\b(?:The user is|I need to check|I should respond|I should check|AI model|prompt says|operating system to close|direct access to the user|hallucinating|in character as Maki|as an AI)\b", s, re.IGNORECASE)
                    ]
                    cleaned = " ".join(valid_s).strip() if valid_s else "I'm right here, sir. How can I help?"

        # Clean residual markdown asterisks and bullet symbols from spoken response
        cleaned = re.sub(r"\*{1,3}", "", cleaned)
        cleaned = re.sub(r"^[-*•]\s*", "", cleaned)
        return cleaned.strip()

    def _send_groq(self, user_text: str, system_context: str, depth: int = 0) -> str:
        """Send via Groq API with streaming for faster response and model rotation on 429."""
        # Bound system context to 15,000 chars so full workflow tables and KB context fit comfortably
        bounded_ctx = system_context[:15000] if len(system_context) > 15000 else system_context
        app_name = os.getenv("APP_NAME", "MakiAI")
        user_name = os.getenv("USER_NAME", "Sir")
        kb_path = os.getenv("KB_PATH", r"C:\Knowledge-Base")
        storage_path = os.getenv("MAKI_SYNC_PATH", r"C:\MakiSync Storage")

        base_prompt = bounded_ctx if bounded_ctx else f"""You are {app_name}, a personal AI assistant for {user_name} inspired by Jarvis from Iron Man. Always address the user as 'sir'. Be warm, conversational, and natural. Keep responses concise and spoken aloud in clear English. No markdown or bullet points.

You have full access to:
- {kb_path} — user's schedule, deadlines, projects, preferences
- {storage_path} — organized file storage (School, Work, Personal, Freelance, {app_name} with Screenshots/Photos/Recordings in date folders)
You CAN search, open, and manage files in these locations."""
        
        system_prompt = f"""{base_prompt}

CRITICAL RULES:
- NEVER output meta-analysis, reasoning steps, translation notes, or third-person commentary about the user (e.g., 'Here's a thinking process: 1. Analyze User Input...').
- Speak directly to sir in character as Maki immediately in natural English.
- Do NOT output any <think> tags or reasoning steps."""

        messages = [{"role": "system", "content": system_prompt}]

        for turn in self._history[-(MAX_HISTORY_TURNS * 2):]:
            role = "user" if turn["role"] == "user" else "assistant"
            messages.append({"role": role, "content": turn["text"]})

        messages.append({"role": "user", "content": user_text})

        # Try active model, rotate if rate limited
        candidate_models = [self._groq_model] + [m for m in self.GROQ_MODELS if m != self._groq_model]

        for model_name in candidate_models:
            for attempt in range(2):
                try:
                    stream = self._groq_client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=250,
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
                        if attempt == 0:
                            import time
                            time.sleep(1.5)
                            continue
                    print(f"[AIService] Groq error on {model_name}: {e}")
                    break


        # Fallback to Gemini if all Groq models fail or are rate limited (one-shot, no loop)
        if self._gemini_client and depth == 0:
            print("[AIService] Groq unavailable — using Gemini fallback.")
            return self._send_gemini(user_text, bounded_ctx, depth=depth + 1)

        return "I had trouble thinking. Please try again."

    def _send_gemini(self, user_text: str, system_context: str, depth: int = 0) -> str:
        """Send via Gemini API with automatic model rotation on temporary 503/429 errors."""
        bounded_ctx = system_context[:15000] if len(system_context) > 15000 else system_context
        full_prompt = f"{bounded_ctx}\n\n---\n\nUser: {user_text}" if bounded_ctx else user_text
        gemini_models = ["gemini-3.6-flash"]


        for model_name in gemini_models:
            try:
                response = self._gemini_client.models.generate_content(
                    model=model_name,
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
                print(f"[AIService] Gemini error on {model_name}: {e}")
                if "503" in error_str or "unavailable" in error_str or "quota" in error_str or "rate" in error_str or "404" in error_str:
                    continue
                break

        # Fallback to Groq if Gemini is unavailable (one-shot, no loop)
        if self._groq_client and depth == 0:
            print("[AIService] Gemini unavailable — trying Groq backup...")
            return self._send_groq(user_text, bounded_ctx, depth=depth + 1)

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

        app_name = os.getenv("APP_NAME", "MakiAI")
        user_name = os.getenv("USER_NAME", "Sir")
        prompt = (
            f"{system_context}\n\nUser Question about Screen: {user_text}"
            if system_context else
            f"You are {app_name}, personal AI assistant for {user_name}. Address the user as 'sir'.\n"
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

