import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, patch
from tests.paths import mock_data_dir
from src.core.runner import ETLRunner
from src.core.utils import yield_csv_value
from src.core.exceptions import InvalidAdm4CodeError


MOCK_ADM4_CODES_PATH = mock_data_dir() / "mock_adm4_codes.csv"


async def mock_loader_delay(adm4_code: str) -> None:
    await asyncio.sleep(0.1)
    return None


@pytest.fixture
def etl_runner() -> ETLRunner:
    mock_loader = AsyncMock()
    mock_loader.load_transformed_forecast.side_effect = mock_loader_delay
    etl_runner = ETLRunner(loader=mock_loader)
    etl_runner.TASK_DELAY = 0  # remove delay between task creation
    return etl_runner


async def test_runner_max_concurrency(etl_runner: ETLRunner) -> None:
    max_concurrent_tasks = etl_runner.MAX_CONCURRENT_TASKS
    await etl_runner.run_batch(yield_csv_value(MOCK_ADM4_CODES_PATH, "Kode"))
    assert etl_runner.peak_active_tasks <= max_concurrent_tasks


async def test_runner_on_invalid_adm4_codes(
    caplog: pytest.LogCaptureFixture, etl_runner: ETLRunner
) -> None:
    caplog.set_level(logging.ERROR)
    with patch.object(
        etl_runner.loader, "load_transformed_forecast", side_effect=InvalidAdm4CodeError("")
    ):
        await etl_runner.run_batch(yield_csv_value(MOCK_ADM4_CODES_PATH, "Kode"))
        for log in caplog.records:
            assert "Invalid adm4_code" in log.getMessage()
    caplog.clear()
