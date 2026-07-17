import csv
import logging
from pathlib import Path
from collections.abc import Iterable
from src.core.exceptions import (
    NotFileError,
    EmptyFileError,
    NotCSVFileError,
    InvalidColumnName,
)

logger = logging.getLogger(__name__)


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
