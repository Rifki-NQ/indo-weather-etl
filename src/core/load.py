import logging
from sqlalchemy import (
    create_engine,
    MetaData,
    Connection,
    Table,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.sqlite import insert
from src.core.models.domain_model import LocationModel, ForecastModel
from src.core.models.protocols import TransformProtocol

logger = logging.getLogger(__name__)


class LoadForecast:
    def __init__(self, transformer: TransformProtocol) -> None:
        self.transformer = transformer
        self.engine = create_engine("sqlite:///database/data.db")
        self.metadata = MetaData()
        self._define_forecast_location_table()
        self._define_forecast_table()
        self.metadata.create_all(self.engine)  # create all tables

    async def load_transformed_forecast(self) -> None:
        (
            forecast_location,
            weather_forecast,
        ) = await self.transformer.get_transformed_forecast()
        with self.engine.connect() as conn:
            self._insert_or_ignore_location(conn, forecast_location)
            async for single_forecast in weather_forecast:
                self._insert_or_replace_forecast(conn, single_forecast)
            conn.commit()
            logger.info(f"Load: forecast for {forecast_location.adm4_code} commited")

    def _insert_or_ignore_location(
        self, conn: Connection, location_data: LocationModel
    ) -> None:
        stmt = insert(self.locations_table).values(**location_data.as_dict())
        stmt = stmt.on_conflict_do_nothing()
        result = conn.execute(stmt)
        if result.rowcount == 0:
            logger.info(
                f"Load(location_table): ignore location: adm4_code {location_data.adm4_code}"
            )
            return
        logger.info(
            f"Load(location_table): insert location: adm4_code {location_data.adm4_code}"
        )

    def _insert_or_replace_forecast(
        self, conn: Connection, forecast_data: ForecastModel
    ) -> None:
        stmt = (
            insert(self.forecast_table)
            .prefix_with("OR REPLACE")
            .values(**forecast_data.as_dict())
        )
        conn.execute(stmt)
        logger.info(
            f"Load(forecast_table): insert or replace forecast: {forecast_data.forecast_datetime} on {forecast_data.adm4_code}"
        )

    def _define_forecast_location_table(self) -> None:
        self.locations_table = Table(
            "forecast_location",
            self.metadata,
            Column("adm4_code", String(), primary_key=True),
            Column("adm1", Integer()),
            Column("adm2", Integer()),
            Column("adm3", Integer()),
            Column("adm4", Integer()),
            Column("provinsi", String()),
            Column("kotkab", String()),
            Column("kecamatan", String()),
            Column("desa", String()),
            Column("lon", Float()),
            Column("lat", Float()),
            Column("timezone", String()),
        )

    def _define_forecast_table(self) -> None:
        self.forecast_table = Table(
            "weather_forecast",
            self.metadata,
            Column(
                "adm4_code",
                String(),
                ForeignKey("forecast_location.adm4_code"),
                primary_key=True,
            ),
            Column("forecast_datetime", DateTime(), primary_key=True),
            Column("analysis_datetime", DateTime()),
            Column("temperature", Integer()),
            Column("total_cloud_coverage", Integer()),
            Column("total_precipitation", Float()),
            Column("weather_description", String()),
            Column("weather_description_eng", String()),
            Column("wind_direction_degree", Integer()),
            Column("wind_direction_compass", String()),
            Column("wind_direction_compass_to", String()),
            Column("wind_speed", Float()),
            Column("humidity", Integer()),
            Column("visibility", Integer()),
        )
