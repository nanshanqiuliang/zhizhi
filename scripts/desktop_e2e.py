"""End-to-end smoke for the frozen Windows desktop bundle (WORK-2026-033 slice 1).

Launches `dist/zhizhi/zhizhi.exe` and asserts: loopback health, same-origin UI
serving, data-directory creation, single-instance fail-closed, graph PUT/GET
round trip, resource import, AI-draft fail-closed (no key), patch + undo, stale
lock takeover after a hard kill, and port release. Requires the bundle built by
`scripts/build_desktop.py`.

Run from the repository root: `uv run python scripts/desktop_e2e.py`
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EXE = _ROOT / "dist" / "zhizhi" / "zhizhi.exe"

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
CONCEPT_A = "00000000-0000-7000-8000-000000000005"
CONCEPT_B = "00000000-0000-7000-8000-000000000006"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(port: int, timeout_s: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout_s
    url = f"http://127.0.0.1:{port}/api/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.15)
    return False


def port_in_use(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True


def request(
    method: str,
    url: str,
    *,
    body: dict[str, object] | bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, str, object]:
    data = None
    outgoing = dict(headers or {})
    if isinstance(body, dict):
        data = json.dumps(body).encode("utf-8")
        outgoing["Content-Type"] = "application/json"
    elif body is not None:
        data = body
    req = urllib.request.Request(url, data=data, method=method, headers=outgoing)
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), resp.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace"), error.headers


def spawn(args: list[str], log_path: Path) -> subprocess.Popen[bytes]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with open(log_path, "wb") as log:
        return subprocess.Popen(
            [str(_EXE), *args],
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )


def graph_payload() -> dict[str, object]:
    def concept(cid: str, label: str) -> dict[str, object]:
        return {
            "id": cid,
            "course_id": COURSE_ID,
            "label": label,
            "origin": "user",
            "review_state": "accepted",
            "confidence": None,
            "evidence_ids": [],
            "locks": {
                "content": False,
                "relations": False,
                "position": False,
                "annotations": False,
            },
            "annotations": [],
            "revision_no": 0,
        }

    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [concept(CONCEPT_A, "极限"), concept(CONCEPT_B, "连续")],
        "edges": [],
        "layout_items": [],
    }


def create_edge_patch() -> dict[str, object]:
    return {
        "schema_version": 1,
        "patch_id": "00000000-0000-7000-8000-000000000007",
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": 0,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "补充先修关系",
        "requires_confirmation": True,
        "confirmed": True,
        "operations": [
            {
                "op_id": "00000000-0000-7000-8000-000000000008",
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
                    "id": "00000000-0000-7000-8000-000000000009",
                    "course_id": COURSE_ID,
                    "source_concept_id": CONCEPT_A,
                    "target_concept_id": CONCEPT_B,
                    "edge_type": "prerequisite_of",
                    "origin": "user",
                    "review_state": "accepted",
                    "confidence": None,
                    "evidence_ids": [],
                    "locked": False,
                    "revision_no": 0,
                },
            }
        ],
    }


def multipart_file_body(filename: str, content: str, mime: str) -> tuple[bytes, str]:
    boundary = "----kt-e2e-" + os.urandom(8).hex()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
        f"{content}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    return body, f"multipart/form-data; boundary={boundary}"


def main() -> None:
    if not _EXE.is_file():
        raise SystemExit(f"missing {_EXE}; run `uv run python scripts/build_desktop.py` first")

    port = free_port()
    data_root = Path(tempfile.mkdtemp(prefix="kt-e2e-"))
    log_dir = Path(tempfile.mkdtemp(prefix="kt-e2e-log-"))
    base = f"http://127.0.0.1:{port}"
    ws = f"{base}/api/workspaces/{WORKSPACE_ID}"

    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))

    proc_a = spawn(
        ["--no-window", "--data-root", str(data_root), "--port", str(port)], log_dir / "a.log"
    )
    try:
        check("health", wait_health(port), "sidecar became healthy")
        status, text, _ = request("GET", base + "/")
        check("ui-index", status == 200 and 'id="root"' in text, f"GET / -> {status}")

        check("data-dir", data_root.is_dir() and (data_root / ".lock").is_file(), "data dir + lock")

        status, _, _ = request("PUT", ws + "/graph", body=graph_payload())
        check("graph-put", status == 200, f"PUT /graph -> {status}")

        status, text, _ = request("GET", ws + "/graph")
        loaded = json.loads(text) if status == 200 else {}
        labels = [c.get("label") for c in loaded.get("concepts", [])]
        check(
            "graph-get", status == 200 and labels == ["极限", "连续"], f"GET /graph labels={labels}"
        )

        status, _, _ = request("POST", ws + "/graph/patches", body=create_edge_patch())
        check("patch-apply", status == 200, f"POST /graph/patches -> {status}")

        status, _, _ = request("POST", ws + "/graph/undo")
        check("patch-undo", status == 200, f"POST /graph/undo -> {status}")

        status, text, _ = request("GET", ws + "/graph")
        loaded = json.loads(text) if status == 200 else {}
        check("undo-reverted", status == 200 and loaded.get("edges") == [], "edges reverted")

        body, ctype = multipart_file_body(
            "note.md", "# 极限\n极限是微积分的基础。\n", "text/markdown"
        )
        status, text, _ = request(
            "POST", ws + "/resources", body=body, headers={"Content-Type": ctype}
        )
        rid = json.loads(text).get("id") if status == 200 else None
        check("resource-import", status == 200 and bool(rid), f"POST /resources -> {status}")

        status, text, _ = request("POST", ws + "/ai-draft", body={"resource_id": rid or ""})
        code = json.loads(text).get("code") if text else None
        check(
            "ai-draft-fail-closed",
            status == 503 and code == "ai_not_available",
            f"/ai-draft -> {status} {code}",
        )

        proc_b = spawn(
            ["--no-window", "--data-root", str(data_root), "--port", str(free_port())],
            log_dir / "b.log",
        )
        rc_b = proc_b.wait(timeout=30)
        check("single-instance", rc_b == 1, f"second instance exit code {rc_b} (expect 1)")
        check("instance-a-alive", wait_health(port), "first instance still healthy")
    finally:
        proc_a.terminate()
        try:
            proc_a.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc_a.kill()

    check("port-released", not port_in_use(port), "loopback port released after terminate")

    proc_c = spawn(
        ["--no-window", "--data-root", str(data_root), "--port", str(port)], log_dir / "c.log"
    )
    try:
        check("stale-lock-takeover", wait_health(port), "new instance took over stale lock")
    finally:
        proc_c.terminate()
        try:
            proc_c.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc_c.kill()
    check("port-released-again", not port_in_use(port), "port released again")

    # Window-mode smoke: the frozen exe should open a native WebView2 window and
    # enter its GUI loop without crashing. We cannot assert the window visually,
    # but we assert the process stays alive and keeps serving the sidecar.
    w_data = Path(tempfile.mkdtemp(prefix="kt-e2e-win-"))
    w_port = free_port()
    proc_w = spawn(["--data-root", str(w_data), "--port", str(w_port)], log_dir / "w.log")
    try:
        check("window-health", wait_health(w_port), "windowed exe serves sidecar")
        time.sleep(2)
        check("window-process-alive", proc_w.poll() is None, "windowed exe running (GUI loop)")
    finally:
        proc_w.terminate()
        try:
            proc_w.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc_w.kill()
    check("window-port-released", not port_in_use(w_port), "windowed exe port released")

    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    failed = [r for r in results if not r[1]]
    if failed:
        print(f"\n{len(failed)}/{len(results)} checks failed", file=sys.stderr)
        raise SystemExit(1)
    print(f"\n{len(results)}/{len(results)} checks passed")


if __name__ == "__main__":
    main()
