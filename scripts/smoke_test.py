"""Run the local foundation smoke test from a Windows development checkout."""

import argparse
import tempfile
from pathlib import Path

from job_finder.settings import Settings
from job_finder.smoke import run_smoke_test


def main() -> int:
    """Run the local foundation smoke test in an isolated data directory."""

    parser = argparse.ArgumentParser(description="Verify the Job Finder local foundation.")
    parser.add_argument(
        "--frontend-dist",
        type=Path,
        help="Optional path to the compiled frontend directory.",
    )
    arguments = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="job-finder-smoke-") as temporary_directory:
        settings = Settings(data_dir=Path(temporary_directory), environment="test")
        result = run_smoke_test(settings, frontend_dist_dir=arguments.frontend_dist)

    print(f"Smoke test passed: {result.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
