import json
import socket
from pathlib import Path
from urllib.request import urlopen

from job_finder.launcher import LOOPBACK_HOST, LocalServer, find_available_port
from job_finder.logging import log_file_path
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
    log_content = log_file_path(tmp_path).read_text(encoding="utf-8")
    assert "Starting local Job Finder service." in log_content
    assert "Stopping local Job Finder service." in log_content
    log_file_path(tmp_path).replace(log_file_path(tmp_path).with_suffix(".closed"))


def test_local_server_serves_frontend_and_api_from_one_url(tmp_path: Path) -> None:
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<main>Job Finder</main>", encoding="utf-8")

    settings = Settings(data_dir=tmp_path / "data", environment="test")
    server = LocalServer(
        create_app(settings, frontend_dist_dir=frontend_dist),
        startup_timeout_seconds=5,
    )

    try:
        server.start()

        with urlopen(f"{server.url}/", timeout=2) as response:
            root = response.read().decode()
        with urlopen(f"{server.url}/pipeline", timeout=2) as response:
            pipeline = response.read().decode()
        with urlopen(f"{server.url}/api/health", timeout=2) as response:
            health = json.loads(response.read())
    finally:
        server.stop()

    assert root == "<main>Job Finder</main>"
    assert pipeline == "<main>Job Finder</main>"
    assert health == {"status": "ok", "version": "0.1.0"}
