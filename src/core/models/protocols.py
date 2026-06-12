from typing import Protocol
from collections.abc import AsyncIterable
from src.core.models.raw_model import RawLocation, RawForecast
from src.core.models.domain_model import ForecastModel


class ExtractProtocol(Protocol):
    async def get_forecast(
        self, adm4_code: str
    ) -> tuple[RawLocation, AsyncIterable[RawForecast]]: ...


class TransformProtocol(Protocol):
    def get_transformed_forecast(
        self,
    ) -> tuple[RawLocation, AsyncIterable[ForecastModel]]: ...
