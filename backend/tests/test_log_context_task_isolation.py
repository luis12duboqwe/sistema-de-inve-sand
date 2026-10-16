import asyncio
import logging

from app.utils.logging_config import LogContext


def test_log_context_is_task_isolated_and_keeps_one_factory():
    emitted = []

    class Capture(logging.Handler):
        def emit(self, record):
            emitted.append((getattr(record, "request_id", None), record.msg))

    logger = logging.getLogger("test.softmobile.logcontext")
    capture = Capture()
    logger.addHandler(capture)
    logger.setLevel(logging.INFO)

    async def worker(request_id):
        with LogContext(request_id=request_id):
            await asyncio.sleep(0)
            logger.info("event")
            await asyncio.sleep(0)
            logger.info("done")

    async def runner():
        await asyncio.gather(worker("A"), worker("B"))

    try:
        asyncio.run(runner())
    finally:
        logger.removeHandler(capture)
    assert sorted(emitted) == sorted([("A", "event"), ("A", "done"), ("B", "event"), ("B", "done")])
