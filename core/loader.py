from __future__ import annotations

import asyncio
import importlib
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)


class ModuleLoader:
    def __init__(self, runtime, modules_path: str = "modules"):
        self.runtime = runtime
        self.modules_path = Path(modules_path)
        self.modules = {}
        self._unload_locks = {}

    async def discover(self):
        self.modules_path.mkdir(exist_ok=True)
        modules = []
        for file in self.modules_path.glob("*.py"):
            if file.name.startswith("__"):
                continue
            name = file.stem
            mod = importlib.import_module(f"modules.{name}")
            module = getattr(mod, "module", None)
            if module is not None:
                self.modules[name] = module
                modules.append(module)
        return modules

    async def unload_module(self, name: str):
        if name not in self.modules:
            return
        lock = self._unload_locks.setdefault(name, asyncio.Lock())
        async with lock:
            if name not in self.modules:
                return
            module = self.modules[name]
            try:
                await asyncio.wait_for(module.stop(), timeout=5.0)
            except asyncio.TimeoutError:
                log.error(f"Module {name} stop timeout")
            await self.runtime.task_manager.cancel_all(name, timeout=5.0)
            sys.modules.pop(f"modules.{name}", None)
            del self.modules[name]
            log.info(f"Module {name} unloaded")
