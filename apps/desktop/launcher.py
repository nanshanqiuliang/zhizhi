"""Desktop launcher for the local sidecar (WORK-2026-033 slice 1).

Starts the FastAPI sidecar on loopback, waits for health, opens the built Web UI
in the system browser, and shuts down cleanly. In a PyInstaller-frozen build the
Web UI and LLM config are bundled under `sys._MEIPASS`; in source runs they are
resolved from the repository root.

Run: `python -m apps.desktop.launcher [--data-root DIR] [--port N] [--no-browser]`
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.request
import webbrowser
from contextlib import suppress
from pathlib import Path

import uvicorn

from apps.api._runtime import ensure_source_paths, runtime_root
from apps.desktop.version import __version__

ensure_source_paths()

from apps.api.ai_draft import build_deepseek_draft_generator  # noqa: E402
from apps.api.answer import build_deepseek_answer_generator  # noqa: E402
from apps.api.command import build_deepseek_command_generator  # noqa: E402
from apps.api.main import create_app  # noqa: E402

_APP_NAME = "知枝"
_HEALTH_TIMEOUT_S = 15.0


def _default_data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / _APP_NAME / "data"


def _wait_for_health(port: int) -> bool:
    deadline = time.monotonic() + _HEALTH_TIMEOUT_S
    url = f"http://127.0.0.1:{port}/api/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.1)
    return False


def _read_lock_port(lock_path: Path) -> int | None:
    """Return the port recorded in a lock file, or None if absent/corrupt."""
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        port = payload.get("port")
        return int(port) if isinstance(port, int) else None
    except (OSError, ValueError, TypeError):
        return None


def _is_running(port: int) -> bool:
    """True when a sidecar on `port` answers our health check."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as response:
            return bool(response.status == 200)
    except OSError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Tree desktop launcher")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=_default_data_root(),
        help="data directory for workspaces (default: %%LOCALAPPDATA%%/知枝/data)",
    )
    parser.add_argument("--port", type=int, default=8000, help="loopback port")
    parser.add_argument("--web-dist", type=Path, default=None, help="built Web UI directory")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args()

    data_root = args.data_root
    try:
        data_root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"无法创建数据目录 {data_root}：{error}", file=sys.stderr)
        raise SystemExit(1) from error

    # Single-instance guard: an exclusive lock file in the data root that
    # records this instance's port. A second launch health-checks that port and
    # fails closed if a sidecar is already answering, so it never races the
    # first instance for the database or the loopback port.
    lock_path = data_root / ".lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        existing_port = _read_lock_port(lock_path)
        if existing_port is None:
            # A racing starter may not have written its port yet; give it a beat.
            time.sleep(0.5)
            existing_port = _read_lock_port(lock_path)
        if existing_port is not None and _is_running(existing_port):
            print(
                f"已有一个 {_APP_NAME} 实例在运行（http://127.0.0.1:{existing_port}/），"
                "本次启动退出。",
                file=sys.stderr,
            )
            raise SystemExit(1) from None
        # Stale lock from a crashed run: take it over.
        with suppress(OSError):
            lock_path.unlink()
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            print("无法获取单实例锁，本次启动退出。", file=sys.stderr)
            raise SystemExit(1) from None
    os.write(lock_fd, json.dumps({"pid": os.getpid(), "port": args.port}).encode("utf-8"))
    os.close(lock_fd)

    try:
        _run(
            data_root=data_root, port=args.port, web_dist=args.web_dist, no_browser=args.no_browser
        )
    finally:
        with suppress(OSError):
            lock_path.unlink()


def _run(*, data_root: Path, port: int, web_dist: Path | None, no_browser: bool) -> None:
    if web_dist is None:
        web_dist = runtime_root() / "web_dist"

    app = create_app(
        data_root=data_root,
        allowed_origins=[],
        draft_generator=build_deepseek_draft_generator(),
        answer_generator=build_deepseek_answer_generator(),
        command_generator=build_deepseek_command_generator(),
        web_dist=web_dist if web_dist.is_dir() else None,
    )

    # asyncio + h11 are pure Python: PyInstaller-friendly and deterministic
    # (avoid uvloop/httptools hidden imports in the frozen build).
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="info", loop="asyncio", http="h11"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not _wait_for_health(port):
        server.should_exit = True
        thread.join(timeout=5)
        print(f"启动失败：127.0.0.1:{port} 未就绪（端口可能被占用）。", file=sys.stderr)
        raise SystemExit(1)

    url = f"http://127.0.0.1:{port}/"
    print(f"{_APP_NAME} {__version__} 已启动：{url}（数据目录：{data_root}）")
    if not no_browser:
        webbrowser.open(url)

    try:
        while thread.is_alive():
            thread.join(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
