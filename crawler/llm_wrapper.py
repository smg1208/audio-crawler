"""Simple wrapper for LLM-based improvements.

This module provides a tiny wrapper over OpenAI ChatCompletions (if available),
and falls back to a no-op local cleaner when an API key or library is not present.

It is intentionally small — for production you may wish to add retries,
timeouts and request/response logging.
"""
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

try:
    import openai
    _HAS_OPENAI = True
except Exception:
    openai = None  # type: ignore
    _HAS_OPENAI = False


class LLMClient:
    def __init__(self, model: str = 'gpt-3.5-turbo', api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if _HAS_OPENAI and self.api_key:
            openai.api_key = self.api_key

    def available(self) -> bool:
        return _HAS_OPENAI and bool(self.api_key)

    def improve_text(self, text: str, system_prompt: Optional[str] = None) -> str:
        """Return improved text using the LLM if available, otherwise return text.

        The caller should ensure placeholder tokens are present and instruct the model to not change them.
        """
        if not self.available():
            logger.debug('LLM not available; returning text unchanged')
            # Basic local improvement fallback: normalize whitespace and punctuation
            return ' '.join(text.split())

        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': text})

        resp = openai.ChatCompletion.create(model=self.model, messages=messages, temperature=0.0)
        # get assistant content
        choice = resp.get('choices', [{}])[0]
        content = choice.get('message', {}).get('content') or choice.get('text') or ''
        return content.strip()
