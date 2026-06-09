from pydantic import BaseModel, ConfigDict, AwareDatetime, NaiveDatetime


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RawLocation(StrictModel):
    adm1: str
    adm2: str
    adm3: str
    adm4: str
    provinsi: str
    kotkab: str
    kecamatan: str
    desa: str
    lon: float
    lat: float
    timezone: str
    type: str


class RawForecast(StrictModel):
    datetime: AwareDatetime  # datetime (ISO 8601)
    t: int  # temprature (celcius)
    tcc: int  # total cloud coverage (percent)
    tp: float  # total precipitation | total rain fall (mm)
    weather: int  # weather code (BMKG forecast code)
    weather_desc: str  # weather description in indonesian (string)
    weather_desc_en: str  # weather description in english (string)
    wd_deg: int  # wind direction (degree)
    wd: str  # wind direction from (compas)
    wd_to: str  # wind direction to (compas)
    ws: float  # wind speed (km/h)
    hu: int  # humidity (percent)
    vs: int  # visibility (meter)
    vs_text: str  # visibility (km in string)
    time_index: str  # forecast time window (hour range)
    analysis_date: NaiveDatetime  # forecast production time (datetime)
    image: str  # url to BMKG weather icon (url / link)
    utc_datetime: NaiveDatetime  # utc datetime (datetime)
    local_datetime: NaiveDatetime  # local datetime (datetime)
