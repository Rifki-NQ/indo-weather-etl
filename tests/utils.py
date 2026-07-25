from typing import Any
from collections.abc import Sequence
from sqlalchemy import Row, MetaData, select
from sqlalchemy.ext.asyncio import AsyncConnection
from src.core.etl.load import LoadForecast


async def drop_all_tables(conn: AsyncConnection) -> None:
    metadata = MetaData()
    await conn.run_sync(metadata.reflect)
    await conn.run_sync(metadata.drop_all)


async def read_forecast_table_rows(loader_obj: LoadForecast) -> Sequence[Row[Any]]:
    db = loader_obj._get_db()  # pyright: ignore[reportPrivateUsage]
    stmt = select(db.forecast_table).order_by(db.forecast_table.c.forecast_datetime)
    async with db.engine.begin() as conn:
        result = await conn.execute(stmt)
        return result.fetchall()
