"""Lifecycle management for the Job Finder loopback web server."""

import socket
import time
from dataclasses import dataclass, field
from threading import Thread

import uvicorn
from fastapi import FastAPI

LOOPBACK_HOST = "127.0.0.1"


def find_available_port(host: str = LOOPBACK_HOST) -> int:
    """Reserve an ephemeral loopback port long enough to discover its number."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_server:
        socket_server.bind((host, 0))
        return int(socket_server.getsockname()[1])


@dataclass
class LocalServer:
    """Run one Uvicorn server locally and provide explicit start/stop operations."""

    application: FastAPI
    port: int | None = None
    startup_timeout_seconds: float = 10
    _server: uvicorn.Server | None = field(default=None, init=False, repr=False)
    _thread: Thread | None = field(default=None, init=False, repr=False)

    @property
    def is_running(self) -> bool:
        return bool(
            self._server
            and self._server.started
            and self._thread
            and self._thread.is_alive()
        )

    @property
    def url(self) -> str:
        if self.port is None:
            raise RuntimeError("The local server has not been assigned a port.")

        return f"http://{LOOPBACK_HOST}:{self.port}"

    def start(self) -> None:
        """Start the loopback server and wait until Uvicorn finishes application startup."""

        if self.is_running:
            raise RuntimeError("The local server is already running.")

        self.port = self.port or find_available_port()
        configuration = uvicorn.Config(
            app=self.application,
            host=LOOPBACK_HOST,
            port=self.port,
            log_config=None,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(configuration)
        self._thread = Thread(
            daemon=True,
            name="job-finder-local-server",
            target=self._server.run,
        )
        self._thread.start()
        self._wait_until_started()

    def stop(self) -> None:
        """Request a graceful shutdown and wait for the loopback server to stop."""

        if self._server is None or self._thread is None:
            return

        self._server.should_exit = True
        self._thread.join(timeout=self.startup_timeout_seconds)

        if self._thread.is_alive():
            raise TimeoutError("The local server did not stop within the configured timeout.")

        self._server = None
        self._thread = None

    def __enter__(self) -> "LocalServer":
        self.start()
        return self

    def __exit__(self, _exception_type: object, _exception: object, _traceback: object) -> None:
        self.stop()

    def _wait_until_started(self) -> None:
        if self._server is None or self._thread is None:
            raise RuntimeError("The local server was not initialized.")

        deadline = time.monotonic() + self.startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._server.started:
                return

            if not self._thread.is_alive():
                self.stop()
                raise RuntimeError("The local server stopped before becoming ready.")

            time.sleep(0.01)

        self.stop()
        raise TimeoutError("The local server did not become ready within the configured timeout.")
