from dataclasses import dataclass
from datetime import datetime


@dataclass
class LocationModel:
    adm: int  # adm4 code dumped into one unified digits
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


@dataclass
class ForecastModel:
    forecast_datetime: datetime  # datetime for the weather forecast
    analysis_datetime: datetime  # datetime for the forecast analysis
    adm4_code: str  # district level four code, the forecast location
    temperature: int  # temprature in celcius
    total_cloud_coverage: int  # percentage
    weather: int  # consider making this enum or point to other table
    weather_description: str
    weather_description_eng: str
    wind_direction_degree: int
    wind_direction_compass: str  # direction from
    wind_direction_compass_to: str  # direction to
    wind_speed: float  # km/h unit
    humidity: int  # percentage
    visibility: int  # meters unit
