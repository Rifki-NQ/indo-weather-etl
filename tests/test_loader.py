import pytest
import pytest_asyncio
import logging
from dotenv import load_dotenv
from unittest.mock import patch
from datetime import datetime
from typing import Any
from collections.abc import Sequence, AsyncGenerator
from sqlalchemy import Connection, Row, MetaData, select, inspect
from sqlalchemy.ext.asyncio import AsyncConnection
from tests.mock_class.mock_extract import (
    MockExtractForecast,
    MockExtractForecastBA,
    MockExtractForecastAB,
)
from src.main import get_env
from src.core.transform import TransformForecast
from src.core.load import LoadForecast
from src.core.exceptions import DBNotInitializedError


pytestmark = pytest.mark.integration

# make TransformForecast._current_datetime patched with hardcoded datetime value
# because original implementation uses datetime.now()
MOCK_FIRST_RUN_CURRENT_DATETIME = datetime(2025, 12, 30, 12, 30, 30)
MOCK_SECOND_RUN_CURRENT_DATETIME = datetime(2025, 12, 30, 12, 30, 40)

load_dotenv()
test_db_url = get_env("TEST_DATABASE_URL")


async def make_loader(
    transformer: TransformForecast,
) -> LoadForecast:

    loader = LoadForecast(transformer)
    await loader.setup_db(test_db_url)
    return loader


async def drop_all_tables(conn: AsyncConnection) -> None:
    metadata = MetaData()
    await conn.run_sync(metadata.reflect)
    await conn.run_sync(metadata.drop_all)


@pytest_asyncio.fixture
async def loader() -> AsyncGenerator[LoadForecast, None]:
    transformer = TransformForecast(MockExtractForecast())
    with patch.object(
        transformer, "_current_datetime", new=MOCK_FIRST_RUN_CURRENT_DATETIME
    ):
        loader = await make_loader(transformer)
        yield loader
        db = loader._get_db()  # pyright: ignore[reportPrivateUsage]
        async with db.engine.begin() as conn:
            await drop_all_tables(conn)
        await db.engine.dispose()


@pytest_asyncio.fixture
async def loader_with_different_forecast_location() -> AsyncGenerator[
    LoadForecast, None
]:
    transformer = TransformForecast(MockExtractForecastBA())
    with patch.object(
        transformer, "_current_datetime", new=MOCK_FIRST_RUN_CURRENT_DATETIME
    ):
        loader = await make_loader(transformer)
        yield loader
        db = loader._get_db()  # pyright: ignore[reportPrivateUsage]
        async with db.engine.begin() as conn:
            await drop_all_tables(conn)
        await db.engine.dispose()


@pytest_asyncio.fixture
async def loader_with_different_weather_forecast() -> AsyncGenerator[
    LoadForecast, None
]:
    transformer = TransformForecast(MockExtractForecastAB())
    with patch.object(
        transformer, "_current_datetime", new=MOCK_SECOND_RUN_CURRENT_DATETIME
    ):
        loader = await make_loader(transformer)
        yield loader
        db = loader._get_db()  # pyright: ignore[reportPrivateUsage]
        async with db.engine.begin() as conn:
            await drop_all_tables(conn)
        await db.engine.dispose()


async def read_location_table_rows(loader_obj: LoadForecast) -> Sequence[Row[Any]]:
    db = loader_obj._get_db()  # pyright: ignore[reportPrivateUsage]
    stmt = select(db.location_table)
    async with db.engine.begin() as conn:
        result = await conn.execute(stmt)
        return result.fetchall()


async def read_forecast_table_rows(loader_obj: LoadForecast) -> Sequence[Row[Any]]:
    db = loader_obj._get_db()  # pyright: ignore[reportPrivateUsage]
    stmt = select(db.forecast_table).order_by(db.forecast_table.c.forecast_datetime)
    async with db.engine.begin() as conn:
        result = await conn.execute(stmt)
        return result.fetchall()


async def test_load_transformed_forecast_without_setup_db_first() -> None:
    transformer = TransformForecast(MockExtractForecast())
    loader = LoadForecast(transformer)
    with pytest.raises(DBNotInitializedError):
        await loader.load_transformed_forecast("")


async def test_tables_exists(loader: LoadForecast) -> None:
    db = loader._get_db()  # pyright: ignore[reportPrivateUsage]
    async with db.engine.begin() as conn:

        def _inspect(sync_conn: Connection) -> list[str]:
            inspector = inspect(sync_conn)
            return inspector.get_table_names()

        tables_name = await conn.run_sync(_inspect)
        assert db.location_table.name in tables_name
        assert db.forecast_table.name in tables_name


async def test_tables_row_length(loader: LoadForecast) -> None:
    await loader.load_transformed_forecast("")
    location_table_rows = await read_location_table_rows(loader)
    forecast_table_rows = await read_forecast_table_rows(loader)
    assert len(location_table_rows) == 1
    assert len(forecast_table_rows) == 8


