from collections.abc import AsyncIterable
from typing import Protocol

from src.core.models.contexts import DBContext
from src.core.models.domain_model import ForecastModel, LocationModel
from src.core.models.raw_model import RawForecast, RawLocation


class ExtractProtocol(Protocol):
    async def get_forecast(
        self, adm4_code: str
    ) -> tuple[RawLocation, AsyncIterable[RawForecast]]: ...


class TransformProtocol(Protocol):
    async def get_transformed_forecast(
        self, adm4_code: str
    ) -> tuple[LocationModel, AsyncIterable[ForecastModel]]: ...


class LoadProtocol(Protocol):
    async def setup_db(self, db_url: str) -> DBContext: ...
    async def load_transformed_forecast(self, adm4_code: str) -> None: ...
