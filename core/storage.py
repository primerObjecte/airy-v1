from __future__ import annotations

import asyncio
import json
from pathlib import Path


class AsyncKVStorage:
    def __init__(self, filename: str = "storage.json"):
        self._path = Path(filename)
        self._data: dict = {}
        self._lock = asyncio.Lock()
        self._loaded = False

    async def _load(self):
        if self._loaded:
            return
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}
        self._loaded = True

    async def get(self, key, default=None):
        async with self._lock:
            await self._load()
            return self._data.get(key, default)

    async def set(self, key, value):
        async with self._lock:
            await self._load()
            self._data[key] = value
            await asyncio.to_thread(self._atomic_write)

    def _atomic_write(self):
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def shutdown(self):
        self._atomic_write()
