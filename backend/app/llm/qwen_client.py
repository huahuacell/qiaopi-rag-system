from __future__ import annotations

from typing import Any, Mapping

import httpx

from app import settings


class QwenClientError(RuntimeError):
    """Controlled error for Qwen configuration and request failures."""


def _chat_completion_url(base_url: str) -> str:
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/chat/completions"):
        return clean_url
    return f"{clean_url}/chat/completions"


class QwenClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.api_key = settings.QWEN_API_KEY if api_key is None else api_key
        self.base_url = settings.QWEN_BASE_URL if base_url is None else base_url
        self.model = settings.QWEN_MODEL if model is None else model
        self.timeout_seconds = settings.QWEN_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        self.enabled = settings.QWEN_ENABLED if enabled is None else enabled

    def _validate_configuration(self) -> None:
        if not self.enabled:
            raise QwenClientError(
                "Qwen generation is disabled. Set QWEN_ENABLED=true and provide QWEN_API_KEY to enable live generation."
            )
        if not self.api_key:
            raise QwenClientError(
                "Qwen API key is missing. Set QWEN_API_KEY before live generation."
            )
        if not self.base_url:
            raise QwenClientError(
                "Qwen base URL is missing. Set QWEN_BASE_URL to an OpenAI-compatible chat completion endpoint base."
            )

    def generate_chat_completion(
        self,
        messages: list[Mapping[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        self._validate_configuration()

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                _chat_completion_url(self.base_url),
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise QwenClientError(
                f"Qwen request timed out after {self.timeout_seconds} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise QwenClientError(
                f"Qwen request failed with HTTP {status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise QwenClientError("Qwen request failed before a response was received.") from exc

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise QwenClientError("Qwen response did not contain a chat completion message.") from exc

        if not isinstance(content, str) or not content.strip():
            raise QwenClientError("Qwen response message was empty.")
        return content.strip()
