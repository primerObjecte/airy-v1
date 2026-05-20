from __future__ import annotations

import asyncio
import logging
import os
import signal

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from .config import Config
from .diagnostics import Diagnostics
from .events import EventBus
from .loader import ModuleLoader
from .storage import AsyncKVStorage
from .tasks import TaskManager

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AiryRuntime:
    def __init__(self):
        self.config = Config.from_env()
        self.storage = AsyncKVStorage()
        self.event_bus = EventBus()
        self.task_manager = TaskManager()
        self.loader = ModuleLoader(self)
        self.diag = Diagnostics(self.storage)
        self.event_bus.set_diagnostics(self.diag)
        self.client = None
        self._running = False
        self._stopping = False
        self._stop_lock = asyncio.Lock()
        self._health_server = None
        self._message_handler = None

    async def _ensure_ready(self):
        if self.config.api_id <= 0 or not self.config.api_hash or self.config.owner_id <= 0:
            raise RuntimeError("API_ID, API_HASH and OWNER_ID are required")

    async def _health_handler(self, reader, writer):
        try:
            request = await asyncio.wait_for(reader.read(1024), timeout=1.0)
            if b"GET /health" in request:
                ok = (self.client is not None and self.client.is_connected() and self.loader.modules and not getattr(self, "_stopping", False))
                status = 200 if ok else 503
                writer.write(f"HTTP/1.1 {status} OK\nContent-Length: 2\n\nok".encode())
            else:
                writer.write(b"HTTP/1.1 404 Not Found\n\n")
            await writer.drain()
        except asyncio.TimeoutError:
            writer.write(b"HTTP/1.1 408 Request Timeout\n\n")
        except Exception as e:
            log.warning(f"Healthcheck handler error: {e}")
            writer.write(b"HTTP/1.1 500 Internal Server Error\n\n")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _start_healthcheck(self):
        if self._health_server is not None:
            return
        port = int(os.getenv("AIRY_HEALTH_PORT", os.getenv("PORT", "8080")))
        try:
            self._health_server = await asyncio.start_server(self._health_handler, "0.0.0.0", port)
            log.info(f"Healthcheck listening on port {port}")
        except OSError as e:
            log.warning(f"Healthcheck failed to start on port {port}: {e}")
            self._health_server = None

    async def _stop_healthcheck(self):
        if self._health_server:
            self._health_server.close()
            await self._health_server.wait_closed()
            self._health_server = None

    async def _connection_guard(self):
        backoff = 1
        max_backoff = 60
        attempts = 0
        max_attempts = 10
        reconnect_lock = asyncio.Lock()
        while self._running and not getattr(self, "_stopping", False):
            try:
                await self.client.get_me()
                backoff = 1
                attempts = 0
                await asyncio.sleep(30)
            except Exception as e:
                if getattr(self, "_stopping", False):
                    break
                log.warning(f"Connection lost: {e}")
                async with reconnect_lock:
                    try:
                        await self.client.get_me()
                        continue
                    except Exception:
                        pass
                    attempts += 1
                    if attempts > max_attempts:
                        log.critical("Max reconnect attempts reached, stopping process")
                        self._running = False
                        break
                    try:
                        await asyncio.wait_for(self.client.disconnect(), timeout=5.0)
                    except Exception:
                        pass
                    while self._running and not getattr(self, "_stopping", False):
                        try:
                            await asyncio.wait_for(self.client.connect(), timeout=10.0)
                            if not await self.client.is_user_authorized():
                                raise RuntimeError("Not authorized")
                            log.info("Reconnected successfully")
                            attempts = 0
                            break
                        except Exception as retry_err:
                            log.error(f"Reconnect failed: {retry_err}, retry in {backoff}s")
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * 2, max_backoff)

    async def _handle_message(self, event):
        return

    def _setup_signal_handlers(self):
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self.stop()))
            except NotImplementedError:
                pass

    async def start(self):
        await self._ensure_ready()
        self._running = True
        self.client = TelegramClient(
            StringSession(self.config.session_string) if self.config.session_string else StringSession(),
            self.config.api_id,
            self.config.api_hash,
        )
        await self.client.start()
        await self.diag._ensure_storage()
        await self._start_healthcheck()
        self._message_handler = self.client.add_event_handler(self._handle_message, events.NewMessage)
        await self.loader.discover()
        await self.task_manager.create_task("__core__", self._connection_guard(), name="connection_guard")
        self._setup_signal_handlers()
        try:
            await self.client.run_until_disconnected()
        except Exception as e:
            log.critical(f"Runtime crashed: {e}")
            await self.diag.log_crash(str(e))
            raise
        finally:
            await self.stop()

    async def stop(self):
        async with self._stop_lock:
            if self._stopping:
                return
            self._stopping = True
            try:
                log.info("Stopping Airy runtime...")
                self._running = False
                if self.client and self.client.is_connected() and self._message_handler is not None:
                    try:
                        self.client.remove_event_handler(self._message_handler)
                    except Exception:
                        pass
                for name in list(self.loader.modules.keys()):
                    try:
                        await asyncio.wait_for(self.loader.unload_module(name), timeout=5.0)
                    except asyncio.TimeoutError:
                        log.error(f"Unload module {name} timeout")
                await self.task_manager.cancel_all("__core__", timeout=5.0)
                if self.client:
                    try:
                        await asyncio.wait_for(self.client.disconnect(), timeout=5.0)
                    except asyncio.TimeoutError:
                        log.warning("Client disconnect timeout")
                try:
                    await self._stop_healthcheck()
                except Exception as e:
                    log.error(f"Error stopping healthcheck: {e}")
                self.diag.disable()
                try:
                    self.storage.shutdown()
                except Exception as e:
                    log.error(f"Storage shutdown error: {e}")
            finally:
                self._stopping = False
