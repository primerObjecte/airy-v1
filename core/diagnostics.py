from __future__ import annotations

import asyncio
import time

from .storage import AsyncKVStorage


class Diagnostics:
    def __init__(self, storage: AsyncKVStorage, max_errors: int = 50, max_error_len: int = 500):
        self.storage = storage
        self.max_errors = max_errors
        self.max_error_len = max_error_len
        self._lock = asyncio.Lock()
        self._enabled = True

    async def _ensure_storage(self):
        try:
            await self.storage.get("diag_errors", [])
        except Exception:
            await self.storage.set("diag_errors", [])
            await self.storage.set("diag_last_crash", None)

    async def log_error(self, source: str, error: str):
        if not self._enabled:
            return
        if len(error) > self.max_error_len:
            error = error[: self.max_error_len] + "..."
        async with self._lock:
            errors = await self.storage.get("diag_errors", [])
            errors.append({"ts": time.time(), "source": source, "error": error})
            if len(errors) > self.max_errors:
                errors = errors[-self.max_errors:]
            await self.storage.set("diag_errors", errors)

    async def log_crash(self, reason: str):
        if not self._enabled:
            return
        await self.storage.set("diag_last_crash", {"ts": time.time(), "reason": reason[: self.max_error_len]})

    async def get_report(self):
        async with self._lock:
            return {
                "errors": await self.storage.get("diag_errors", []),
                "last_crash": await self.storage.get("diag_last_crash"),
            }

    def disable(self):
        self._enabled = False
