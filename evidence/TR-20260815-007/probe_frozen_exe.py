"""Frozen desktop exe probes for WORK-2026-046 cap (TR-20260815-007).

Launches dist/zhizhi/zhizhi.exe headless on a free port with a temp data-root
and probes: health, workspace creation, ai-draft fail-closed (no key), the
raised GraphPatch cap (120-op patch accepted => cap=5000 embedded), the
enforced bound (5001-op patch => 422 maxItems), then terminates the process and
verifies the port is released.

Run: uv run python evidence/TR-20260815-007/probe_frozen_exe.py
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXE = ROOT / "dist" / "zhizhi" / "zhizhi.exe"

_results: list[tuple[str, str, str]] = []


def record(probe_id: str, name: str, outcome: str, detail: str = "") -> None:
    _results.append((probe_id, name, outcome))
    print(f"[{outcome}] {probe_id} {name}{(' — ' + detail) if detail else ''}", flush=True)


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


def wait_health(port: int, timeout_s: float = 30.0) -> bool:
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


def request(method: str, url: str, body: object | None = None) -> tuple[int, object]:
    data = None
    headers: dict[str, str] = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        parsed: object
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = raw
        return error.code, parsed


def uuid7ish(counter: int, base: int = 0x00100000) -> str:
    return f"00000000-0000-7000-8000-{(base + counter):012x}"


def create_concept_op(op_index: int, concept_index: int, course_id: str, workspace_id: str) -> dict:
    concept_id = uuid7ish(concept_index)
    return {
        "op_id": uuid7ish(op_index),
        "op": "create_concept",
        "concept": {
            "id": concept_id,
            "course_id": course_id,
            "label": f"冻结探针概念{concept_index:04d}",
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
        },
    }


def build_patch(n_ops: int, workspace_id: str, course_id: str, *, confirmed: bool) -> dict:
    return {
        "schema_version": 1,
        "patch_id": uuid7ish(n_ops + 0x2000),
        "workspace_id": workspace_id,
        "course_id": course_id,
        "base_revision_no": 0,
        "actor": {"type": "user", "id": "local-user"},
        "reason": f"QA TR-20260815-007 冻结探针：{n_ops} 操作补丁",
        "requires_confirmation": True,
        "confirmed": confirmed,
        "operations": [create_concept_op(i, i, course_id, workspace_id) for i in range(n_ops)],
    }


def main() -> int:
    if not EXE.is_file():
        record("EXE-000", "frozen exe present", "FAIL", f"missing {EXE}")
        return 1
    size = EXE.stat().st_size
    record("EXE-000", "frozen exe present", "PASS", f"{EXE.name} {size} bytes")

    port = free_port()
    data_root = Path(tempfile.mkdtemp(prefix="tr007-exe-"))
    log_path = Path(tempfile.mkdtemp(prefix="tr007-exe-log-")) / "exe.log"
    base = f"http://127.0.0.1:{port}"

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with open(log_path, "wb") as log:
        proc = subprocess.Popen(
            [str(EXE), "--no-window", "--data-root", str(data_root), "--port", str(port)],
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )

    try:
        if not wait_health(port):
            record("EXE-001", "GET /api/health -> 200", "FAIL", "sidecar never became healthy")
            return 1
        status, body = request("GET", base + "/api/health")
        ok = status == 200 and isinstance(body, dict) and body.get("status") == "ok"
        record(
            "EXE-001",
            "GET /api/health -> 200",
            "PASS" if ok else "FAIL",
            f"status={status} body={body}",
        )

        status, body = request("POST", base + "/api/workspaces", {"name": "QA-007-冻结探针"})
        ok = status == 200 and isinstance(body, dict) and body.get("id")
        record(
            "EXE-002",
            "POST /api/workspaces -> 200",
            "PASS" if ok else "FAIL",
            f"status={status} body={body}",
        )
        if not ok:
            return 1
        workspace_id = str(body["id"])

        status, body = request("GET", f"{base}/api/workspaces/{workspace_id}/graph")
        if status != 200 or not isinstance(body, dict):
            record("EXE-002b", "GET workspace graph", "FAIL", f"status={status} body={body}")
            return 1
        course_id = str(body["course_id"])
        baseline_concepts = len(body.get("concepts", []))
        record(
            "EXE-002b",
            "GET workspace graph (course_id for patch)",
            "PASS",
            f"course_id={course_id} baseline_concepts={baseline_concepts}",
        )

        # No API key in a fresh data-root: both draft modes must fail closed 503.
        status, body = request("POST", f"{base}/api/workspaces/{workspace_id}/ai-draft", {})
        ok = status == 503 and isinstance(body, dict) and body.get("code") == "ai_not_available"
        record(
            "EXE-003",
            "POST /ai-draft (whole-workspace, no key) -> 503 ai_not_available",
            "PASS" if ok else "FAIL",
            f"status={status} body={body}",
        )

        status, body = request(
            "POST",
            f"{base}/api/workspaces/{workspace_id}/ai-draft",
            {"resource_id": "00000000-0000-7000-8000-000000000999"},
        )
        ok = status == 503 and isinstance(body, dict) and body.get("code") == "ai_not_available"
        record(
            "EXE-003b",
            "POST /ai-draft (single-resource, no key) -> 503 ai_not_available",
            "PASS" if ok else "FAIL",
            f"status={status} body={body}",
        )

        # Cap raised: a 120-op patch (old cap was 100) must be accepted and committed.
        patch120 = build_patch(120, workspace_id, course_id, confirmed=True)
        status, body = request(
            "POST", f"{base}/api/workspaces/{workspace_id}/graph/patches", patch120
        )
        ok = status == 200 and isinstance(body, dict) and body.get("status") == "applied"
        record(
            "EXE-004",
            "120-op patch accepted (cap=5000 embedded, old cap was 100)",
            "PASS" if ok else "FAIL",
            f"status={status} body={body}",
        )

        # Bound still enforced: 5001 ops must fail closed with maxItems.
        patch5001 = build_patch(5001, workspace_id, course_id, confirmed=True)
        status, body = request(
            "POST", f"{base}/api/workspaces/{workspace_id}/graph/patches", patch5001
        )
        rule = body.get("rule") if isinstance(body, dict) else None
        ok = status == 422 and rule == "maxItems"
        record(
            "EXE-005",
            "5001-op patch rejected 422 rule=maxItems (bound enforced)",
            "PASS" if ok else "FAIL",
            f"status={status} body={body}",
        )

        # Graph state after 120-op commit: baseline (seeded root) + 120.
        status, body = request("GET", f"{base}/api/workspaces/{workspace_id}/graph")
        n_concepts = len(body["concepts"]) if isinstance(body, dict) else -1
        ok = status == 200 and n_concepts == baseline_concepts + 120
        revision = body.get("revision_no") if isinstance(body, dict) else "?"
        record(
            "EXE-006",
            "120 concepts persisted after commit",
            "PASS" if ok else "FAIL",
            f"concepts={n_concepts} (baseline {baseline_concepts} + 120) revision_no={revision}",
        )

        return 1 if any(outcome == "FAIL" for _pid, _name, outcome in _results) else 0
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        released = not port_in_use(port)
        record(
            "EXE-007",
            "process terminated and port released",
            "PASS" if released else "FAIL",
            f"port={port} in_use={port_in_use(port)}",
        )


if __name__ == "__main__":
    sys.exit(main())
