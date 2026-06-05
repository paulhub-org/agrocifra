"""Клиент Jotform REST API для получения ответов из действующих форм (Спринт 3).

Использует API-ключ соискателя (settings.jotform_api_key) и базовый URL
EU-облака Jotform (settings.jotform_api_base). Сетевые вызовы инкапсулированы;
для тестов можно передать собственный httpx.Client (например, с MockTransport).
"""
from __future__ import annotations

from collections.abc import Iterator

import httpx

from app.core.config import settings


class JotformClient:
    """Тонкая обёртка над Jotform REST API (формы и сабмишены)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.jotform_api_key
        self.base_url = (base_url or settings.jotform_api_base).rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def __enter__(self) -> "JotformClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        params["apiKey"] = self.api_key
        resp = self._client.get(f"{self.base_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_form_questions(self, form_id: str) -> dict:
        """GET /form/{id}/questions — структура вопросов формы (метаданные)."""
        return self._get(f"/form/{form_id}/questions").get("content", {})

    def get_submissions(self, form_id: str, limit: int = 1000, offset: int = 0) -> list[dict]:
        """GET /form/{id}/submissions — список сабмишенов (по странице)."""
        data = self._get(
            f"/form/{form_id}/submissions",
            {"limit": limit, "offset": offset},
        )
        return data.get("content", [])

    def iter_submissions(self, form_id: str, page_size: int = 100) -> Iterator[dict]:
        """Итерироваться по всем сабмишенам формы с постраничной выборкой."""
        offset = 0
        while True:
            page = self.get_submissions(form_id, limit=page_size, offset=offset)
            if not page:
                return
            yield from page
            if len(page) < page_size:
                return
            offset += page_size
