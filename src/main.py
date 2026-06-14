import sys
import asyncio
import logging
from httpx import AsyncClient
from src.core.extract import ExtractForecast
from src.core.transform import TransformForecast
from src.core.load import LoadForecast
from src.core.exceptions import DomainError

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler("logs.log", "w"), logging.StreamHandler()],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def run_app() -> None:
    setup_logging()
    logger.info("App started")
    async with AsyncClient() as client:
        extractor = ExtractForecast(client)
        transformer = TransformForecast(extractor, "32.16.20.2003")
        loader = LoadForecast(transformer)
        await loader.load_transformed_forecast()
    logger.info("App finished successfully")


def main() -> None:
    try:
        asyncio.run(run_app())
    except DomainError as e:
        logger.critical(e)
        logger.info("App finished with error")
        sys.exit(1)


if __name__ == "__main__":
    main()
