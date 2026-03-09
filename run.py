from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent


def _read_dotenv() -> dict[str, str]:
    env_file = ROOT / ".env"
    values: dict[str, str] = {}
    if not env_file.exists():
        return values
    for line in env_file.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _replace_host_in_url(url: str, host_map: dict[str, str]) -> str:
    parts = urlsplit(url)
    hostname = parts.hostname
    if not hostname or hostname not in host_map:
        return url

    new_host = host_map[hostname]
    userinfo = ""
    if parts.username:
        userinfo = parts.username
        if parts.password:
            userinfo += f":{parts.password}"
        userinfo += "@"

    port = f":{parts.port}" if parts.port else ""
    new_netloc = f"{userinfo}{new_host}{port}"
    return urlunsplit((parts.scheme, new_netloc, parts.path, parts.query, parts.fragment))


def _prepare_env() -> dict[str, str]:
    env = os.environ.copy()
    dotenv = _read_dotenv()

    host_map = {"redis": "localhost", "postgres": "localhost"}
    candidates = [
        "APP_REDIS_URL",
        "APP_CELERY_BROKER_URL",
        "APP_CELERY_RESULT_BACKEND",
        "APP_DATABASE_URL",
    ]

    for key in candidates:
        value = env.get(key) or dotenv.get(key)
        if value:
            env[key] = _replace_host_in_url(value, host_map)

    env.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    env.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    return env


def _start_process(cmd: list[str], name: str, env: dict[str, str]) -> subprocess.Popen:
    print(f"[run.py] starting {name}: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def _run_single(cmd: list[str], name: str, env: dict[str, str]) -> int:
    try:
        return subprocess.call(cmd, cwd=str(ROOT), env=env)
    except KeyboardInterrupt:
        return 130


def _stop_processes(processes: list[subprocess.Popen]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    time.sleep(1)
    for proc in processes:
        if proc.poll() is None:
            proc.kill()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AI News Intelligence services without Docker.")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["api", "worker", "beat", "streamlit", "all"],
        default="all",
        help="Service mode to run.",
    )
    parser.add_argument("--host", default=os.getenv("APP_HOST", "0.0.0.0"))
    parser.add_argument("--port", default=os.getenv("APP_PORT", "8000"))
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for API server.")
    parser.add_argument("--worker-concurrency", default="4")
    parser.add_argument("--ui-port", default="8501")
    parser.add_argument("--monitor-interval", default="5", help="Health monitor interval in seconds.")
    parser.add_argument("--with-beat", action="store_true", help="Only used with mode=all.")
    parser.add_argument(
        "--with-ui",
        action="store_true",
        default=True,
        help="Only used with mode=all (enabled by default).",
    )
    parser.add_argument(
        "--no-ui",
        action="store_false",
        dest="with_ui",
        help="Only used with mode=all. Disable Streamlit UI process.",
    )
    return parser


def _health_monitor_loop(base_url: str, interval_seconds: int, stop_event: threading.Event) -> None:
    health_url = f"{base_url.rstrip('/')}/api/v1/health"
    while not stop_event.is_set():
        try:
            with urlopen(health_url, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
                status = payload.get("status")
                db_ok = payload.get("database")
                redis_ok = payload.get("redis")
                print(f"[run.py][health] status={status} database={db_ok} redis={redis_ok}")
        except URLError as exc:
            print(f"[run.py][health] unreachable: {exc}")
        except Exception as exc:
            print(f"[run.py][health] error: {exc}")
        stop_event.wait(interval_seconds)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    process_env = _prepare_env()

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        str(args.host),
        "--port",
        str(args.port),
    ]
    if args.reload:
        api_cmd.append("--reload")

    worker_cmd: list[str] = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.tasks.celery_app.celery_app",
        "worker",
        "--loglevel=INFO",
    ]
    if os.name == "nt":
        worker_cmd.extend(["--pool", "solo"])
    else:
        worker_cmd.extend(["--concurrency", str(args.worker_concurrency)])

    beat_cmd = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.tasks.celery_app.celery_app",
        "beat",
        "--loglevel=INFO",
    ]

    streamlit_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "streamlit_app.py",
        "--server.port",
        str(args.ui_port),
    ]

    if args.mode == "api":
        return _run_single(api_cmd, "api", process_env)
    if args.mode == "worker":
        return _run_single(worker_cmd, "worker", process_env)
    if args.mode == "beat":
        return _run_single(beat_cmd, "beat", process_env)
    if args.mode == "streamlit":
        return _run_single(streamlit_cmd, "streamlit", process_env)

    processes: list[subprocess.Popen] = []
    monitor_stop = threading.Event()
    monitor_thread: threading.Thread | None = None
    try:
        processes.append(_start_process(api_cmd, "api", process_env))
        processes.append(_start_process(worker_cmd, "worker", process_env))
        if args.with_beat:
            processes.append(_start_process(beat_cmd, "beat", process_env))
        if args.with_ui:
            processes.append(_start_process(streamlit_cmd, "streamlit", process_env))

        base_url = f"http://localhost:{args.port}"
        monitor_thread = threading.Thread(
            target=_health_monitor_loop,
            args=(base_url, int(args.monitor_interval), monitor_stop),
            daemon=True,
        )
        monitor_thread.start()

        while True:
            for proc in processes:
                rc = proc.poll()
                if rc is not None:
                    print(f"[run.py] process exited with code {rc}, stopping all.")
                    return rc
            time.sleep(1)
    except KeyboardInterrupt:
        print("[run.py] received interrupt, stopping...")
        return 130
    finally:
        monitor_stop.set()
        if monitor_thread is not None:
            monitor_thread.join(timeout=1)
        _stop_processes(processes)


if __name__ == "__main__":
    if os.name == "nt":
        signal.signal(signal.SIGINT, signal.default_int_handler)
    raise SystemExit(main())
