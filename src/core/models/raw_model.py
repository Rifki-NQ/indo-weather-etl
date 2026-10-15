from pydantic import AwareDatetime, BaseModel, ConfigDict, NaiveDatetime


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
    t: int  # temperature (celcius)
    tcc: int | None  # total cloud coverage (percent)
    tp: float | None  # total precipitation | total rain fall (mm)
    weather: int | None  # weather code (BMKG forecast code)
    weather_desc: str | None  # weather description in indonesian (string)
    weather_desc_en: str | None  # weather description in english (string)
    wd_deg: int | None  # wind direction (degree)
    wd: str | None  # wind direction from (compass)
    wd_to: str | None  # wind direction to (compass)
    ws: float | None  # wind speed (km/h)
    hu: int | None  # humidity (percent)
    vs: int | None  # visibility (meter)
    vs_text: str | None  # visibility (km in string)
    time_index: str | None  # forecast time window (hour range)
    analysis_date: NaiveDatetime | None  # forecast production time (datetime)
    image: str | None  # url to BMKG weather icon (url / link)
    utc_datetime: NaiveDatetime | None  # utc datetime (datetime)
    local_datetime: NaiveDatetime | None  # local datetime (datetime)
