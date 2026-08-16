"""Start Job Finder locally and keep the browser-backed application available."""

import time

from job_finder.application import ApplicationLauncher
from job_finder.settings import get_settings


def main() -> None:
    """Open one loopback instance until the user stops this process."""

    launcher = ApplicationLauncher(settings=get_settings())
    result = launcher.start()
    print(f"Job Finder disponível em {result.url}. Pressione Ctrl+C para encerrar.")
    try:
        while launcher.is_running:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        launcher.stop()


if __name__ == "__main__":
    main()
