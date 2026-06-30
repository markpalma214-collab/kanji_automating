"""
ai/client.py — thin wrapper around the official Groq Python SDK.
All network calls and SDK-specific error handling are centralized here so
the rest of the app never imports `groq` directly, and so raw SDK
errors/tracebacks never reach the GUI.

AIClient always raises AIError with an already-friendly, user-facing
message (str(exc)). The original exception is preserved on
`exc.__cause__` for logging/debugging only — it is never shown in the UI.

Model choice: llama-3.3-70b-versatile is Groq's strongest general-purpose
hosted model and handles Japanese generation/comprehension well (it's a
multilingual instruction-tuned model), while still running at Groq's
characteristic low latency — a good fit for an app that fires off several
short generation requests per study session.
"""

import concurrent.futures
import json

from . import config

try:
    from groq import Groq
except ImportError:  # pragma: no cover - surfaced as a friendly error instead
    Groq = None


REQUEST_TIMEOUT_SECONDS = 30

MSG_QUOTA = (
    "⚠ The AI service is temporarily unavailable because the free API quota/rate "
    "limit has been reached.\nPlease wait a few minutes and try again."
)
MSG_NO_INTERNET = "⚠ No internet connection detected."
MSG_NO_API_KEY = "⚠ Groq API key was not found.\nPlease check your .env file."
MSG_TIMEOUT = "⚠ The AI took too long to respond. Please try again."
MSG_AUTH = "⚠ Groq API key was not found.\nPlease check your .env file."


def _generic_message(context: str) -> str:
    return f"⚠ Something went wrong while generating the {context}.\nPlease try again."


class AIError(Exception):
    """Raised for any problem talking to the AI provider (missing key,
    network failure, quota, timeout, malformed response, etc). The
    message is already user-friendly and safe to display directly in the
    GUI."""


def _classify_error(exc: Exception, context: str) -> str:
    """Maps an arbitrary SDK/network exception to a friendly message.
    Never includes the raw exception text or traceback."""
    type_name = type(exc).__name__.lower()
    text = str(exc).lower()

    # Quota / rate limit (HTTP 429)
    if (
        "429" in text or "quota" in text or "rate limit" in text
        or "ratelimiterror" in type_name
    ):
        return MSG_QUOTA

    # Timeouts
    if (
        isinstance(exc, (TimeoutError, concurrent.futures.TimeoutError))
        or "timeout" in type_name
        or "timed out" in text
    ):
        return MSG_TIMEOUT

    # Auth / API key problems (401/403, permission denied, invalid key)
    if (
        "401" in text or "403" in text or "permission" in text
        or "unauthenticated" in text or "unauthorized" in text
        or "authenticationerror" in type_name or "permissiondeniederror" in type_name
        or "invalid api key" in text
    ):
        return MSG_AUTH

    # Network / connectivity problems
    if (
        "connectionerror" in type_name or "apiconnectionerror" in type_name
        or "connection" in text or "network" in text or "name resolution" in text
        or "name or service not known" in text or "nodename nor servname" in text
        or "temporary failure in name resolution" in text
        or "getaddrinfo" in text or "max retries exceeded" in text
        or "failed to establish a new connection" in text
        or "gaierror" in type_name or "urlerror" in type_name
    ):
        return MSG_NO_INTERNET

    # Server-side problems (500s)
    if (
        "internalservererror" in type_name or "service unavailable" in text
        or "503" in text or "500" in text or "502" in text
    ):
        return _generic_message(context)

    return _generic_message(context)


class AIClient:
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        if Groq is None:
            raise AIError(
                "⚠ The Groq library is not installed.\nRun: pip install groq"
            )

        self.api_key = api_key or config.get_api_key()
        if not self.api_key:
            raise AIError(MSG_NO_API_KEY)

        self.model_name = model_name or self.DEFAULT_MODEL
        try:
            self._client = Groq(api_key=self.api_key, timeout=REQUEST_TIMEOUT_SECONDS)
        except Exception as exc:
            raise AIError(_classify_error(exc, "connection")) from exc

    # -- timeout-enforced call ------------------------------------------
    def _call_with_timeout(self, fn, *args, **kwargs):
        """Runs fn(*args, **kwargs) with a hard timeout, regardless of
        whether the underlying SDK/transport honors its own timeout."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn, *args, **kwargs)
            try:
                return future.result(timeout=REQUEST_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError as exc:
                raise AIError(MSG_TIMEOUT) from exc

    def _complete(self, prompt: str, temperature: float, json_mode: bool):
        kwargs = dict(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return self._client.chat.completions.create(**kwargs)

    # -- core calls -----------------------------------------------------
    def generate_json(self, prompt: str, temperature: float = 0.9, context: str = "content") -> dict:
        """Sends `prompt` and parses the response as JSON. Always raises
        AIError with a friendly, display-safe message on failure."""
        try:
            response = self._call_with_timeout(self._complete, prompt, temperature, True)
        except AIError:
            raise
        except Exception as exc:
            raise AIError(_classify_error(exc, context)) from exc

        text = self._extract_text(response, context)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIError(_generic_message(context)) from exc

    def generate_text(self, prompt: str, temperature: float = 0.9, context: str = "content") -> str:
        try:
            response = self._call_with_timeout(self._complete, prompt, temperature, False)
        except AIError:
            raise
        except Exception as exc:
            raise AIError(_classify_error(exc, context)) from exc
        return self._extract_text(response, context)

    @staticmethod
    def _extract_text(response, context: str = "content") -> str:
        try:
            text = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError):
            text = None
        if not text:
            raise AIError(_generic_message(context))
        return text


# Backwards-compatible aliases — older code/imports that still reference
# the original Gemini-era class/exception names keep working unchanged.
GeminiClient = AIClient
GeminiError = AIError
