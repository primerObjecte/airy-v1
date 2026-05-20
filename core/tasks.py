from __future__ import annotations

import asyncio
from collections import defaultdict


class TaskManager:
    def __init__(self, limit_per_module: int = 100):
        self._tasks: dict[str, set[asyncio.Task]] = defaultdict(set)
        self._limit_per_module = limit_per_module
        self._lock = asyncio.Lock()

    async def create_task(self, module_name: str, coro, *, name: str | None = None) -> asyncio.Task:
        async with self._lock:
            if len(self._tasks[module_name]) >= self._limit_per_module:
                raise RuntimeError(f"Module {module_name} exceeded task limit")
            task = asyncio.create_task(coro, name=name)
            self._tasks[module_name].add(task)
            task.add_done_callback(lambda t, m=module_name: self._tasks[m].discard(t))
            return task

    async def cancel_all(self, module_name: str, timeout: float = 2.0):
        async with self._lock:
            tasks = list(self._tasks.pop(module_name, set()))
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
            except asyncio.TimeoutError:
                pass
