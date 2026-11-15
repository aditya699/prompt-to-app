"""In-process pub/sub for build logs.

The build worker publishes every log event here as well as saving it to the
database. An SSE request subscribes, replays what is already saved, then
follows the live events. One server process means a dict of queues is enough;
with several processes you would put Redis pub/sub behind the same interface.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

# A published item is either a log event (dict) or CLOSED, meaning the build ended.
CLOSED = object()


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[Any]]] = defaultdict(set)

    def publish(self, build_id: int, item: Any) -> None:
        for queue in self._subscribers.get(build_id, ()):
            queue.put_nowait(item)

    def close(self, build_id: int) -> None:
        self.publish(build_id, CLOSED)

    @asynccontextmanager
    async def subscribe(self, build_id: int) -> AsyncIterator[asyncio.Queue[Any]]:
        queue: asyncio.Queue[Any] = asyncio.Queue()
        self._subscribers[build_id].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[build_id].discard(queue)
            if not self._subscribers[build_id]:
                del self._subscribers[build_id]
