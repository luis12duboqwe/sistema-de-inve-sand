"""Cliente compartido para interactuar con la API de OpenAI."""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.config_production import prod_settings


class OpenAIService:
    """Encapsula la inicializacion y uso del cliente oficial de OpenAI."""

    def __init__(self) -> None:
        self._client: Optional[OpenAI] = None

    def _build_client(self) -> OpenAI:
        if not prod_settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY no esta configurada")
        return OpenAI(api_key=prod_settings.OPENAI_API_KEY)

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def create_chat_completion(
        self,
        *,
        messages: Sequence[ChatCompletionMessageParam],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=model or prod_settings.OPENAI_MODEL,
                messages=messages,
                temperature=temperature if temperature is not None else prod_settings.OPENAI_TEMPERATURE,
            )
            return {
                "reply": response.choices[0].message.content if response.choices else "",
                "model": response.model,
                "usage": {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                },
            }
        except (APIError, APITimeoutError, APIConnectionError) as exc:
            raise RuntimeError(f"Error al comunicarse con OpenAI: {exc}") from exc
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"OpenAI produjo un error inesperado: {exc}") from exc


def get_openai_service() -> OpenAIService:
    return openai_service


openai_service = OpenAIService()
