from dataclasses import dataclass
from datetime import datetime


@dataclass
class ForecastModel:
    forecast_datetime: datetime  # datetime for the weather forecast
    analysis_datetime: datetime  # datetime for the forecast analysis
    adm4_code: str  # district level four code, the forecast location
    temprature: int  # temprature in celcius
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
