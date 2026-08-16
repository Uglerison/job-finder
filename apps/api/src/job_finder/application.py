"""Desktop application lifecycle, browser launch, and single-instance control."""

import json
import os
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from job_finder.launcher import LOOPBACK_HOST, LocalServer, find_available_port
from job_finder.main import create_app
from job_finder.settings import Settings

INSTANCE_LOCK_FILENAME = "job-finder.instance.json"
HEALTH_CHECK_ATTEMPTS = 3
HEALTH_CHECK_DELAY_SECONDS = 0.1
HEALTH_CHECK_TIMEOUT_SECONDS = 0.25
BrowserOpener = Callable[[str], object]


def open_browser(url: str) -> bool:
    """Open the locally running application in the user's default browser."""

    return webbrowser.open(url, new=2)


@dataclass(frozen=True)
class LaunchResult:
    """Describe the browser URL and whether a running instance was reused."""

    url: str
    reused_existing_instance: bool


@dataclass
class InstanceLock:
    """Coordinate one local Job Finder process through an exclusive metadata file."""

    path: Path
    _descriptor: int | None = field(default=None, init=False, repr=False)

    @property
    def existing_url(self) -> str | None:
        """Return the validated loopback URL recorded by the active instance."""

        record = self._read_record()
        if record is None:
            return None

        url = record.get("url")
        if not isinstance(url, str):
            return None

        parsed_url = urlparse(url)
        if parsed_url.scheme != "http" or parsed_url.hostname != LOOPBACK_HOST:
            return None

        try:
            port = parsed_url.port
        except ValueError:
            return None

        return url if port is not None else None

    def acquire(self, url: str) -> bool:
        """Atomically claim this instance lock and store the URL for later launches."""

        if self._descriptor is not None:
            raise RuntimeError("This instance lock is already held by this process.")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                descriptor = os.open(
                    self.path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError:
                if not self._is_stale():
                    return False

                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass
            else:
                break
        else:
            return False

        record = json.dumps({"pid": os.getpid(), "url": url}, separators=(",", ":"))
        try:
            os.write(descriptor, record.encode("utf-8"))
            os.fsync(descriptor)
        except BaseException:
            os.close(descriptor)
            self.path.unlink(missing_ok=True)
            raise

        self._descriptor = descriptor
        return True

    def release(self) -> None:
        """Release a lock held by this process so a later launch can start normally."""

        if self._descriptor is None:
            return

        os.close(self._descriptor)
        self._descriptor = None
        self.path.unlink(missing_ok=True)

    def reclaim_unresponsive_instance(self, expected_url: str) -> bool:
        """Remove a lock only when it still identifies the failed loopback URL."""

        record = self._read_record()
        if record is None or record.get("url") != expected_url:
            return False
        try:
            self.path.unlink()
        except (FileNotFoundError, PermissionError):
            return False
        return True

    def _is_stale(self) -> bool:
        """Determine whether a valid lock record belongs to a process that has ended."""

        record = self._read_record()
        if record is None:
            return False

        process_id = record.get("pid")
        if not isinstance(process_id, int) or isinstance(process_id, bool) or process_id <= 0:
            return True

        return not _process_is_running(process_id)

    def _read_record(self) -> dict[str, object] | None:
        try:
            record = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        return record if isinstance(record, dict) else None


def _process_is_running(process_id: int) -> bool:
    """Return whether a process exists without sending Windows a signal."""

    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.__dict__["windll"].kernel32
        kernel32.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulong),
        )
        kernel32.GetExitCodeProcess.restype = ctypes.c_bool
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.restype = ctypes.c_bool
        process_handle = kernel32.OpenProcess(
            process_query_limited_information,
            False,
            process_id,
        )
        if not process_handle:
            return False

        exit_code = ctypes.c_ulong()
        try:
            if not kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(process_handle)

    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

    return True


def _is_local_service_healthy(url: str) -> bool:
    """Check the local health endpoint without trusting a PID or lock file alone."""

    try:
        with urlopen(f"{url}/api/health", timeout=HEALTH_CHECK_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False

    return response.status == 200 and isinstance(payload, dict) and payload.get("status") == "ok"


def _wait_for_local_service(url: str) -> bool:
    """Give a concurrently starting service a short chance to become healthy."""

    for attempt in range(HEALTH_CHECK_ATTEMPTS):
        if _is_local_service_healthy(url):
            return True
        if attempt < HEALTH_CHECK_ATTEMPTS - 1:
            time.sleep(HEALTH_CHECK_DELAY_SECONDS)
    return False


@dataclass
class ApplicationLauncher:
    """Start the local app once, otherwise bring its current browser tab forward."""

    settings: Settings
    browser_opener: BrowserOpener = open_browser
    _server: LocalServer | None = field(default=None, init=False, repr=False)
    _instance_lock: InstanceLock | None = field(default=None, init=False, repr=False)

    @property
    def is_running(self) -> bool:
        """Whether this launcher owns a running local server."""

        return self._server is not None and self._server.is_running

    def start(self) -> LaunchResult:
        """Open the existing instance or start one loopback server and open its URL."""

        server = self._server
        if server is not None and server.is_running:
            url = server.url
            self.browser_opener(url)
            return LaunchResult(url=url, reused_existing_instance=True)

        port = find_available_port()
        url = f"http://{LOOPBACK_HOST}:{port}"
        instance_lock = InstanceLock(self.settings.data_dir / INSTANCE_LOCK_FILENAME)
        if not instance_lock.acquire(url):
            existing_url = instance_lock.existing_url
            if existing_url is None:
                raise RuntimeError("Another Job Finder instance is starting. Try again shortly.")
            if _wait_for_local_service(existing_url):
                self.browser_opener(existing_url)
                return LaunchResult(url=existing_url, reused_existing_instance=True)
            if not instance_lock.reclaim_unresponsive_instance(existing_url):
                raise RuntimeError(
                    "The existing Job Finder instance is not responding. Close it and try again."
                )
            if not instance_lock.acquire(url):
                raise RuntimeError("Another Job Finder instance is starting. Try again shortly.")

        server = LocalServer(create_app(self.settings), port=port)
        try:
            server.start()
        except BaseException:
            instance_lock.release()
            raise

        self._server = server
        self._instance_lock = instance_lock
        self.browser_opener(server.url)
        return LaunchResult(url=server.url, reused_existing_instance=False)

    def stop(self) -> None:
        """Stop the owned local server and make a future launch available."""

        try:
            if self._server is not None:
                self._server.stop()
        finally:
            self._server = None
            if self._instance_lock is not None:
                self._instance_lock.release()
                self._instance_lock = None
