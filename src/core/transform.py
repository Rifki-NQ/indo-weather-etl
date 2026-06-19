import asyncio
import logging
from collections.abc import AsyncIterable
from src.core.models.raw_model import RawLocation, RawForecast
from src.core.models.domain_model import LocationModel, ForecastModel
from src.core.models.protocols import ExtractProtocol

logger = logging.getLogger(__name__)


class TransformForecast:
    def __init__(self, extractor: ExtractProtocol) -> None:
        self.extractor = extractor

    async def get_transformed_forecast(
        self, adm4_code: str
    ) -> tuple[LocationModel, AsyncIterable[ForecastModel]]:
        raw_location, raw_forecast = await self.extractor.get_forecast(adm4_code)
        return self._transform_forecast_location(
            raw_location
        ), self._transform_all_forecast(raw_location.adm4, raw_forecast)

    async def _transform_all_forecast(
        self, adm4_code: str, raw_forecast: AsyncIterable[RawForecast]
    ) -> AsyncIterable[ForecastModel]:
        async for single_raw_forecast in raw_forecast:
            logger.info(
                f"Transforming: forecast date {single_raw_forecast.local_datetime}"
            )
            yield self._transform_single_forecast(adm4_code, single_raw_forecast)
            await asyncio.sleep(0)

    def _transform_single_forecast(
        self, adm4_code: str, single_raw_forecast: RawForecast
    ) -> ForecastModel:
        return ForecastModel(
            forecast_datetime=single_raw_forecast.local_datetime,
            analysis_datetime=single_raw_forecast.analysis_date,
            adm4_code=adm4_code,
            temperature=single_raw_forecast.t,
            total_cloud_coverage=single_raw_forecast.tcc,
            total_precipitation=single_raw_forecast.tp,
            weather_description=single_raw_forecast.weather_desc,
            weather_description_eng=single_raw_forecast.weather_desc_en,
            wind_direction_degree=single_raw_forecast.wd_deg,
            wind_direction_compass=single_raw_forecast.wd,
            wind_direction_compass_to=single_raw_forecast.wd_to,
            wind_speed=single_raw_forecast.ws,
            humidity=single_raw_forecast.hu,
            visibility=single_raw_forecast.vs,
        )

    def _transform_forecast_location(self, raw_location: RawLocation) -> LocationModel:
        """
        throw away 'type' field from raw_location,
        'adm4_code' is native adm code used to talk to the api
        """
        adm_codes = [int(adm_code) for adm_code in raw_location.adm4.split(".")]
        return LocationModel(
            adm1=adm_codes[0],
            adm2=adm_codes[1],
            adm3=adm_codes[2],
            adm4=adm_codes[3],
            adm4_code=raw_location.adm4,
            **raw_location.model_dump(
                exclude={"adm1", "adm2", "adm3", "adm4", "adm4_code", "type"}
            ),
        )
