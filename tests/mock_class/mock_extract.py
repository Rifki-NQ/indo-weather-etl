import asyncio
from collections.abc import AsyncIterable
from tests.mock_data.mock_flattened_data import (
    MOCKED_FORECAST_LOCATION_DATA_A,
    MOCKED_WEATHER_FORECAST_DATA_A,
)
from src.core.models.raw_model import RawLocation, RawForecast


class MockExtractForecast:
    async def get_forecast(
        self, adm4_code: str
    ) -> tuple[RawLocation, AsyncIterable[RawForecast]]:
        return RawLocation(**MOCKED_FORECAST_LOCATION_DATA_A), self._yield_forecast()

    async def _yield_forecast(self) -> AsyncIterable[RawForecast]:
        for data in MOCKED_WEATHER_FORECAST_DATA_A:
            yield RawForecast(**data)
            await asyncio.sleep(0)
