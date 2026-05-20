from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

log = logging.getLogger(__name__)


class Event:
    def __init__(self, type: str, data=None):
        self.type = type
        self.data = data or {}


class EventBus:
    def __init__(self):
        self._handlers = defaultdict(list)
        self._failures = defaultdict(list)
        self._suspended = {}
        self._diag = None
        self._error_threshold = 3
        self._error_window = 60
        self._suspend_duration = 60

    def set_diagnostics(self, diag):
        self._diag = diag

    def on(self, event_type: str, handler, priority: int = 0, module_name: str = "__core__"):
        self._handlers[event_type].append((priority, handler, module_name))
        self._handlers[event_type].sort(key=lambda x: x[0], reverse=True)

    def _record_failure(self, module: str, event_type: str):
        key = (module, event_type)
        now = asyncio.get_running_loop().time()
        self._failures[key] = [t for t in self._failures[key] if now - t < self._error_window]
        self._failures[key].append(now)
        if len(self._failures[key]) >= self._error_threshold:
            self._suspended[key] = now + self._suspend_duration

    def _is_suspended(self, module: str, event_type: str) -> bool:
        key = (module, event_type)
        until = self._suspended.get(key)
        if until is None:
            return False
        now = asyncio.get_running_loop().time()
        if now >= until:
            self._suspended.pop(key, None)
            return False
        return True

    async def emit(self, event: Event):
        for _, handler, module in list(self._handlers.get(event.type, [])):
            if self._is_suspended(module, event.type):
                continue
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                log.error(f"Handler {handler} from module {module} failed: {e}")
                try:
                    if getattr(self, '_diag', None) and (module != "__core__" or (module == "__core__" and "diagnostics" not in str(handler))):
                        await self._diag.log_error(event.type, str(e))
                    self._record_failure(module, event.type)
                except Exception as diag_err:
                    log.error(f"Diagnostics failed: {diag_err}")
