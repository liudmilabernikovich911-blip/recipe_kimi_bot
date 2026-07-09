import logging
from typing import List, Union

import httpx
from openai import AsyncOpenAI

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)

logger = logging.getLogger(__name__)


class DeepSeekProvider:
    """Прямое обращение к DeepSeek API через httpx."""

    @staticmethod
    async def fetch(system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


class OpenRouterProvider:
    """OpenRouter через официальный AsyncOpenAI-клиент."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )

    async def fetch(self, system_prompt: str, user_prompt: str) -> str:
        completion = await self.client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        return completion.choices[0].message.content


class RecipeService:
    """
    Пробует DeepSeek → если ошибка/нет ключа → OpenRouter.
    """

    providers: List[Union[DeepSeekProvider, OpenRouterProvider]]

    def __init__(self) -> None:
        self.providers = []
        if DEEPSEEK_API_KEY:
            self.providers.append(DeepSeekProvider())
        if OPENROUTER_API_KEY:
            self.providers.append(OpenRouterProvider())

        if not self.providers:
            raise RuntimeError("Не задан ни DEEPSEEK_API_KEY, ни OPENROUTER_API_KEY")

    async def get_recipes(self, system_prompt: str, user_prompt: str) -> str:
        last_error: Union[Exception, None] = None
        for provider in self.providers:
            provider_name = type(provider).__name__
            try:
                logger.info("Пробуем провайдер: %s", provider_name)
                result = await provider.fetch(system_prompt, user_prompt)
                logger.info("Успех через %s", provider_name)
                return result
            except Exception as exc:
                logger.warning("Ошибка в %s: %s", provider_name, exc)
                last_error = exc

        raise last_error or Exception("Все провайдеры недоступны")