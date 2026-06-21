import pytest
from datetime import datetime
from collections.abc import AsyncIterable
from tests.mock_class.mock_extract import MockExtractForecast
from src.core.transform import TransformForecast
from src.core.models.domain_model import LocationModel, ForecastModel


@pytest.fixture
def extractor() -> MockExtractForecast:
    return MockExtractForecast()


@pytest.fixture
def transformer(extractor: MockExtractForecast) -> TransformForecast:
    return TransformForecast(extractor)


@pytest.fixture
async def transformed_forecast(
    transformer: TransformForecast,
) -> tuple[LocationModel, AsyncIterable[ForecastModel]]:
    return await transformer.get_transformed_forecast("")


@pytest.fixture
async def forecast_location(
    transformed_forecast: tuple[LocationModel, AsyncIterable[ForecastModel]],
) -> LocationModel:
    forecast_location, _ = transformed_forecast
    return forecast_location


@pytest.fixture
async def weather_forecast(
    transformed_forecast: tuple[LocationModel, AsyncIterable[ForecastModel]],
) -> AsyncIterable[ForecastModel]:
    _, weather_forecast = transformed_forecast
    return weather_forecast


async def test_transformed_forecast_location_type(
    forecast_location: LocationModel,
) -> None:
    assert isinstance(forecast_location, LocationModel)


async def test_transformed_weather_forecast_type(
    weather_forecast: AsyncIterable[ForecastModel],
) -> None:
    total_data = 0
    async for data in weather_forecast:
        assert isinstance(data, ForecastModel)
        total_data += 1
    assert total_data == 8


async def test_transformed_forecast_location_values(
    forecast_location: LocationModel,
) -> None:
    assert forecast_location.adm1 == 32
    assert forecast_location.adm2 == 16
    assert forecast_location.adm3 == 20
    assert forecast_location.adm4 == 2003
    assert forecast_location.adm4_code == "32.16.20.2003"
    assert forecast_location.provinsi == "Jawa Barat"
    assert forecast_location.kotkab == "Bekasi"
    assert forecast_location.kecamatan == "Cikarang Pusat"
    assert forecast_location.desa == "Pasiranji"
    assert forecast_location.lon == 107.2025067024
    assert forecast_location.lat == -6.374008913
    assert forecast_location.timezone == "+0700"


async def test_transformed_weather_forecast_first_values(
    weather_forecast: AsyncIterable[ForecastModel],
) -> None:
    async for data in weather_forecast:
        assert data.forecast_datetime == datetime(2026, 6, 17, 2, 0, 0)
        assert data.analysis_datetime == datetime(2026, 6, 16, 12, 0, 0)
        assert data.adm4_code == "32.16.20.2003"
        assert data.temperature == 25
        assert data.total_cloud_coverage == 98
        assert data.total_precipitation == 0
        assert data.weather_description == "Berawan"
        assert data.weather_description_eng == "Mostly Cloudy"
        assert data.wind_direction_degree == 138
        assert data.wind_direction_compass == "SE"
        assert data.wind_direction_compass_to == "NW"
        assert data.wind_speed == 4.7
        assert data.humidity == 91
        assert data.visibility == 7360
        break
