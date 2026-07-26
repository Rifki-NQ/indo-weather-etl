import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import logging
from httpx import HTTPError, HTTPStatusError
from typing import Any
from tests.mock_data.mock_forecast_data import (
    MOCKED_FORECAST_DATA,
    MOCKED_FORECAST_WITH_ONE_MALFORED_DATA,
    MOCKED_FORECAST_WITH_ALL_MALFORED_DATA,
)
from src.core.etl.extract import ExtractForecast
from src.core.models.raw_model import RawForecast
from src.core.exceptions import (
    MaxRetryAttemptError,
    InvalidAdm4CodeError,
    EmptyForecastDataError,
    AllForecastDataMalformedError,
)

RATE_LIMITED_BACKOFF = ExtractForecast.RATE_LIMITED_BACKOFF


@pytest.fixture
def extractor() -> ExtractForecast:
    return ExtractForecast(MagicMock())


async def test_retry_then_fail(extractor: ExtractForecast) -> None:
    with (
        patch("asyncio.sleep"),
        patch.object(extractor, "_request", side_effect=HTTPError("error")) as mock_req,
    ):
        with pytest.raises(MaxRetryAttemptError):
            await extractor.get_forecast("")
        assert mock_req.call_count == extractor.RETRY_MAX_ATTEMPT


async def test_retry_then_succeed(extractor: ExtractForecast) -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = MOCKED_FORECAST_DATA
    with (
        patch("asyncio.sleep"),
        patch.object(
            extractor,
            "_request",
            side_effect=[
                HTTPError("error"),
                mock_response,
            ],
        ) as mock_req,
    ):
        await extractor.get_forecast("")
        assert mock_req.call_count == 2


async def test_invalid_adm4_code(extractor: ExtractForecast) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch.object(
        extractor.client, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        with pytest.raises(InvalidAdm4CodeError):
            await extractor._request("")  # pyright: ignore[reportPrivateUsage]


async def test_convert_all_forecast_with_all_data_valid(
    extractor: ExtractForecast,
) -> None:
    all_data = extractor._convert_all_forecast(  # pyright: ignore[reportPrivateUsage]
        MOCKED_FORECAST_DATA["data"][0]["cuaca"], ""
    )
    total_data = 0
    async for data in all_data:
        assert isinstance(data, RawForecast)
        total_data += 1
    assert total_data == 18


async def test_convert_all_forecast_with_one_malformed_data(
    caplog: pytest.LogCaptureFixture,
    extractor: ExtractForecast,
) -> None:
    caplog.set_level(logging.WARNING)
    all_data = extractor._convert_all_forecast(  # pyright: ignore[reportPrivateUsage]
        MOCKED_FORECAST_WITH_ONE_MALFORED_DATA["data"][0]["cuaca"], ""
    )
    total_data = 0
    async for data in all_data:
        assert isinstance(data, RawForecast)
        total_data += 1
    assert total_data == 17
    assert "malformed forecast" in caplog.records[0].getMessage()


async def test_convert_all_forecast_with_all_malformed_data(
    extractor: ExtractForecast,
) -> None:
    all_data = extractor._convert_all_forecast(  # pyright: ignore[reportPrivateUsage]
        MOCKED_FORECAST_WITH_ALL_MALFORED_DATA["data"][0]["cuaca"], ""
    )
    with pytest.raises(AllForecastDataMalformedError) as exc_info:
        async for _ in all_data:
            pass
    assert exc_info.value.total_malformed == 18


@pytest.mark.parametrize(
    "forecast_data",
    [
        [],
        [[]],
    ],
)
async def test_convert_all_forecast_with_empty_forecast_data(
    forecast_data: list[list[Any]], extractor: ExtractForecast
) -> None:
    with pytest.raises(EmptyForecastDataError):
        async for _ in extractor._convert_all_forecast(forecast_data, ""):  # pyright: ignore[reportPrivateUsage]
            pass


# helper function
async def setup_rate_limited_test(
    retry_after_value: int | str | None,
    caplog: pytest.LogCaptureFixture,
    extractor: ExtractForecast,
) -> list[str]:
    """
    Patch extractor._request to raise an HTTPStatusError (429, with the given
    Retry-After header) on the first call, then succeed on the second call,
    and drive extractor._request_with_retry through that retry.

    Args:
        retry_after_value: value to set for the mocked response's Retry-After header.
        caplog: pytest fixture for capturing log output.
        extractor: the ExtractForecast instance under test.

    Returns:
        Captured WARNING-level log messages emitted during the retry.
    """
    caplog.set_level(logging.WARNING)
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": retry_after_value}
    status_error_429 = HTTPStatusError(
        "Too many request", request=MagicMock(), response=mock_response
    )
    with (
        patch("asyncio.sleep"),
        patch.object(
            extractor,
            "_request",
            new_callable=AsyncMock,
            side_effect=[status_error_429, None],
        ),
    ):
        await extractor._request_with_retry("", 5, 5)  # pyright: ignore[reportPrivateUsage]
    return caplog.messages


async def test_rate_limited_retry_after_return_int(
    caplog: pytest.LogCaptureFixture, extractor: ExtractForecast
) -> None:
    """Test when raised exc.response.header['Retry-After'] returns an int value."""
    retry_after_value = 10
    logs = await setup_rate_limited_test(retry_after_value, caplog, extractor)
    assert f"retry after {retry_after_value}" in logs[1]


async def test_rate_limited_retry_after_return_convertible_str(
    caplog: pytest.LogCaptureFixture, extractor: ExtractForecast
) -> None:
    """Test when raised exc.response.header['Retry-After'] returns a convertible str value."""
    retry_after_value = "10"
    logs = await setup_rate_limited_test(retry_after_value, caplog, extractor)
    assert f"retry after {retry_after_value}" in logs[1]


async def test_rate_limited_retry_after_return_non_convertible_str(
    caplog: pytest.LogCaptureFixture, extractor: ExtractForecast
) -> None:
    """Test when raised exc.response.header['Retry-After'] return a non-convertible str value,
    it then should use the default value: ExtractForecast.RATE_LIMITED_BACKOFF."""
    retry_after_value = "non convertible"
    logs = await setup_rate_limited_test(retry_after_value, caplog, extractor)
    assert f"retry after {RATE_LIMITED_BACKOFF}" in logs[1]


async def test_rate_limited_retry_after_is_absent(
    caplog: pytest.LogCaptureFixture, extractor: ExtractForecast
) -> None:
    """Test when raised exc.response.header['Retry-After'] is absent, which means it returns None,
    it then should use the default value: ExtractForecast.RATE_LIMITED_BACKOFF."""
    retry_after_value = None
    logs = await setup_rate_limited_test(retry_after_value, caplog, extractor)
    assert f"retry after {RATE_LIMITED_BACKOFF}" in logs[1]


async def test_rate_limited_retry_after_return_minus_int(
    caplog: pytest.LogCaptureFixture, extractor: ExtractForecast
) -> None:
    """Test when raised exc.response.header['Retry-After'] returns a minus int value,
    it then should returns the value as 0."""
    retry_after_value = -10
    logs = await setup_rate_limited_test(retry_after_value, caplog, extractor)
    assert "retry after 0" in logs[1]
