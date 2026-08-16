"""Start Job Finder locally and keep the browser-backed application available."""

import os
import time

from job_finder.application import ApplicationLauncher
from job_finder.settings import get_settings


def main() -> None:
    """Open one loopback instance until the user stops this process."""

    settings = get_settings()
    if os.getenv("JOB_FINDER_NO_BROWSER") == "1":
        launcher = ApplicationLauncher(settings=settings, browser_opener=lambda _url: False)
    else:
        launcher = ApplicationLauncher(settings=settings)
    result = launcher.start()
    print(f"Job Finder disponível em {result.url}. Pressione Ctrl+C para encerrar.", flush=True)
    try:
        while launcher.is_running:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        launcher.stop()


if __name__ == "__main__":
    main()
