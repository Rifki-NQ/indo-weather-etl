import logging
from datetime import date, datetime
from sqlalchemy import delete
from src.core.models.contexts import DBContext

logger = logging.getLogger(__name__)


async def delete_past_forecasts(
    db: DBContext,
    date_to: date | datetime,
) -> None:
    """Delete all rows of weather_forecast table up until given 'date_to'."""
    if isinstance(date_to, datetime):
        # Deletion is day-scoped; drop the time component.
        date_to = date_to.date()
    async with db.engine.begin() as conn:
        stmt = (
            delete(db.forecast_table)
            .where(db.forecast_table.c.forecast_datetime < date_to)
            .returning(db.forecast_table.c.forecast_datetime)
        )
        result = await conn.execute(stmt)
        deleted = result.scalars().all()
        if deleted:
            logger.info(
                f"deleted weather_forecast: {len(deleted)} rows, range {min(deleted)} to {max(deleted)}"
            )
        else:
            logger.info("no rows to delete")
