from dataclasses import dataclass
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class DBContext:
    engine: AsyncEngine
    location_table: Table
    forecast_table: Table
