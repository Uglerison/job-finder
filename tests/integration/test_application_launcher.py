import json
from pathlib import Path

from job_finder.application import ApplicationLauncher, InstanceLock
from job_finder.settings import Settings


def test_instance_lock_exposes_the_existing_url_and_releases_it(tmp_path: Path) -> None:
    lock_path = tmp_path / "job-finder.instance.json"
    first_lock = InstanceLock(lock_path)
    second_lock = InstanceLock(lock_path)
    url = "http://127.0.0.1:48123"

    assert first_lock.acquire(url)
    assert not second_lock.acquire("http://127.0.0.1:48124")
    assert second_lock.existing_url == url

    first_lock.release()

    assert not lock_path.exists()
    assert second_lock.acquire("http://127.0.0.1:48124")
    second_lock.release()


def test_instance_lock_recovers_an_invalid_stale_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "job-finder.instance.json"
    lock_path.write_text(
        json.dumps({"pid": 0, "url": "http://127.0.0.1:48123"}),
        encoding="utf-8",
    )
    lock = InstanceLock(lock_path)

    assert lock.acquire("http://127.0.0.1:48124")
    assert lock.existing_url == "http://127.0.0.1:48124"

    lock.release()


def test_application_launcher_reuses_existing_url_then_releases_the_instance_lock(
    tmp_path: Path,
) -> None:
    settings = Settings(data_dir=tmp_path / "data", environment="test")
    first_browser_urls: list[str] = []
    second_browser_urls: list[str] = []
    first_launcher = ApplicationLauncher(settings, browser_opener=first_browser_urls.append)
    second_launcher = ApplicationLauncher(settings, browser_opener=second_browser_urls.append)

    try:
        first_result = first_launcher.start()
        second_result = second_launcher.start()

        assert not first_result.reused_existing_instance
        assert second_result.reused_existing_instance
        assert second_result.url == first_result.url
        assert first_launcher.is_running
        assert not second_launcher.is_running
        assert first_browser_urls == [first_result.url]
        assert second_browser_urls == [first_result.url]
    finally:
        second_launcher.stop()
        first_launcher.stop()

    next_browser_urls: list[str] = []
    next_launcher = ApplicationLauncher(settings, browser_opener=next_browser_urls.append)
    try:
        next_result = next_launcher.start()

        assert not next_result.reused_existing_instance
        assert next_browser_urls == [next_result.url]
    finally:
        next_launcher.stop()
