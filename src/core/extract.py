import httpx
import asyncio
import logging
from typing import Any
from collections.abc import Callable, Awaitable
from src.core.models.raw_model import RawForecast, RawLocation
from src.core.exceptions import MaxRetryAttemptError

logger = logging.getLogger(__name__)


class ExtractWeather:
    BASE_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4="
    REQUEST_TIMEOUT = 3.0
    REQUEST_DELAY = 1.0
    RETRY_MAX_ATTEMPT = 5
    RETRY_DELAY = 5.0

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_forecast(
        self, regional_code: str
    ) -> tuple[list[RawForecast], RawLocation]:
        main_url = self.BASE_URL + regional_code
        response = await self._request_with_retry(
            self._request, main_url, self.RETRY_MAX_ATTEMPT, self.RETRY_DELAY
        )
        data = response.json()["data"][0]
        raw_forecast = self._unpack_forecast_data(data["cuaca"])
        raw_location = data["lokasi"]
        return [RawForecast(**r) for r in raw_forecast], RawLocation(**raw_location)

    async def _request_with_retry(
        self,
        requester: Callable[[str], Awaitable[httpx.Response]],
        url: str,
        max_attempt: int,
        retry_delay: float,
    ) -> httpx.Response:
        for attempt in range(max_attempt):
            try:
                return await requester(url)
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Extractor: http status error occured, code: {e.response.status_code}"
                )
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    logger.warning(
                        f"Extractor: rate limited, retry after {retry_after} seconds"
                    )
                    if retry_after:
                        await asyncio.sleep(int(retry_after))
            except httpx.HTTPError as e:
                logger.warning(f"Extractor: http error occured: {repr(e)}")
            logger.info(
                f"Extractor: retry attempt: {attempt + 1}, after {retry_delay} seconds"
            )
            await asyncio.sleep(retry_delay)
        logger.error("Extractor: max attempt reached")
        raise MaxRetryAttemptError(max_attempt)

    async def _request(self, url: str) -> httpx.Response:
        response = await self.client.get(url, timeout=self.REQUEST_TIMEOUT)
        response.raise_for_status()
        await asyncio.sleep(self.REQUEST_DELAY)
        return response

    def _unpack_forecast_data(
        self, forecast_data: list[list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        new_list: list[dict[str, Any]] = []
        for inner_list in forecast_data:
            for item in inner_list:
                new_list.append(dict(item))
        return new_list
