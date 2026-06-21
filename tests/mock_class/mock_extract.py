import asyncio
from collections.abc import AsyncIterable
from tests.mock_data.mock_forecast_data import (
    MOCKED_FORECAST_LOCATION_DATA,
    MOCKED_FLATTENED_FORECAST_DATA,
)
from src.core.models.raw_model import RawLocation, RawForecast


class MockExtractForecast:
    async def get_forecast(
        self, adm4_code: str
    ) -> tuple[RawLocation, AsyncIterable[RawForecast]]:
        return RawLocation(**MOCKED_FORECAST_LOCATION_DATA), self._yield_forecast()

    async def _yield_forecast(self) -> AsyncIterable[RawForecast]:
        for data in MOCKED_FLATTENED_FORECAST_DATA:
            yield RawForecast(**data)
            await asyncio.sleep(0)
