import asyncio
import logging
from collections.abc import AsyncIterable
from typing import Any

import httpx
from pydantic import ValidationError

from src.core.exceptions import (
    AllForecastDataMalformedError,
    EmptyForecastDataError,
    InvalidAdm4CodeError,
    MaxRetryAttemptError,
)
from src.core.models.raw_model import RawForecast, RawLocation

logger = logging.getLogger(__name__)


class ExtractForecast:
    BASE_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4="
    REQUEST_TIMEOUT = 3.0
    RETRY_MAX_ATTEMPT = 5
    RETRY_DELAY = 5.0
    RATE_LIMITED_BACKOFF = 60

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_forecast(
        self, adm4_code: str
    ) -> tuple[RawLocation, AsyncIterable[RawForecast]]:
        logger.info(f"Extractor: extracting weather forecast on {adm4_code}")
        response = await self._request_with_retry(
            adm4_code, self.RETRY_MAX_ATTEMPT, self.RETRY_DELAY
        )
        data = response.json()["data"][0]
        raw_location = RawLocation(**data["lokasi"])
        raw_forecast = self._convert_all_forecast(data["cuaca"], adm4_code)
        return raw_location, raw_forecast

    async def _request_with_retry(
        self,
        adm4_code: str,
        max_attempt: int,
        retry_delay: float,
    ) -> httpx.Response:
        for attempt in range(max_attempt):
            try:
                return await self._request(adm4_code)
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Extractor: http status error occured, code: {e.response.status_code}"
                )
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    backoff_value = self._parse_retry_after(retry_after)
                    logger.warning(
                        f"Extractor: rate limited, retry after {backoff_value} seconds"
                    )
                    await asyncio.sleep(backoff_value)
                    continue
            except httpx.HTTPError as e:
                logger.warning(f"Extractor: http error occured: {e!r}")
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
        return response

    def _convert_all_forecast(
        self,
        forecast_data: list[list[dict[str, Any]]],
        adm4_code: str,
    ) -> AsyncIterable[RawForecast]:
        """
        Return AsyncIterable[RawForecast] if there is at least one forecast data,
        raise error if there is no.
        """
        if not any(forecast_data):
            raise EmptyForecastDataError("Empty forecast data from the API")

        async def _convert() -> AsyncIterable[RawForecast]:
            """
            Convert each single forecast to RawForecast then yield it,
            while giving the event loop control with: await asyncio.sleep(0),
            skip yield on malformed forecast -> raise error if yielded_data is 0.
            """
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

        return _convert()

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

    def _parse_retry_after(self, retry_after: str | int | None) -> int:
        """
        Return default value of backoff - RATE_LIMITED_BACKOFF if the retry_after value
        is None or non-convertible string, if it's convertible string, convert the value
        to int then return it, if the value is already an int, return as it is.
        """
        if retry_after is None:
            return self.RATE_LIMITED_BACKOFF
        if isinstance(retry_after, str):
            try:
                value = int(retry_after)
            except ValueError:
                return self.RATE_LIMITED_BACKOFF
        else:
            value = retry_after
        return max(0, value)  # return 0 if the value is minus int
