"""Real LLM adapters — Ollama and generic OpenAI-compatible HTTP.

Two concrete implementations of the LLMAdapter protocol:

  OllamaLLMAdapter  — talks to a local Ollama instance via /api/generate
  HttpLLMAdapter    — talks to any OpenAI-compatible /v1/chat/completions

Both are opt-in. UMH falls back to NullLLMAdapter when neither is configured
or reachable. No EOS imports. No side effects on import.

Configuration via environment variables:
  UMH_OLLAMA_HOST    — Ollama base URL (default: http://localhost:11434)
  UMH_OLLAMA_MODEL   — model name (default: qwen2.5:0.5b)
  UMH_LLM_URL        — OpenAI-compatible endpoint base URL
  UMH_LLM_MODEL      — model name for HTTP adapter
  UMH_LLM_API_KEY    — API key for HTTP adapter (optional)
  UMH_LLM_TIMEOUT    — request timeout in seconds (default: 30)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class OllamaLLMAdapter:
    """LLM adapter that calls a local Ollama instance."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._host = (
            host or os.environ.get("UMH_OLLAMA_HOST", "http://localhost:11434")
        ).rstrip("/")
        self._model = model or os.environ.get("UMH_OLLAMA_MODEL", "qwen2.5:0.5b")
        self._timeout = timeout or int(os.environ.get("UMH_LLM_TIMEOUT", "30"))
        self._reachable: bool | None = None

    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self._host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=self._timeout)
        data = json.loads(resp.read())
        return data.get("response", "")

    def available(self) -> bool:
        if self._reachable is not None:
            return self._reachable
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            self._reachable = any(self._model in m for m in models)
        except Exception:
            self._reachable = False
        return self._reachable

    @property
    def model(self) -> str:
        return self._model

    @property
    def host(self) -> str:
        return self._host

    def __repr__(self) -> str:
        status = (
            "reachable"
            if self._reachable
            else "unknown"
            if self._reachable is None
            else "unreachable"
        )
        return f"OllamaLLMAdapter(model={self._model!r}, host={self._host!r}, {status})"


class HttpLLMAdapter:
    """LLM adapter for any OpenAI-compatible /v1/chat/completions endpoint."""

    def __init__(
        self,
        url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        base = (url or os.environ.get("UMH_LLM_URL", "")).rstrip("/")
        if not base:
            raise ValueError(
                "HttpLLMAdapter requires a URL (UMH_LLM_URL env or url param)"
            )
        self._url = f"{base}/v1/chat/completions" if "/v1/" not in base else base
        self._model = model or os.environ.get("UMH_LLM_MODEL", "default")
        self._api_key = api_key or os.environ.get("UMH_LLM_API_KEY", "")
        self._timeout = timeout or int(os.environ.get("UMH_LLM_TIMEOUT", "30"))

    def generate(self, prompt: str, system: str = "", **kwargs: Any) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
        }

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            self._url,
            data=body,
            headers=headers,
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=self._timeout)
        data = json.loads(resp.read())
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    def available(self) -> bool:
        return bool(self._url)

    @property
    def model(self) -> str:
        return self._model

    def __repr__(self) -> str:
        return f"HttpLLMAdapter(model={self._model!r}, url={self._url!r})"


def discover_llm_adapter() -> Any:
    """Try to find the best available LLM adapter.

    Discovery order:
      1. OllamaLLMAdapter if Ollama is reachable
      2. HttpLLMAdapter if UMH_LLM_URL is set
      3. None (caller should fall back to NullLLMAdapter)
    """
    ollama = OllamaLLMAdapter()
    if ollama.available():
        return ollama

    llm_url = os.environ.get("UMH_LLM_URL", "")
    if llm_url:
        try:
            return HttpLLMAdapter(url=llm_url)
        except ValueError:
            pass

    return None
