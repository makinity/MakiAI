"""
MakiAI — Intelligent Multi-Key Auto-Rotation Pool (key_rotator.py)

Features:
  1. Multi-key ring buffer for Groq and Gemini (from GROQ_API_KEYS / GEMINI_API_KEYS in .env).
  2. Startup quota health scanner (reads live rate-limit headers in parallel).
  3. Proactive low-quota auto-switch (rotates when remaining quota < 15%).
  4. Reactive failover on 429 / RateLimitError (< 50ms instant retry on next key).
  5. Timed cooldown loop (60s burst reset & daily midnight recovery).
  6. Thread-safe round-robin load distribution.
"""

import os
import re
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class KeyInfo:
    key: str
    masked: str
    provider: str  # "groq" | "gemini"
    status: str = "healthy"  # "healthy" | "low_quota" | "cooldown" | "exhausted" | "invalid"
    cooldown_until: float = 0.0
    remaining_tokens: Optional[int] = None
    limit_tokens: Optional[int] = None
    remaining_requests: Optional[int] = None
    limit_requests: Optional[int] = None
    reset_seconds: Optional[float] = None
    total_success: int = 0
    total_errors: int = 0
    last_used: float = 0.0
    last_error: str = ""

    @property
    def token_percent_remaining(self) -> Optional[float]:
        if self.remaining_tokens is not None and self.limit_tokens and self.limit_tokens > 0:
            return round((self.remaining_tokens / self.limit_tokens) * 100.0, 1)
        return None

    @property
    def is_available(self) -> bool:
        if self.status == "invalid":
            return False
        if self.status in ("cooldown", "exhausted"):
            if time.time() >= self.cooldown_until:
                self.status = "healthy"
                return True
            return False
        return True


