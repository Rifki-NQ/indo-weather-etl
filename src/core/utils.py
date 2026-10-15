import csv
import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.core.exceptions import (
    EmptyFileError,
    InvalidColumnName,
    NotCSVFileError,
    NotFileError,
)

logger = logging.getLogger(__name__)
ETL_TIMEZONE = ZoneInfo("Asia/Jakarta")


def yield_csv_value(filepath: Path, column_name: str) -> Iterable[str]:
    """Open the filepath then yield the values of given column_name."""
    if not filepath.exists():
        raise FileNotFoundError("Error: file not found")
    elif not filepath.is_file():
        raise NotFileError(filepath)
    elif filepath.stat().st_size == 0:
        raise EmptyFileError(filepath)
    elif not filepath.suffix == ".csv":
        raise NotCSVFileError(filepath.name)

    def _yield() -> Iterable[str]:
        logger.debug(f"Start yielding adm4_codes from {filepath}")
        with open(filepath, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            if column_name not in (reader.fieldnames or []):
                raise InvalidColumnName(column_name)
            for row in reader:
                yield row[column_name]

    return _yield()


def get_current_datetime() -> datetime:
    """Get current datetime in Asia/Jakarta timezone, with tzinfo removed."""
    return datetime.now(tz=ETL_TIMEZONE).replace(tzinfo=None)
