import os
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
    os.makedirs(LOGS_FOLDER, exist_ok=True)

    # define log filename, which is the datetime when the app run
    LOG_FILENAME = f"{LOGS_FOLDER}/{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.log"

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
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def setup_argparse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="weather")
    parser.add_argument("--adm4", type=str, required=True)
    return parser.parse_args()


async def run_app(adm4_code: str) -> None:
    logger.info("App started")
    async with AsyncClient() as client:
        extractor = ExtractForecast(client)
        transformer = TransformForecast(extractor, adm4_code)
        loader = LoadForecast(transformer)
        await loader.load_transformed_forecast()
    logger.info("App finished successfully")


# package bootstrap
def main() -> None:
    setup_logging()
    args = setup_argparse()
    try:
        asyncio.run(run_app(args.adm4))
    except DomainError as e:
        logger.critical(e)
        logger.info("App finished with error")
        sys.exit(1)


if __name__ == "__main__":
    main()
