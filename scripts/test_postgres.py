#!/usr/bin/env python3
"""Run tests on a disposable loopback PostgreSQL cluster, never the configured DB."""

import getpass
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    candidates = (
        sorted(Path("/usr/lib/postgresql").glob("*/bin/initdb"))
        if Path("/usr/lib/postgresql").exists()
        else []
    )
    initdb = shutil.which("initdb") or (str(candidates[-1]) if candidates else None)
    if not initdb:
        raise SystemExit(
            "PostgreSQL binaries unavailable; no concurrency tests executed."
        )
    pg_ctl = str(Path(initdb).with_name("pg_ctl"))
    artifacts = ROOT / ".test-artifacts"
    artifacts.mkdir(mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="postgres-", dir=artifacts) as folder:
        folder = Path(folder)
        data = folder / "data"
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        subprocess.run(
            [
                initdb,
                "-D",
                str(data),
                "--auth-local=trust",
                "--auth-host=trust",
                "--no-locale",
                "--encoding=UTF8",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        started = False
        try:
            subprocess.run(
                [
                    pg_ctl,
                    "-D",
                    str(data),
                    "-l",
                    str(folder / "server.log"),
                    "-o",
                    f"-h 127.0.0.1 -p {port} -k {folder} -c fsync=off",
                    "-w",
                    "start",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            started = True
            env = {
                **os.environ,
                "DJANGO_TEST_SQLITE": "False",
                "DJANGO_ENV": "test",
                "POSTGRES_DB": "postgres",
                "POSTGRES_USER": getpass.getuser(),
                "POSTGRES_PASSWORD": "",
                "POSTGRES_HOST": "127.0.0.1",
                "POSTGRES_PORT": str(port),
                "POSTGRES_CONN_MAX_AGE": "0",
                "POSTGRES_TEST_DB": "test_isolated_events",
            }
            result = subprocess.run(
                [
                    str(ROOT / "backend/.venv/bin/python"),
                    "-B",
                    "manage.py",
                    "test",
                    "--settings=config.test_settings",
                    "--noinput",
                    "--verbosity=1",
                ],
                cwd=ROOT / "backend",
                env=env,
            )
        finally:
            if started:
                subprocess.run(
                    [pg_ctl, "-D", str(data), "-m", "fast", "-w", "stop"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
