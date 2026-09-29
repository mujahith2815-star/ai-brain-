"""
Google Gemini Flash Engine for Orvix Sphere.
Provides high-speed, free-tier primary cognitive reasoning with rate-limit protection,
exponential backoff, token usage tracking, streaming, and tool execution support.
"""

from __future__ import annotations
import json
import logging
import os
import re
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

# Suppress standard deprecation warnings from google.generativeai if present
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    GENAI_INSTALLED = True
except ImportError:
    genai = None
    google_exceptions = None
    GENAI_INSTALLED = False

from config.api_config import api_config
from tools.api_cost_tracker import api_cost_tracker

logger = logging.getLogger("orvix.tools.gemini_engine")

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "gemini_api.log"


class GeminiEngine:
    """Primary reasoning engine utilizing Google Gemini Flash."""

    name: str = "gemini"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return other.lower() in ("gemini", "cloud", "gemini-2.0-flash", "gemini_engine")
        return self is other

    def __hash__(self) -> int:
        return id(self)

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = (api_key or api_config.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
        self.model_name = (model_name or api_config.default_model or "gemini-2.0-flash").strip()
        self._model = None
        self._configured_key = None

        if self.api_key and GENAI_INSTALLED:
            self._configure_sdk()

    def _configure_sdk(self) -> None:
        """Configures the google-generativeai SDK with current API key."""
        if not GENAI_INSTALLED or not self.api_key:
            return
        try:
            genai.configure(api_key=self.api_key)
            self._configured_key = self.api_key
            self._model = genai.GenerativeModel(model_name=self.model_name)
        except Exception as e:
            logger.warning(f"Error configuring Gemini SDK: {e}")
            self._model = None

    def is_available(self) -> bool:
        """Checks if Gemini Flash is available (SDK installed and API key set)."""
        # Refresh key in case it was updated in environment or config
        current_key = (api_config.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
        if current_key and current_key != self.api_key:
            self.api_key = current_key
            self._configure_sdk()

        return bool(GENAI_INSTALLED and self.api_key and len(self.api_key) > 5)

    def _log_api_call(
        self,
        prompt_snippet: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        duration_sec: float,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        """Appends structured audit log to logs/gemini_api.log."""
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "total_tokens": tokens_in + tokens_out,
                "duration_sec": round(duration_sec, 3),
                "status": status,
                "prompt_sample": prompt_snippet[:100].replace("\n", " "),
                "error": error,
            }
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.debug(f"Failed to append to gemini_api.log: {e}")

    def count_tokens(self, prompt: str) -> int:
        """
        Counts prompt tokens using Gemini's tokenizer if available,
        or falls back to a fast byte-pair heuristic.
        """
        if not prompt:
            return 0
        if self.is_available() and self._model is not None:
            try:
                res = self._model.count_tokens(prompt)
                if hasattr(res, "total_tokens"):
                    return int(res.total_tokens)
            except Exception:
                pass
        # Fallback heuristic: ~4 chars / token or words * 1.3
        return max(1, int(len(prompt.split()) * 1.33))

    def _wait_for_rate_limit(self) -> None:
        """Ensures request adheres to the 14 RPM quota window."""
        allowed, wait_sec = api_cost_tracker.check_rate_limit(max_rpm=api_config.rate_limit_rpm)
        if not allowed and wait_sec > 0:
            logger.info(f"GeminiEngine: Rate limit cushion reached. Waiting {wait_sec}s...")
            time.sleep(min(wait_sec, 10.0))

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        Generates a text completion using Gemini Flash with automatic rate limiting
        and exponential backoff retry logic.
        """
        if not self.is_available():
            raise RuntimeError("GeminiEngine is unavailable: Missing GEMINI_API_KEY or SDK not installed.")

        if self._model is None or self._configured_key != self.api_key:
            self._configure_sdk()

        retries = 0
        max_retries = api_config.max_retries
        backoff_sec = 2.0
        start_time = time.time()
        tokens_in = self.count_tokens(prompt)

        # Dynamic model fallback candidates
        candidate_models = [self.model_name] + [m for m in api_config.fallback_models if m != self.model_name]

        last_error = None
        for model_cand in candidate_models:
            active_model = genai.GenerativeModel(
                model_name=model_cand,
                system_instruction=system_instruction if system_instruction else None,
            )
            model_retries = 0
            while model_retries <= max_retries:
                try:
                    self._wait_for_rate_limit()
                    api_cost_tracker.record_request_start()

                    gen_config = genai.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                    )
                    
                    response = active_model.generate_content(
                        prompt,
                        generation_config=gen_config,
                    )

                    text_output = ""
                    if response and response.text:
                        text_output = response.text.strip()

                    duration = time.time() - start_time
                    tokens_out = self.count_tokens(text_output)

                    # Log usage and cost
                    api_cost_tracker.log_request(
                        model=model_cand,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost=0.0,  # Free tier
                    )
                    self._log_api_call(
                        prompt_snippet=prompt,
                        model=model_cand,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        duration_sec=duration,
                        status="SUCCESS",
                    )
                    logger.info(f"GeminiEngine: Successfully generated response using model '{model_cand}'.")
                    if self.model_name != model_cand:
                        logger.info(f"GeminiEngine: Updating active model from '{self.model_name}' to '{model_cand}'.")
                        self.model_name = model_cand
                    return text_output

                except Exception as e:
                    last_error = e
                    duration = time.time() - start_time
                    err_str = str(e)
                    is_404 = (
                        "404" in err_str
                        or "not found" in err_str.lower()
                        or "not_found" in err_str.lower()
                        or (google_exceptions and isinstance(e, getattr(google_exceptions, "NotFound", type(None))))
                    )
                    if is_404:
                        logger.warning(
                            f"GeminiEngine: Model '{model_cand}' returned 404 / NotFound ({err_str}). "
                            "Trying next fallback model..."
                        )
                        break  # Break retry loop to try next candidate model

                    is_rate_limit = any(k in err_str.lower() for k in ["429", "resource_exhausted", "quota", "rate limit"])
                    is_transient = any(k in err_str.lower() for k in ["timeout", "connection", "503", "unavailable"])

                    if (is_rate_limit or is_transient) and model_retries < max_retries:
                        model_retries += 1
                        sleep_time = backoff_sec * (2 ** (model_retries - 1))
                        logger.warning(f"Gemini API error ({err_str}). Retrying in {sleep_time:.1f}s (Attempt {model_retries}/{max_retries})...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        break  # Try next candidate model or raise

        # All retries / models exhausted
        duration = time.time() - start_time
        self._log_api_call(
            prompt_snippet=prompt,
            model=self.model_name,
            tokens_in=tokens_in,
            tokens_out=0,
            duration_sec=duration,
            status="FAILED",
            error=str(last_error),
        )
        raise RuntimeError(f"GeminiEngine generation failed after retries: {last_error}")

    def generate_with_tools(
        self,
        prompt: str,
        tools: Optional[List[Any]] = None,
        max_steps: int = 6,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes reasoning with tool-calling capabilities.
        Extracts structured tool calls either from native Gemini function calls
        or from structured JSON output schema ({'actions': [...]}).
        """
        if not self.is_available():
            raise RuntimeError("GeminiEngine is unavailable for tool generation.")

        # Ensure prompt instructs JSON action schema if raw tools list given
        prompt_augmented = prompt
        if tools and not any(k in prompt.lower() for k in ["return json", "json output", "actions"]):
            prompt_augmented += "\n\nIf you need to execute tools, return a valid JSON action plan: {\"actions\": [{\"tool\": \"tool_name\", \"args\": {...}}]} or {\"action\": \"final_answer\", \"response\": \"...\"}"

        raw_text = self.generate(prompt_augmented, system_instruction=system_instruction)

        # Parse potential tool calls
        tool_calls: List[Dict[str, Any]] = []
        text_content = raw_text

        # 1. Parse JSON action schema (direct, stripped codeblock, or outermost object)
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)

        candidates = [clean_text]
        m = re.search(r"(\{[\s\S]*\})", clean_text)
        if m and m.group(1) != clean_text:
            candidates.append(m.group(1))

        for cand in candidates:
            try:
                parsed = json.loads(cand)
                if isinstance(parsed, dict):
                    if "actions" in parsed and isinstance(parsed["actions"], list):
                        for act in parsed["actions"]:
                            if isinstance(act, dict) and "tool" in act:
                                tool_calls.append({
                                    "tool": act["tool"],
                                    "args": act.get("args", act.get("parameters", {})),
                                })
                    elif parsed.get("action") == "call_tool":
                        tool_calls.append({
                            "tool": parsed.get("tool_name", parsed.get("tool", "")),
                            "args": parsed.get("parameters", parsed.get("args", {})),
                        })
                    if tool_calls:
                        break
            except Exception:
                continue

        return {
            "text": text_content,
            "tool_calls": tool_calls,
            "has_tools": len(tool_calls) > 0,
        }

    def stream(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_instruction: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Streams text chunks token-by-token from Gemini Flash."""
        if not self.is_available():
            raise RuntimeError("GeminiEngine is unavailable: Missing GEMINI_API_KEY or SDK.")

        if self._model is None or self._configured_key != self.api_key:
            self._configure_sdk()

        start_time = time.time()
        tokens_in = self.count_tokens(prompt)

        candidate_models = [self.model_name] + [m for m in api_config.fallback_models if m != self.model_name]
        last_error = None

        for model_cand in candidate_models:
            try:
                self._wait_for_rate_limit()
                api_cost_tracker.record_request_start()

                active_model = genai.GenerativeModel(
                    model_name=model_cand,
                    system_instruction=system_instruction if system_instruction else None,
                )
                gen_config = genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
                response = active_model.generate_content(
                    prompt,
                    generation_config=gen_config,
                    stream=True,
                )

                accumulated_text: List[str] = []
                for chunk in response:
                    if chunk and chunk.text:
                        accumulated_text.append(chunk.text)
                        yield chunk.text

                full_text = "".join(accumulated_text)
                tokens_out = self.count_tokens(full_text)
                duration = time.time() - start_time

                api_cost_tracker.log_request(
                    model=model_cand,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=0.0,
                )
                self._log_api_call(
                    prompt_snippet=prompt,
                    model=model_cand,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    duration_sec=duration,
                    status="SUCCESS",
                )
                logger.info(f"GeminiEngine: Successfully streamed response using model '{model_cand}'.")
                if self.model_name != model_cand:
                    logger.info(f"GeminiEngine: Updating active model from '{self.model_name}' to '{model_cand}'.")
                    self.model_name = model_cand
                return

            except Exception as e:
                last_error = e
                err_str = str(e)
                is_404 = (
                    "404" in err_str
                    or "not found" in err_str.lower()
                    or "not_found" in err_str.lower()
                    or (google_exceptions and isinstance(e, getattr(google_exceptions, "NotFound", type(None))))
                )
                if is_404:
                    logger.warning(
                        f"GeminiEngine: Model '{model_cand}' returned 404 / NotFound during stream ({err_str}). "
                        "Trying next fallback model..."
                    )
                    continue
                else:
                    duration = time.time() - start_time
                    self._log_api_call(
                        prompt_snippet=prompt,
                        model=model_cand,
                        tokens_in=tokens_in,
                        tokens_out=0,
                        duration_sec=duration,
                        status="FAILED",
                        error=str(e),
                    )
                    raise

        duration = time.time() - start_time
        self._log_api_call(
            prompt_snippet=prompt,
            model=self.model_name,
            tokens_in=tokens_in,
            tokens_out=0,
            duration_sec=duration,
            status="FAILED",
            error=str(last_error),
        )
        raise RuntimeError(f"GeminiEngine stream failed after trying fallback models: {last_error}")


# Global singleton engine instance
gemini_engine = GeminiEngine()
