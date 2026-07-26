import pytest
import pytest_asyncio
from dotenv import load_dotenv
from datetime import date
from collections.abc import AsyncGenerator
from tests.utils import drop_all_tables, read_forecast_table_rows
from tests.mock_class.mock_extract import MockExtractForecastFull
from src.main import get_env
from src.core.etl.transform import TransformForecast
from src.core.etl.load import LoadForecast
from src.core.db_balancer import delete_past_forecasts

pytestmark = pytest.mark.integration

# the dates are based on mocked data: MOCKED_WEATHER_FORECAST_DATA_FULL
MOCK_CURRENT_DATE = date(year=2026, month=7, day=27)  # last date of the mocked data
MOCK_CURRENT_DATE_2 = date(year=2026, month=7, day=25)  # first date of the mocked data

load_dotenv()
test_db_url = get_env("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def loader() -> AsyncGenerator[LoadForecast, None]:
    transformer = TransformForecast(MockExtractForecastFull())
    loader = LoadForecast(transformer)
    await loader.setup_db(test_db_url)
    yield loader
    db = loader._get_db()  # pyright: ignore[reportPrivateUsage]
    async with db.engine.begin() as conn:
        await drop_all_tables(conn)
    await db.engine.dispose()


async def test_delete_rows_before_date_to(loader: LoadForecast) -> None:
    await loader.load_transformed_forecast("")
    deleted_count = await delete_past_forecasts(loader._get_db(), MOCK_CURRENT_DATE)  # pyright: ignore[reportPrivateUsage]
    assert deleted_count == 10
    rows = await read_forecast_table_rows(loader)
    assert len(rows) == 8  # 18 total, 10 deleted
    # assert rows with current_date does not get deleted
    for row in rows:
        assert row.forecast_datetime.date() == MOCK_CURRENT_DATE


async def test_returns_none_when_date_to_is_earliest_date(loader: LoadForecast) -> None:
    await loader.load_transformed_forecast("")
    deleted_count = await delete_past_forecasts(loader._get_db(), MOCK_CURRENT_DATE_2)  # pyright: ignore[reportPrivateUsage]
    assert deleted_count is None
    rows = await read_forecast_table_rows(loader)
    assert len(rows) == 18
