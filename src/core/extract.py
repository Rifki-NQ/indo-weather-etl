import httpx
import asyncio
import logging
from pydantic import ValidationError
from typing import Any
from collections.abc import Callable, Awaitable, AsyncIterable
from src.core.models.raw_model import RawForecast, RawLocation
from src.core.exceptions import (
    MaxRetryAttemptError,
    InvalidAdm4CodeError,
    EmptyForecastDataError,
    AllForecastDataMalformedError,
)

logger = logging.getLogger(__name__)


class ExtractForecast:
    BASE_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4="
    REQUEST_TIMEOUT = 3.0
    REQUEST_DELAY = 1.0
    RETRY_MAX_ATTEMPT = 5
    RETRY_DELAY = 5.0

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_forecast(
        self, adm4_code: str
    ) -> tuple[RawLocation, AsyncIterable[RawForecast]]:
        logger.info(f"Extractor: extracting weather forecast on {adm4_code}")
        response = await self._request_with_retry(
            self._request, adm4_code, self.RETRY_MAX_ATTEMPT, self.RETRY_DELAY
        )
        data = response.json()["data"][0]
        raw_location = RawLocation(**data["lokasi"])
        raw_forecast = self._convert_all_forecast(data["cuaca"], adm4_code)
        del data
        return raw_location, raw_forecast

    async def _request_with_retry(
        self,
        requester: Callable[[str], Awaitable[httpx.Response]],
        adm4_code: str,
        max_attempt: int,
        retry_delay: float,
    ) -> httpx.Response:
        for attempt in range(max_attempt):
            try:
                return await requester(adm4_code)
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
                        continue
            except httpx.HTTPError as e:
                logger.warning(f"Extractor: http error occured: {repr(e)}")
            logger.info(
                f"Extractor: retry attempt: {attempt + 1}, after {retry_delay} seconds"
            )
            await asyncio.sleep(retry_delay)
        logger.error("Extractor: max attempt reached")
        raise MaxRetryAttemptError(max_attempt)

    async def _request(self, adm4_code: str) -> httpx.Response:
        main_url = self.BASE_URL + adm4_code
        response = await self.client.get(main_url, timeout=self.REQUEST_TIMEOUT)
        if response.status_code == 404:
            raise InvalidAdm4CodeError(adm4_code)
        response.raise_for_status()
        await asyncio.sleep(self.REQUEST_DELAY)
        return response

    async def _convert_all_forecast(
        self,
        forecast_data: list[list[dict[str, Any]]],
        adm4_code: str,
    ) -> AsyncIterable[RawForecast]:
        """
        flatten the two depth nested list into one depth flat list
        then convert to RawForecast for each yield,
        while giving the event loop control with: await asyncio.sleep(0)
        """
        if not any(forecast_data):
            raise EmptyForecastDataError("Empty forecast data from the API")
        yielded_data = 0
        total_malformed = 0
        for inner_list in forecast_data:
            for item in inner_list:
                converted_forecast = self._convert_single_forecast(item)
                if converted_forecast is None:
                    total_malformed += 1
                    continue
                logger.debug(
                    f"Extractor: forecast data for {converted_forecast.local_datetime} on {adm4_code} validated"
                )
                yield converted_forecast
                yielded_data += 1
                await asyncio.sleep(0)
        if yielded_data == 0:
            raise AllForecastDataMalformedError(total_malformed)

    def _convert_single_forecast(
        self, single_forecast_data: dict[str, Any]
    ) -> RawForecast | None:
        """
        validate then convert raw_forecast into pydantic model
        return None if the validation failed
        """
        try:
            return RawForecast(**single_forecast_data)
        except ValidationError as e:
            err = e.errors()
            logger.warning(
                f"Extractor: skipping malformed forecast entry: {err[0]['loc']} {err[0]['msg']}"
            )
            return None