async def test_location_table_first_values(loader: LoadForecast) -> None:
    await loader.load_transformed_forecast("")
    rows = await read_location_table_rows(loader)
    first_row = rows[0]
    assert first_row.adm4_code == "32.16.20.2003"
    assert first_row.adm1 == 32
    assert first_row.adm2 == 16
    assert first_row.adm3 == 20
    assert first_row.adm4 == 2003
    assert first_row.provinsi == "Jawa Barat"
    assert first_row.kotkab == "Bekasi"
    assert first_row.kecamatan == "Cikarang Pusat"
    assert first_row.desa == "Pasiranji"
    assert first_row.lon == 107.2025067024
    assert first_row.lat == -6.374008913
    assert first_row.timezone == "+0700"


async def test_forecast_table_first_values(loader: LoadForecast) -> None:
    await loader.load_transformed_forecast("")
    rows = await read_forecast_table_rows(loader)
    first_row = rows[0]
    assert first_row.forecast_datetime == datetime(2026, 6, 17, 2, 0, 0)
    assert first_row.analysis_datetime == datetime(2026, 6, 16, 12, 0, 0)
    assert first_row.temperature == 25
    assert first_row.total_cloud_coverage == 98
    assert first_row.total_precipitation == 0
    assert first_row.weather_description == "Berawan"
    assert first_row.weather_description_eng == "Mostly Cloudy"
    assert first_row.wind_direction_degree == 138
    assert first_row.wind_direction_compass == "SE"
    assert first_row.wind_direction_compass_to == "NW"
    assert first_row.wind_speed == 4.7
    assert first_row.humidity == 91
    assert first_row.visibility == 7360
    assert first_row.updated_at == MOCK_FIRST_RUN_CURRENT_DATETIME
    assert first_row.created_at == MOCK_FIRST_RUN_CURRENT_DATETIME


async def test_load_with_existed_forecast_location_data(
    loader: LoadForecast, loader_with_different_forecast_location: LoadForecast
) -> None:
    """
    location_table should ignore row with existing primary_key on the same db.

    loader_with_different_forecast_location uses MockExtractForecastBA which
    shares the same location PK as MockExtractForecast but has different
    mocked 'provinsi' data.
    """

    await loader.load_transformed_forecast("")
    first_run_rows = await read_location_table_rows(loader)
    first_run_first_row = first_run_rows[0]

    await loader_with_different_forecast_location.load_transformed_forecast("")
    second_run_rows = await read_location_table_rows(
        loader_with_different_forecast_location
    )
    second_run_first_row = second_run_rows[0]

    assert first_run_first_row == second_run_first_row


async def test_load_with_existed_weather_forecast_data(
    caplog: pytest.LogCaptureFixture,
    loader: LoadForecast,
    loader_with_different_weather_forecast: LoadForecast,
) -> None:
    """
    Weather_forecast should update row with existing primary_key on the same db.
    *except the PKs themselves and the 'created_at' column.

    loader_with_different_weather_forecast uses MockExtractForecastDataAB which
    shares the same composite PK as MockExtractForecast but has different
    'weather_desc' and 'weather_desc_en' mocked data.

    Logger should logs first run as insert, and second run as update.
    """
    caplog.set_level(logging.DEBUG)

    await loader.load_transformed_forecast("")
    first_run_rows = await read_forecast_table_rows(loader)
    first_run_first_row = first_run_rows[0]
    assert first_run_first_row.weather_description == "Berawan"
    assert first_run_first_row.weather_description_eng == "Mostly Cloudy"
    assert "insert forecast" in caplog.records[1].getMessage()

    caplog.clear()

    await loader_with_different_weather_forecast.load_transformed_forecast("")
    second_run_rows = await read_forecast_table_rows(
        loader_with_different_weather_forecast
    )
    second_run_first_row = second_run_rows[0]
    assert second_run_first_row.weather_description == "Berawan b version"
    assert second_run_first_row.weather_description_eng == "Mostly Cloudy b version"
    assert "update forecast" in caplog.records[1].getMessage()

    assert first_run_first_row != second_run_first_row


async def test_created_at_field_on_existed_weather_forecast_data(
    loader: LoadForecast,
    loader_with_different_weather_forecast: LoadForecast,
) -> None:
    """
    Created_at column should only change if the row has not existed yet in the db.
    which means it was inserted, not updated.
    """
    await loader.load_transformed_forecast("")
    first_run_rows = await read_forecast_table_rows(loader)
    first_run_first_row = first_run_rows[0]
    assert first_run_first_row.created_at == MOCK_FIRST_RUN_CURRENT_DATETIME

    await loader_with_different_weather_forecast.load_transformed_forecast("")
    second_run_rows = await read_forecast_table_rows(
        loader_with_different_weather_forecast
    )
    second_run_first_row = second_run_rows[0]
    assert second_run_first_row.created_at == MOCK_FIRST_RUN_CURRENT_DATETIME
