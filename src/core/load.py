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
from src.core.models.contexts import DBContext
from src.core.models.domain_model import LocationModel, ForecastModel
from src.core.models.protocols import TransformProtocol
from src.core.exceptions import DBNotInitializedError

logger = logging.getLogger(__name__)


class LoadForecast:
    def __init__(self, transformer: TransformProtocol) -> None:
        self.transformer = transformer
        self._db: DBContext | None = None

    def setup_db(self, db_url: str) -> None:
        """Must be called before load_transformed_forecast()."""
        engine = create_engine(db_url)
        metadata = MetaData()
        location_table = self._define_forecast_location_table(metadata)
        forecast_table = self._define_forecast_table(metadata)
        metadata.create_all(engine)
        self._db = DBContext(engine, location_table, forecast_table)

    async def load_transformed_forecast(self, adm4_code: str) -> None:
        db = self._get_db()
        (
            forecast_location,
            weather_forecast,
        ) = await self.transformer.get_transformed_forecast(adm4_code)
        with db.engine.connect() as conn:
            self._insert_or_ignore_location(conn, db.location_table, forecast_location)
            async for single_forecast in weather_forecast:
                self._insert_or_update_forecast(
                    conn, db.forecast_table, single_forecast
                )
            conn.commit()
            logger.info(f"Load: forecast for {forecast_location.adm4_code} commited")

    def _get_db(self) -> DBContext:
        """
        methods that need db atttibute need get through here,
        raises error if DBContext has not initiated through setup_db method
        """
        if self._db is None:
            raise DBNotInitializedError("setup_db() has not called yet")
        return self._db

    def _insert_or_ignore_location(
        self, conn: Connection, location_table: Table, location_data: LocationModel
    ) -> None:
        """Ignore the new row if there is a conflict"""
        stmt = insert(location_table).values(**location_data.as_dict())
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

    def _insert_or_update_forecast(
        self, conn: Connection, forecast_table: Table, forecast_data: ForecastModel
    ) -> None:
        """Update existing row except the primary keys if there is a conflict"""
        pk_names = {pk.name for pk in forecast_table.primary_key.columns}
        stmt = insert(forecast_table).values(**forecast_data.as_dict())
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=list(pk_names),
            set_={
                col.name: stmt.excluded[col.name]
                for col in forecast_table.c
                if col.name not in pk_names
            }
        )
        conn.execute(upsert_stmt)
        logger.info(
            f"Load(forecast_table): insert or replace forecast: {forecast_data.forecast_datetime} on {forecast_data.adm4_code}"
        )

    def _define_forecast_location_table(self, metadata: MetaData) -> Table:
        return Table(
            "forecast_location",
            metadata,
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

    def _define_forecast_table(self, metadata: MetaData) -> Table:
        return Table(
            "weather_forecast",
            metadata,
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
