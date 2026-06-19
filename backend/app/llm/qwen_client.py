from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import httpx

from app import settings


RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


class QwenClientError(RuntimeError):
    """Controlled error for Qwen configuration, transport, or response failures."""

    def __init__(
        self,
        message: str,
        *,
        reason_code: str,
        attempt_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.attempt_count = attempt_count


@dataclass(frozen=True)
class QwenStructuredResult:
    payload: dict[str, Any]
    model: str
    attempt_count: int


def _chat_completion_url(base_url: str) -> str:
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/chat/completions"):
        return clean_url
    return f"{clean_url}/chat/completions"


def _strip_json_fence(content: str) -> str:
    clean = content.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1] if "\n" in clean else ""
        if clean.rstrip().endswith("```"):
            clean = clean.rstrip()[:-3]
    return clean.strip()


class QwenClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        enabled: bool | None = None,
        scaffold_phase_complete: bool | None = None,
        max_retries: int | None = None,
        retry_backoff_ms: int | None = None,
        post: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.api_key = settings.QWEN_API_KEY if api_key is None else api_key
        self.base_url = settings.QWEN_BASE_URL if base_url is None else base_url
        self.model = settings.QWEN_MODEL if model is None else model
        self.timeout_seconds = (
            settings.QWEN_TIMEOUT_SECONDS
            if timeout_seconds is None
            else timeout_seconds
        )
        self.enabled = settings.QWEN_ENABLED if enabled is None else enabled
        self.scaffold_phase_complete = (
            settings.SCAFFOLD_PHASE_COMPLETE
            if scaffold_phase_complete is None
            else scaffold_phase_complete
        )
        self.max_retries = max(
            0,
            settings.QWEN_MAX_RETRIES if max_retries is None else max_retries,
        )
        self.retry_backoff_ms = max(
            0,
            settings.QWEN_RETRY_BACKOFF_MS
            if retry_backoff_ms is None
            else retry_backoff_ms,
        )
        self._post = post or httpx.post
        self._sleep = sleep or time.sleep

    def _validate_configuration(self) -> None:
        if not self.scaffold_phase_complete:
            raise QwenClientError(
                "Live Qwen generation is blocked until the scaffold phase is explicitly completed.",
                reason_code="scaffold_phase_active",
            )
        if not self.enabled:
            raise QwenClientError(
                "Qwen generation is disabled.",
                reason_code="qwen_disabled",
            )
        if not self.api_key:
            raise QwenClientError(
                "Qwen API key is missing.",
                reason_code="qwen_api_key_missing",
            )
        if not self.base_url:
            raise QwenClientError(
                "Qwen base URL is missing.",
                reason_code="qwen_base_url_missing",
            )

    def generate_structured(
        self,
        messages: list[Mapping[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1600,
    ) -> QwenStructuredResult:
        self._validate_configuration()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: QwenClientError | None = None
        total_attempts = self.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                response = self._post(
                    _chat_completion_url(self.base_url),
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                result_payload = self._parse_structured_response(response)
                return QwenStructuredResult(
                    payload=result_payload,
                    model=self.model,
                    attempt_count=attempt,
                )
            except httpx.TimeoutException:
                last_error = QwenClientError(
                    f"Qwen request timed out after {self.timeout_seconds} seconds.",
                    reason_code="qwen_timeout",
                    attempt_count=attempt,
                )
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                last_error = QwenClientError(
                    f"Qwen request failed with HTTP {status_code}.",
                    reason_code=f"qwen_http_{status_code}",
                    attempt_count=attempt,
                )
                if status_code not in RETRYABLE_STATUS_CODES:
                    raise last_error from exc
            except httpx.RequestError:
                last_error = QwenClientError(
                    "Qwen request failed before a response was received.",
                    reason_code="qwen_request_error",
                    attempt_count=attempt,
                )
            except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
                last_error = QwenClientError(
                    "Qwen response was not valid structured JSON.",
                    reason_code="qwen_invalid_structured_output",
                    attempt_count=attempt,
                )

            if attempt < total_attempts:
                self._sleep((self.retry_backoff_ms / 1000) * (2 ** (attempt - 1)))

        if last_error is not None:
            raise last_error
        raise QwenClientError(
            "Qwen generation failed.",
            reason_code="qwen_unknown_error",
            attempt_count=total_attempts,
        )

    @staticmethod
    def _parse_structured_response(response: Any) -> dict[str, Any]:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, Mapping):
            parsed = dict(content)
        elif isinstance(content, str):
            parsed = json.loads(_strip_json_fence(content))
        else:
            raise TypeError("Unsupported Qwen message content")
        generated_text = parsed.get("generated_text")
        if not isinstance(generated_text, str) or not generated_text.strip():
            raise ValueError("Structured response generated_text is empty")
        return {
            "generated_text": generated_text.strip(),
            "summary": _string_list(parsed.get("summary")),
            "style_notes": _string_list(parsed.get("style_notes")),
            "warnings": _string_list(parsed.get("warnings")),
        }

    def generate_chat_completion(
        self,
        messages: list[Mapping[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1600,
    ) -> str:
        return self.generate_structured(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ).payload["generated_text"]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
