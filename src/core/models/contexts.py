from dataclasses import dataclass
from sqlalchemy import Engine, Table


@dataclass
class DBContext:
    engine: Engine
    location_table: Table
    forecast_table: Table
