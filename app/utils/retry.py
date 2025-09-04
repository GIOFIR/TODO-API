import asyncio
import logging

logger = logging.getLogger(__name__)

async def with_retry(func, retries: int = 3, delay: float = 1.0):
    """
    Runs an async function with retry logic.
    func: async function without parameters.
    retries: number of attempts before failing.
    delay: delay (seconds) between attempts.
    """
    for attempt in range(1, retries + 1):
        try:
            return await func()
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                await asyncio.sleep(delay)
            else:
                logger.error("All retry attempts failed.")
                raise
