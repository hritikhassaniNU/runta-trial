"""OpenAI Responses API client. Model is always set explicitly."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import httpx

RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4.1"


class OpenAIResponses:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        self.model = model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def create(self, **payload: Any) -> Dict[str, Any]:
        payload.setdefault("model", self.model)
        last_error = "OpenAI request failed"
        for attempt in range(4):
            response = httpx.post(
                RESPONSES_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90.0,
            )
            if response.status_code == 429:
                last_error = "OpenAI error 429: rate limited"
                time.sleep(8 * (attempt + 1))
                continue
            if response.status_code >= 400:
                raise RuntimeError(
                    f"OpenAI error {response.status_code}: {response.text[:200]}"
                )
            return response.json()
        raise RuntimeError(last_error)


class ScriptedResponses:
    """Deterministic stand-in for tests. Each create() emits the next function call."""

    def __init__(self, calls):
        self.calls = list(calls)
        self.index = 0

    def create(self, **_payload: Any) -> Dict[str, Any]:
        if self.index >= len(self.calls):
            raise RuntimeError("scripted client has no more calls")
        name, arguments = self.calls[self.index]
        self.index += 1
        call_id = f"call_{self.index}"
        return {
            "id": f"resp_{self.index}",
            "output": [
                {
                    "type": "function_call",
                    "name": name,
                    "arguments": arguments
                    if isinstance(arguments, str)
                    else __import__("json").dumps(arguments),
                    "call_id": call_id,
                }
            ],
        }


def get_client() -> OpenAIResponses:
    return OpenAIResponses()
