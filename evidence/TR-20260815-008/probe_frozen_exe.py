"""Frozen-exe probes for WORK-2026-045 (TR-20260815-008).

Launches `dist/zhizhi/zhizhi.exe` (rebuilt 2026-08-16 12:56:54) and asserts:
  EXE-001 health 200
  EXE-002 GET / serves index.html
  EXE-003 the index.html asset references resolve inside the frozen bundle
  EXE-004 served asset bytes == embedded frozen-bundle asset bytes (hash match)
  EXE-005 frozen bundle contains the unbounded-canvas implementation markers
  EXE-006 process terminated and port released

Boundary (recorded): canvas drag/zoom behavior itself is Web-only and is
verified by the vitest probe suite; the frozen exe is probed at the HTTP/asset
level only (no browser automation, no API key needed).
"""

from __future__ import annotations

import hashlib
import re
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_EXE = _ROOT / "dist" / "zhizhi" / "zhizhi.exe"
_EMBEDDED_WEB = _ROOT / "dist" / "zhizhi" / "_internal" / "web_dist"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def port_in_use(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True


def wait_health(port: int, timeout_s: float = 25.0) -> bool:
    deadline = time.monotonic() + timeout_s
    url = f"http://127.0.0.1:{port}/api/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.2)
    return False


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    if not _EXE.is_file():
        print(f"missing frozen exe: {_EXE}")
        return 2

    port = free_port()
    data_root = Path(tempfile.mkdtemp(prefix="kt-tr008-exe-"))
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        [str(_EXE), "--no-window", "--data-root", str(data_root), "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        check("EXE-001 health", wait_health(port), f"GET {base}/api/health -> 200")
        if not wait_health(port):
            print("sidecar never became healthy; aborting")
            return 2

        with urllib.request.urlopen(base + "/", timeout=5.0) as resp:
            index_html = resp.read().decode("utf-8", "replace")
        check(
            "EXE-002 index.html",
            resp.status == 200 and 'id="root"' in index_html and "<title>" in index_html,
            f"GET / -> {resp.status}, has #root",
        )

        refs = re.findall(r'(?:src|href)="(/assets/[^"]+)"', index_html)
        check("EXE-003 asset refs", len(refs) >= 2, f"refs={sorted(refs)}")

        all_match = True
        detail_parts: list[str] = []
        for ref in sorted(refs):
            rel = ref.lstrip("/")
            embedded = _EMBEDDED_WEB / rel
            if not embedded.is_file():
                all_match = False
                detail_parts.append(f"{rel}: NOT in frozen bundle")
                continue
            with urllib.request.urlopen(base + ref, timeout=10.0) as resp:
                served = resp.read()
            served_ok = resp.status == 200
            embedded_bytes = embedded.read_bytes()
            hash_ok = sha256_bytes(served) == sha256_bytes(embedded_bytes)
            detail_parts.append(
                f"{rel}: status={resp.status} served_sha={sha256_bytes(served)[:12]} "
                f"embedded_sha={sha256_bytes(embedded_bytes)[:12]} match={hash_ok}"
            )
            if not (served_ok and hash_ok):
                all_match = False
        check("EXE-004 served==embedded hashes", all_match, "; ".join(detail_parts))

        # Implementation markers inside the frozen JS bundle (WORK-2026-045):
        # old 835/555 clamps must be gone; the 8px floor must remain.
        js_files = sorted((_EMBEDDED_WEB / "assets").glob("index-*.js"))
        marker_ok = True
        marker_parts: list[str] = []
        for js in js_files:
            text = js.read_text(encoding="utf-8", errors="replace")
            has_old_clamp = "Math.min(835," in text or "Math.min(555," in text
            has_floor = "Math.max(8," in text
            has_canvas_surface = "canvas-surface" in text
            marker_parts.append(
                f"{js.name}: old_clamp={has_old_clamp} floor8={has_floor} "
                f"canvas-surface={has_canvas_surface}"
            )
            if has_old_clamp or not has_floor or not has_canvas_surface:
                marker_ok = False
        check("EXE-005 impl markers", marker_ok, "; ".join(marker_parts))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    check("EXE-006 port released", not port_in_use(port), f"port {port} free after terminate")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} frozen-exe probes passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