class KeyRotator:
    """
    Thread-safe multi-key rotation and quota management engine.
    Singleton accessible across AI and STT services.
    """

    _instance: Optional["KeyRotator"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(KeyRotator, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._pools: Dict[str, List[KeyInfo]] = {"groq": [], "gemini": []}
        self._indexes: Dict[str, int] = {"groq": 0, "gemini": 0}
        self._rotation_lock = threading.Lock()
        self.reload_keys_from_env()
        self._initialized = True

    # ─── Key Parsing ──────────────────────────────────────────────────────────

    @staticmethod
    def _mask_key(key: str) -> str:
        if not key or len(key) < 8:
            return "****"
        return f"{key[:6]}...{key[-4:]}"

    def reload_keys_from_env(self) -> None:
        """Parse keys from environment variables."""
        with self._rotation_lock:
            self._pools["groq"] = self._parse_keys_for_provider("groq", "GROQ_API_KEYS", "GROQ_API_KEY")
            self._pools["gemini"] = self._parse_keys_for_provider("gemini", "GEMINI_API_KEYS", "GEMINI_API_KEY")
            self._indexes["groq"] = 0
            self._indexes["gemini"] = 0

    def _parse_keys_for_provider(self, provider: str, multi_env: str, single_env: str) -> List[KeyInfo]:
        raw_multi = os.getenv(multi_env, "").strip()
        raw_single = os.getenv(single_env, "").strip()
        keys_found: List[str] = []

        if raw_multi:
            # Handle comma-separated, newline-separated, or semicolon-separated keys
            parts = [k.strip().strip('"').strip("'") for k in re.split(r"[,;\n\r]+", raw_multi) if k.strip()]
            for p in parts:
                if p and p not in keys_found and not p.lower().startswith("your_"):
                    keys_found.append(p)

        if raw_single and raw_single not in keys_found and not raw_single.lower().startswith("your_"):
            keys_found.append(raw_single)

        pool: List[KeyInfo] = []
        for k in keys_found:
            pool.append(KeyInfo(key=k, masked=self._mask_key(k), provider=provider))

        return pool

    # ─── Key Selection & Rotation ─────────────────────────────────────────────

    def get_active_key(self, provider: str) -> Optional[str]:
        """
        Get the next best healthy API key for the requested provider in round-robin order.
        Auto-recovers keys whose cooldown has expired.
        """
        with self._rotation_lock:
            pool = self._pools.get(provider.lower(), [])
            if not pool:
                return None

            now = time.time()
            # 1. First pass: look for healthy, non-low-quota keys
            healthy_keys = [k for k in pool if k.is_available and k.status != "low_quota"]
            if healthy_keys:
                idx = self._indexes[provider] % len(healthy_keys)
                selected = healthy_keys[idx]
                self._indexes[provider] = (idx + 1) % len(healthy_keys)
                selected.last_used = now
                return selected.key

            # 2. Second pass: use low-quota keys if no 100% fresh keys remain
            usable_keys = [k for k in pool if k.is_available]
            if usable_keys:
                idx = self._indexes[provider] % len(usable_keys)
                selected = usable_keys[idx]
                self._indexes[provider] = (idx + 1) % len(usable_keys)
                selected.last_used = now
                return selected.key

            # 3. All keys are in cooldown/exhausted — return the one nearest to cooldown expiry
            cooldown_keys = [k for k in pool if k.status != "invalid"]
            if cooldown_keys:
                cooldown_keys.sort(key=lambda x: x.cooldown_until)
                best = cooldown_keys[0]
                best.last_used = now
                return best.key

            return None

    def report_success(self, provider: str, key: str, headers: Optional[Dict[str, Any]] = None) -> None:
        """Mark request as successful and update live rate-limit quotas from headers."""
        with self._rotation_lock:
            pool = self._pools.get(provider.lower(), [])
            for k in pool:
                if k.key == key:
                    k.total_success += 1
                    if k.status in ("cooldown", "exhausted"):
                        k.status = "healthy"
                    if headers:
                        self._extract_headers_quota(k, headers)
                    break

    def report_rate_limit(self, provider: str, key: str, error_msg: str = "") -> Optional[str]:
        """
        Record a 429 / RateLimit error. Sets appropriate cooldown and returns the next healthy key.
        """
        err_lower = error_msg.lower()
        now = time.time()

        # Check if it's daily exhaustion vs burst per-minute exhaustion
        is_daily = any(w in err_lower for w in ["daily", "tokens per day", "tpd", "resource_exhausted", "quota exceeded"])

        if is_daily:
            # Calculate seconds until midnight UTC
            now_utc = datetime.now(timezone.utc)
            midnight_utc = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            cooldown_sec = max(60.0, (midnight_utc - now_utc).total_seconds())
            cooldown_type = f"daily quota ({int(cooldown_sec // 3600)}h remaining)"
            new_status = "exhausted"
        else:
            # Per-minute burst limit (RPM / TPM) — 60s cooldown is sufficient
            cooldown_sec = 60.0
            cooldown_type = "60s burst limit cooldown"
            new_status = "cooldown"

        with self._rotation_lock:
            pool = self._pools.get(provider.lower(), [])
            target_info: Optional[KeyInfo] = None
            for k in pool:
                if k.key == key:
                    target_info = k
                    k.status = new_status
                    k.cooldown_until = now + cooldown_sec
                    k.total_errors += 1
                    k.last_error = error_msg[:120]
                    print(f"[KeyRotator] [RATE LIMIT] {provider.upper()} key {k.masked} hit {cooldown_type}. Set to {new_status}.")
                    break

        # Return next available key immediately
        next_key = self.get_active_key(provider)
        if next_key and target_info and next_key != key:
            next_masked = self._mask_key(next_key)
            print(f"[KeyRotator] [AUTO-SWITCH] Rotated to next {provider.upper()} key: {next_masked}")
        return next_key

    def _extract_headers_quota(self, key_info: KeyInfo, headers: Dict[str, Any]) -> None:
        """Parse standard Groq / Cloud rate limit headers."""
        if not headers:
            return

        # Case-insensitive header dictionary
        h = {str(k).lower(): str(v) for k, v in headers.items()}

        # 1. Remaining tokens
        if "x-ratelimit-remaining-tokens" in h:
            try:
                key_info.remaining_tokens = int(h["x-ratelimit-remaining-tokens"])
            except ValueError:
                pass

        if "x-ratelimit-limit-tokens" in h:
            try:
                key_info.limit_tokens = int(h["x-ratelimit-limit-tokens"])
            except ValueError:
                pass

        # 2. Remaining requests
        if "x-ratelimit-remaining-requests" in h:
            try:
                key_info.remaining_requests = int(h["x-ratelimit-remaining-requests"])
            except ValueError:
                pass

        if "x-ratelimit-limit-requests" in h:
            try:
                key_info.limit_requests = int(h["x-ratelimit-limit-requests"])
            except ValueError:
                pass

        # 3. Check low quota threshold (< 15% tokens remaining)
        pct = key_info.token_percent_remaining
        if pct is not None:
            if pct < 15.0 and key_info.status == "healthy":
                key_info.status = "low_quota"
                print(f"[KeyRotator] [LOW QUOTA] Low tokens on {key_info.provider.upper()} {key_info.masked} ({pct}% remaining). Preferring standby keys.")
            elif pct >= 15.0 and key_info.status == "low_quota":
                key_info.status = "healthy"

    # ─── Startup Health Scanner ───────────────────────────────────────────────

    def scan_pool_health(self) -> Dict[str, Any]:
        """
        Probe all configured keys in parallel on startup to read live quota headers and status.
        Runs in ~200-400ms.
        """
        results = {"groq": [], "gemini": []}
        all_keys: List[KeyInfo] = []

        with self._rotation_lock:
            for provider, pool in self._pools.items():
                all_keys.extend(pool)

        if not all_keys:
            return results

        def _probe_key(info: KeyInfo) -> KeyInfo:
            if info.provider == "groq":
                self._probe_groq_key(info)
            elif info.provider == "gemini":
                self._probe_gemini_key(info)
            return info

        # Probe in parallel with max 10 workers
        with ThreadPoolExecutor(max_workers=min(10, len(all_keys))) as executor:
            futures = [executor.submit(_probe_key, k) for k in all_keys]
            for future in as_completed(futures):
                try:
                    res = future.result()
                    results[res.provider].append(res)
                except Exception:
                    pass

        return results

    def _probe_groq_key(self, info: KeyInfo) -> None:
        try:
            from groq import Groq
            client = Groq(api_key=info.key)
            # Send 1-token probe to check health and capture headers
            resp = client.chat.completions.with_raw_response.create(
                model="qwen/qwen3.8-27b",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            headers = dict(resp.headers)
            info.status = "healthy"
            self._extract_headers_quota(info, headers)
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "rate limit" in err:
                info.status = "cooldown"
                info.cooldown_until = time.time() + 60.0
                info.last_error = "Rate limit detected during probe"
            elif "invalid" in err or "api_key" in err or "auth" in err:
                info.status = "invalid"
                info.last_error = "Invalid API key"
            else:
                info.status = "healthy"

    def _probe_gemini_key(self, info: KeyInfo) -> None:
        try:
            import logging
            logging.getLogger("google.genai").setLevel(logging.ERROR)
            from google import genai
            client = genai.Client(api_key=info.key)
            resp = client.models.generate_content(
                model="gemini-3.6-flash",
                contents="hi",
            )
            if resp and resp.text:
                info.status = "healthy"
            else:
                info.status = "healthy"
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "resource_exhausted" in err:
                info.status = "exhausted"
                info.cooldown_until = time.time() + 3600.0
                info.last_error = "Quota exceeded during probe"
            elif "invalid" in err or "api_key" in err:
                info.status = "invalid"
                info.last_error = "Invalid API key"
            else:
                info.status = "healthy"

    # ─── Dashboard Summary ────────────────────────────────────────────────────

    def get_status_summary(self) -> str:
        """Return a formatted status table of the entire key pool."""
        lines = ["=== MakiAI Key Rotator Pool Dashboard ==="]
        for provider in ["groq", "gemini"]:
            pool = self._pools.get(provider, [])
            if not pool:
                lines.append(f"[{provider.upper()}] No keys configured.")
                continue

            lines.append(f"[{provider.upper()} POOL] ({len(pool)} keys configured):")
            for idx, k in enumerate(pool, start=1):
                status_tag = "[READY]" if k.status == "healthy" else ("[LOW]" if k.status == "low_quota" else f"[{k.status.upper()}]")
                quota_str = f"Tokens: {k.token_percent_remaining}%" if k.token_percent_remaining is not None else "Ready"
                if k.status in ("cooldown", "exhausted"):
                    rem = max(0, int(k.cooldown_until - time.time()))
                    quota_str = f"Cooldown: {rem}s left"
                lines.append(f"  {idx}. {status_tag} {k.masked} | Status: {k.status.upper()} | {quota_str} | Uses: {k.total_success}")
        return "\n".join(lines)


# Global singleton instance
key_rotator = KeyRotator()
