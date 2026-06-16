import sys
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime
from httpx import AsyncClient
from src.core.extract import ExtractForecast
from src.core.transform import TransformForecast
from src.core.load import LoadForecast
from src.core.exceptions import DomainError

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    # create folder for logs if not exists
    LOGS_FOLDER = Path("logs")
    LOGS_FOLDER.mkdir(exist_ok=True)
    

    # define log filename, which is the datetime when the app run
    LOG_FILENAME = Path(
        f"{LOGS_FOLDER}/{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.log"
    )

    # define loggers level
    LOGS_LEVEL = logging.DEBUG

    logging.basicConfig(
        level=LOGS_LEVEL,
        format="%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_FILENAME, "w"),
            logging.StreamHandler(),
        ],
    )

    # supress loggers from dependencies
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def setup_argparse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="weather")
    parser.add_argument("--adm4", type=str, required=True)
    return parser.parse_args()


def setup_db_url_and_path(adm4_code: str) -> str:
    # define database url, which is sqlite currently
    DB_URL = "sqlite:///"

    # create folder for db if not exists
    DB_FOLDER = Path("database")
    DB_FOLDER.mkdir(exist_ok=True)

    # define db filename, which is based on the adm4_code
    DB_FILENAME = f"{DB_FOLDER}/{adm4_code}_weather_forecast.db"

    return DB_URL + DB_FILENAME


async def run_app(adm4_code: str, db_url: str) -> None:
    logger.info("App started")
    async with AsyncClient() as client:
        extractor = ExtractForecast(client)
        transformer = TransformForecast(extractor, adm4_code)
        loader = LoadForecast(transformer)
        loader.setup_db(db_url)
        await loader.load_transformed_forecast()
    logger.info("App finished successfully")


# package bootstrap
def main() -> None:
    setup_logging()
    args = setup_argparse()
    db_url = setup_db_url_and_path(args.adm4)
    try:
        asyncio.run(run_app(args.adm4, db_url))
    except DomainError as e:
        logger.critical(e)
        logger.info("App finished with error")
        sys.exit(1)


if __name__ == "__main__":
    main()
