import socket
from pathlib import Path

from job_finder.smoke import run_smoke_test
from job_finder.settings import Settings


def test_smoke_test_starts_checks_and_stops_the_local_foundation(tmp_path: Path) -> None:
    frontend_dist = tmp_path / "frontend-dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<div id=\"root\">Job Finder</div>", encoding="utf-8")
    settings = Settings(data_dir=tmp_path / "data", environment="test")

    result = run_smoke_test(settings, frontend_dist_dir=frontend_dist)

    assert result.health == {"status": "ok", "version": "0.1.0"}
    assert result.frontend_content == "<div id=\"root\">Job Finder</div>"
    assert result.database_path.is_file()
    assert result.url.startswith("http://127.0.0.1:")

    port = int(result.url.rsplit(":", maxsplit=1)[1])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_server:
        socket_server.bind(("127.0.0.1", port))
