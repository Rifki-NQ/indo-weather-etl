import asyncio
import logging
from collections.abc import Iterable
from src.core.models.protocols import LoadProtocol
from src.core.exceptions import DomainError, InvalidAdm4CodeError

logger = logging.getLogger(__name__)


class ETLRunner:
    TASK_DELAY = 1.1
    MAX_CONCURRENT_TASKS = 10

    def __init__(self, loader: LoadProtocol) -> None:
        self.loader = loader
        self.total_tasks = 0
        self.successful_tasks = 0
        self.peak_active_tasks = 0
        self.active_tasks: set[asyncio.Task[None]] = set()
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_TASKS)

    async def run_batch(self, adm4_codes: Iterable[str]) -> None:
        """Start batch running, with delays per task creation to avoid rate limit."""
        for adm4_code in adm4_codes:
            await self.semaphore.acquire()
            self._create_runner_task(adm4_code)
            self.total_tasks += 1
            await asyncio.sleep(self.TASK_DELAY)
        if self.active_tasks:
            # wait until all remaining tasks are finished
            await asyncio.wait(self.active_tasks)
        logger.info(
            f"{self.successful_tasks} / {self.total_tasks} tasks finished successfully"
        )
        logger.info(f"Task creation delay: {self.TASK_DELAY}")
        logger.info(f"Peak concurrency: {self.peak_active_tasks}")
        

    def _create_runner_task(self, adm4_code: str) -> None:
        """Create the runner task then add it to self.active_tasks."""
        task = asyncio.create_task(self.loader.load_transformed_forecast(adm4_code))
        task.set_name(f"Task-{adm4_code}")
        task.add_done_callback(self._handle_task_completion)
        self.active_tasks.add(task)
        self.peak_active_tasks = max(self.peak_active_tasks, len(self.active_tasks))
        logger.info(f"Task: {task.get_name()} created")

    def _handle_task_completion(self, task: asyncio.Task[None]) -> None:
        try:
            task.result()
        except InvalidAdm4CodeError as e:
            logger.error(f"Invalid adm4_code: {e.adm4_code}")
        except DomainError as e:
            logger.error(e)
        except asyncio.CancelledError:
            logger.error("Task was cancelled")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        else:
            logger.info(f"Task: {task.get_name()} finished successfully")
            self.successful_tasks += 1
            return
        finally:
            self.semaphore.release()
            self.active_tasks.discard(task)
        logger.info(f"Task: {task.get_name()} finished with error")
