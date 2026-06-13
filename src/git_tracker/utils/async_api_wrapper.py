import logging
from abc import ABC
from typing import Any, Optional

import httpx

from .ensure_logger import ensure_logger


class AsyncApiWrapper(ABC):
    BASE_URL: str

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        logger: Optional[logging.Logger] = None,
    ):
        self.timeout = timeout
        self.headers: dict
        self._client: Optional[httpx.AsyncClient]
        self.logger = ensure_logger(logger)
        self.api_calls = 0

        # Implementation for child classes:
        # super().__init__(api_key, timeout, logger)
        # self.headers = {"authorization": api_key}

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            headers=self.headers, timeout=self.timeout, base_url=self.BASE_URL
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None
            self.logger.info(f"Total API calls: {self.api_calls}")
            self.api_calls = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self.headers, timeout=self.timeout, base_url=self.BASE_URL
            )
        return self._client

    async def close(self):
        """Explicitly close the client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _api_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Make API request with error handling"""
        client = await self._get_client()
        try:
            response = await client.get(endpoint, params=params)
            self.api_calls += 1
            self.logger.debug(f"Api calls: {self.api_calls}")
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"Request failed: {str(e)}") from e
