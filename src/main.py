import os
import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from httpx import AsyncClient
from dotenv import load_dotenv
from src.core.etl.extract import ExtractForecast
from src.core.etl.transform import TransformForecast
from src.core.etl.load import LoadForecast
from src.core.runner import ETLRunner
from src.core.utils import yield_csv_value
from src.core.exceptions import DomainError

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    # create folder for logs if not exists
    LOGS_FOLDER = Path("logs")
    LOGS_FOLDER.mkdir(exist_ok=True)

    # define loggers level
    LOGS_LEVEL = logging.INFO

    logging.basicConfig(
        level=LOGS_LEVEL,
        format="%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                filename=Path(LOGS_FOLDER / "weather_etl.log"),
                maxBytes=10_000_000,
                backupCount=5,
                encoding="utf-8",
            ),
        ],
    )

    # supress loggers from dependencies
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


async def run_app(adm4_codes_path: str, db_url: str) -> None:
    logger.info("App started")
    async with AsyncClient() as client:
        extractor = ExtractForecast(client)
        transformer = TransformForecast(extractor)
        loader = LoadForecast(transformer)
        await loader.setup_db(db_url)
        runner = ETLRunner(loader)
        await runner.run_batch(yield_csv_value(Path(adm4_codes_path), "Kode"))
    logger.info("App finished successfully")


# package bootstrap
def main() -> None:
    load_dotenv()
    setup_logging()
    db_url = get_env("DATABASE_URL")
    adm4_codes_path = get_env("ADM4_CODES_PATH")
    try:
        asyncio.run(run_app(adm4_codes_path, db_url))
    except DomainError as e:
        logger.critical(e)
        logger.info("App finished with error")
        sys.exit(1)


if __name__ == "__main__":
    main()
