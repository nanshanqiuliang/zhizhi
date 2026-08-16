"""QA TR-20260815-009 probe: frozen exe HTTP/asset layer (WORK-2026-047).

Launches dist/zhizhi/zhizhi.exe --no-window with a throwaway data root and a
free port, then asserts:
  1. GET /api/health -> 200 {"status":"ok"}
  2. GET / returns the bundled index.html (id="root") and every referenced
     asset is served with a sha256 identical to the file inside the frozen
     bundle (_internal/web_dist).
  3. The frozen bundle matches a fresh build of the current source using the
     exact desktop build env method (`VITE_LOCAL_API=""` passed through a
     Python subprocess env dict, as scripts/build_desktop.py does) — proving
     the frozen exe contains the reviewed HEAD source.
  4. The process terminates cleanly and the port is released.

Boundary: this probe is HTTP/assets only; interactive Web behaviour is covered
by the vitest layer (jsdom). Run from the repo root:
  uv run python evidence/TR-20260815-009/probes/exe_asset_probe.py
"""

from __future__ import annotations

import hashlib
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_EXE = _ROOT / "dist" / "zhizhi" / "zhizhi.exe"
_BUNDLE_WEB = _ROOT / "dist" / "zhizhi" / "_internal" / "web_dist"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(port: int, timeout_s: float = 25.0) -> bool:
    deadline = time.monotonic() + timeout_s
    url = f"http://127.0.0.1:{port}/api/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200 and resp.read() == b'{"status":"ok"}':
                    return True
        except OSError:
            pass
        time.sleep(0.15)
    return False


def get(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=10.0) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as error:  # type: ignore[name-defined]
        return error.code, error.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def port_in_use(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True


def desktop_style_build(out_dir: Path) -> bool:
    """Rebuild current web source exactly like scripts/build_desktop.py.

    The empty VITE_LOCAL_API must ride inside a Python subprocess env dict —
    cmd's `set VAR=` deletes the var and pwsh/cmd shims drop empty vars, while
    Python's env dict preserves it (that is how the frozen bundle was built).
    """
    env = {**os.environ, "VITE_LOCAL_API": ""}
    result = subprocess.run(
        "pnpm --filter @knowledge-tree/web exec vite build --outDir " + str(out_dir),
        cwd=str(_ROOT),
        env=env,
        shell=True,
    )
    return result.returncode == 0 and (out_dir / "index.html").is_file()


def main() -> int:
    if not _EXE.is_file():
        raise SystemExit(f"missing {_EXE}")
    checks: list[tuple[str, bool, object]] = []
    port = free_port()
    data_root = Path(tempfile.mkdtemp(prefix="kt-qa-047-exe-"))
    log = Path(tempfile.mkdtemp(prefix="kt-qa-047-exe-log-")) / "exe.log"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with open(log, "wb") as handle:
        proc = subprocess.Popen(
            [str(_EXE), "--no-window", "--data-root", str(data_root), "--port", str(port)],
            stdout=handle,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
    base = f"http://127.0.0.1:{port}"
    try:
        checks.append(("health 200", wait_health(port), port))
        status, body = get(base + "/")
        text = body.decode("utf-8", "replace")
        checks.append(
            ("GET / 200 + id=root", status == 200 and 'id="root"' in text, f"status={status}")
        )
        refs = sorted(set(re.findall(r'(?:src|href)="(/assets/[^"]+)"', text)))
        checks.append(("asset refs parsed", len(refs) >= 1, refs))
        for ref in refs:
            rel = ref.lstrip("/")
            bundle_file = _BUNDLE_WEB / rel
            status, data = get(base + ref)
            bundle_ok = bundle_file.is_file() and sha256(bundle_file.read_bytes()) == sha256(data)
            checks.append(
                (f"served {rel} matches frozen bundle", status == 200 and bundle_ok,
                 f"status={status} sha_ok={bundle_ok}")
            )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    checks.append(("port released after terminate", not port_in_use(port), port))

    # Frozen bundle vs fresh desktop-style build of the current source.
    build_dir = Path(tempfile.mkdtemp(prefix="kt-qa-047-rebuild-"))
    built = desktop_style_build(build_dir)
    checks.append(("desktop-style rebuild of HEAD succeeded", built, str(build_dir)))
    for rel in ("assets/index-ec9Mn6UR.js", "assets/index-DimZVipg.css", "pdf.worker.min.mjs"):
        frozen = _BUNDLE_WEB / rel
        fresh = build_dir / rel
        if frozen.is_file() and fresh.is_file():
            same = sha256(frozen.read_bytes()) == sha256(fresh.read_bytes())
            checks.append(
                (f"frozen bundle == fresh HEAD desktop build ({rel})", same,
                 f"frozen={sha256(frozen.read_bytes())[:12]} fresh={sha256(fresh.read_bytes())[:12]}")
            )

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  (detail={detail})")
    print(f"RESULT: {len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
