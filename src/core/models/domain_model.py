from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class LocationModel:
    adm1: int
    adm2: int
    adm3: int
    adm4: int
    adm4_code: str  # native adm4 code
    provinsi: str
    kotkab: str
    kecamatan: str
    desa: str
    lon: float
    lat: float
    timezone: str

    def as_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


@dataclass
class ForecastModel:
    forecast_datetime: datetime  # datetime for the weather forecast
    analysis_datetime: datetime  # datetime for the forecast analysis
    adm4_code: str  # district level four code, the forecast location
    temperature: int  # temperature in celcius
    total_cloud_coverage: int | None # percentage unit
    total_precipitation: float | None  # mm unit
    weather_description: str | None
    weather_description_eng: str | None
    wind_direction_degree: int | None
    wind_direction_compass: str | None  # direction from
    wind_direction_compass_to: str | None  # direction to
    wind_speed: float | None  # km/h unit
    humidity: int | None  # percentage
    visibility: int | None # meters unit
    updated_at: datetime  # datetime for the forecast last update
    created_at: datetime  # datetime for the forecast creation

    def as_dict(self) -> dict[str, str | int | float | datetime]:
        return asdict(self)
