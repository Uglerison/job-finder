import json
import socket
from pathlib import Path
from urllib.request import urlopen

from job_finder.launcher import LOOPBACK_HOST, LocalServer, find_available_port
from job_finder.main import create_app
from job_finder.settings import Settings


def test_find_available_port_returns_a_port_that_can_be_bound() -> None:
    port = find_available_port()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_server:
        socket_server.bind((LOOPBACK_HOST, port))


def test_local_server_starts_on_loopback_migrates_and_stops(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, environment="test")
    server = LocalServer(create_app(settings), startup_timeout_seconds=5)

    try:
        server.start()

        with urlopen(f"{server.url}/api/health", timeout=2) as response:
            payload = json.loads(response.read())

        assert server.url.startswith(f"http://{LOOPBACK_HOST}:")
        assert payload == {"status": "ok", "version": "0.1.0"}
        assert (tmp_path / "job-finder.db").is_file()
    finally:
        server.stop()

    assert not server.is_running
