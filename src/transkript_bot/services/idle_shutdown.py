from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


def should_shutdown(last_activity_sec: float, idle_limit_sec: int) -> bool:
    return last_activity_sec >= idle_limit_sec


async def idle_shutdown_loop(queue, state: dict[str, Any], idle_limit_sec: int) -> None:
    while True:
        await asyncio.sleep(30)
        last_activity = state.get("last_activity", time.time())
        idle_for = time.time() - last_activity
        worker_busy = bool(state.get("worker_busy", False))
        if queue.empty() and not worker_busy and should_shutdown(idle_for, idle_limit_sec):
            logger.info(
                "Idle shutdown triggered (idle_for=%.1fs idle_limit=%ss)",
                idle_for,
                idle_limit_sec,
            )
            os._exit(0)
