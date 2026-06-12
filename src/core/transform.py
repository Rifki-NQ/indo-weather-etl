import asyncio
import logging
from collections.abc import AsyncIterable
from src.core.models.raw_model import RawLocation, RawForecast
from src.core.models.domain_model import ForecastModel
from src.core.models.protocols import ExtractProtocol

logger = logging.getLogger(__name__)


class TransformForecast:
    def __init__(self, extractor: ExtractProtocol, adm4_code: str) -> None:
        self.extractor = extractor
        self.adm4_code = adm4_code

    async def get_transformed_forecast(
        self,
    ) -> tuple[RawLocation, AsyncIterable[ForecastModel]]:
        raw_location, raw_forecast = await self.extractor.get_forecast(self.adm4_code)
        return raw_location, self._transform_all_forecast(raw_forecast)

    async def _transform_all_forecast(
        self, raw_forecast: AsyncIterable[RawForecast]
    ) -> AsyncIterable[ForecastModel]:
        async for single_raw_forecast in raw_forecast:
            logger.info(
                f"Transforming: forecast date {single_raw_forecast.local_datetime}"
            )
            yield self._transform_single_forecast(single_raw_forecast)
            await asyncio.sleep(0)

    def _transform_single_forecast(
        self, single_raw_forecast: RawForecast
    ) -> ForecastModel:
        return ForecastModel(
            forecast_datetime=single_raw_forecast.local_datetime,
            analysis_datetime=single_raw_forecast.analysis_date,
            adm4_code=self.adm4_code,
            temperature=single_raw_forecast.t,
            total_cloud_coverage=single_raw_forecast.tcc,
            weather=single_raw_forecast.weather,
            weather_description=single_raw_forecast.weather_desc,
            weather_description_eng=single_raw_forecast.weather_desc_en,
            wind_direction_degree=single_raw_forecast.wd_deg,
            wind_direction_compass=single_raw_forecast.wd,
            wind_direction_compass_to=single_raw_forecast.wd_to,
            wind_speed=single_raw_forecast.ws,
            humidity=single_raw_forecast.hu,
            visibility=single_raw_forecast.vs,
        )
