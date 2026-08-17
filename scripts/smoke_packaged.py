"""Smoke-test a built Windows executable in an isolated local profile."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

_URL_PATTERN = re.compile(r"Job Finder .* em (http://127\.0\.0\.1:\d+)")


def _read_health(url: str) -> dict[str, str]:
    with urlopen(f"{url}/api/health", timeout=1.0) as response:
        payload = json.loads(response.read())
    if response.status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"Resposta de saúde inesperada: {payload!r}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-testa o executável Windows do Job Finder.")
    parser.add_argument("executable", type=Path, help="Caminho para JobFinder.exe")
    parser.add_argument("--timeout", type=float, default=20.0)
    arguments = parser.parse_args()
    executable = arguments.executable.resolve()
    if not executable.is_file():
        raise SystemExit(f"Executável não encontrado: {executable}")

    with tempfile.TemporaryDirectory(prefix="job-finder-packaged-smoke-") as temporary_directory:
        local_app_data = Path(temporary_directory) / "localappdata"
        environment = os.environ.copy()
        environment.update(
            {
                "LOCALAPPDATA": str(local_app_data),
                "JOB_FINDER_ENVIRONMENT": "test",
                "JOB_FINDER_LOG_LEVEL": "WARNING",
                "JOB_FINDER_NO_BROWSER": "1",
            }
        )
        output_file = Path(temporary_directory) / "process-output.log"
        with output_file.open("w", encoding="utf-8") as output_stream:
            process = subprocess.Popen(
                [str(executable)],
                cwd=executable.parent,
                env=environment,
                stdout=output_stream,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                deadline = time.monotonic() + arguments.timeout
                output = ""
                url: str | None = None
                while time.monotonic() < deadline:
                    output = output_file.read_text(encoding="utf-8", errors="replace")
                    match = _URL_PATTERN.search(output)
                    if match:
                        url = match.group(1)
                        break
                    if process.poll() is not None:
                        break
                    time.sleep(0.05)
                if url is None:
                    raise RuntimeError(
                        f"O executável não publicou uma URL local. Saída: {output!r}"
                    )

                health = _read_health(url)
                with urlopen(f"{url}/", timeout=1.0) as response:
                    frontend = response.read().decode("utf-8")
                if health.get("status") != "ok" or not frontend.strip():
                    raise RuntimeError("Health ou frontend vazio no smoke test empacotado.")
                database = local_app_data / "JobFinder" / "job-finder.db"
                if not database.is_file():
                    raise RuntimeError(f"Banco não criado em {database}")
                print(f"Packaged smoke test passed: {url}")
                return 0
            finally:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
