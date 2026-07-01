"""Thin DeepSeek LLM layer for synthesising answers from retrieved report chunks.

DeepSeek exposes an OpenAI-compatible Chat Completions endpoint, so we call it
directly with httpx — no extra SDK required.

The layer is intentionally optional: if ``SIA_DEEPSEEK_API_KEY`` is not set the
function returns ``None`` and the caller falls back to the existing keyword-
retrieval answer unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
_MODEL = "deepseek-chat"
_TIMEOUT = 30  # seconds


def _build_context(chunks: list[tuple[str, str]]) -> str:
    """Format retrieved (source, text) pairs into a numbered context block."""
    lines: list[str] = []
    for i, (source, text) in enumerate(chunks, start=1):
        lines.append(f"[{i}] ({source})\n{text.strip()}")
    return "\n\n".join(lines)


def ask_llm(
    question: str,
    chunks: list[tuple[str, str]],
    fallback_answer: str,
) -> dict[str, Any] | None:
    """Send question + retrieved chunks to DeepSeek and return a structured result.

    Returns a dict with keys ``answer``, ``confidence``, and ``sources``, or
    ``None`` if the API key is missing or the call fails (so the caller can use
    the retrieval-only answer as-is).
    """
    settings = get_settings()
    api_key: str = getattr(settings, "deepseek_api_key", "") or ""
    if not api_key:
        return None

    context = _build_context(chunks)
    sources = [source for source, _ in chunks]

    system_prompt = (
        "You are a financial analyst assistant. "
        "Answer the user's question using ONLY the numbered context excerpts provided. "
        "Be concise, precise, and cite which excerpt numbers support each claim. "
        "If the context does not contain enough information to answer, say so clearly."
    )

    user_prompt = (
        f"Context excerpts extracted from the financial report:\n\n"
        f"{context}\n\n"
        f"Question: {question}\n\n"
        "Answer based strictly on the context above:"
    )

    payload = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 512,
        "temperature": 0.2,
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.post(
                _DEEPSEEK_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            answer_text: str = data["choices"][0]["message"]["content"].strip()

        return {
            "answer": answer_text,
            "confidence": "high",
            "sources": sources,
        }

    except httpx.HTTPStatusError as exc:
        logger.warning("DeepSeek API HTTP error %s: %s", exc.response.status_code, exc.response.text)
        return None
    except Exception as exc:  # network timeout, parse error, etc.
        logger.warning("DeepSeek API call failed: %s", exc)
        return None
