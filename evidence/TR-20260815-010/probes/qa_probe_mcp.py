"""QA adversarial probes for WORK-2026-048 built-in MCP server (TR-20260815-010).

Runs against HEAD 944a996. Every check prints `P-XXX PASS/FAIL <detail>`; the
process exits non-zero if any check fails. Nothing here modifies product code;
workspaces are created under a QA temp root and removed at the end.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from copy import deepcopy
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]  # probes -> TR-20260815-010 -> evidence -> repo
for _p in (
    str(REPO),
    str(REPO / "packages" / "contracts-py" / "src"),
    str(REPO / "packages" / "domain" / "src"),
    str(REPO / "packages" / "infrastructure" / "src"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Airtight no-key environment for the whole probe process.
os.environ.pop("DEEPSEEK_API_KEY", None)
CLEAN_ENV = {k: v for k, v in os.environ.items() if k != "DEEPSEEK_API_KEY"}

from knowledge_tree_domain.ai_draft import DraftError  # noqa: E402
from knowledge_tree_infrastructure.workspace import (  # noqa: E402
    WorkspaceLayout,
    create_workspace,
    import_resource,
    migrate,
    save_course_graph,
)
from apps.api.mcp_server import build_mcp_server  # noqa: E402

JsonObject = dict[str, object]
WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
UNKNOWN_WS = "00000000-0000-7000-8000-00000000ffff"

RESULTS: list[tuple[str, bool, str]] = []


def check(pid: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((pid, ok, detail))
    print(f"{pid} {'PASS' if ok else 'FAIL'} {detail}", flush=True)


def empty_graph() -> JsonObject:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }


def seed_workspace(root: Path, with_resource: bool = True) -> str:
    layout = create_workspace(root / WORKSPACE_ID)
    migrate(layout.db_path)
    save_course_graph(layout, empty_graph())
    if with_resource:
        import_resource(layout, display_name="notes.md", content=b"# limit\n\ncontinuity")
    return WORKSPACE_ID


def fake_workspace_draft(texts: list[tuple[str, str]], graph: JsonObject) -> JsonObject:
    """Deterministic offline generator (same shape as the bridge test fixture)."""
    base = int(graph["revision_no"])
    course_id = str(graph["course_id"])
    workspace_id = str(graph["workspace_id"])
    evidence = "00000000-0000-7000-9000-000000000001"
    concept_a = "00000000-0000-7000-8000-000000000101"
    concept_b = "00000000-0000-7000-8000-000000000102"

    def concept(concept_id: str, label: str) -> JsonObject:
        return {
            "id": concept_id,
            "course_id": course_id,
            "label": label,
            "origin": "user",
            "review_state": "accepted",
            "confidence": None,
            "evidence_ids": [evidence],
            "locks": {"content": False, "relations": False, "position": False, "annotations": False},
            "annotations": [],
            "revision_no": 0,
        }

    patch: JsonObject = {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-8000-{base + 1:012d}",
        "workspace_id": workspace_id,
        "course_id": course_id,
        "base_revision_no": base,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "AI 草案：全库思维导图",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-8000-{base + 2:012d}",
                "op": "create_concept",
                "concept": concept(concept_a, "极限"),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 3:012d}",
                "op": "create_concept",
                "concept": concept(concept_b, "连续"),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 4:012d}",
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
                    "id": f"00000000-0000-7000-8000-{base + 5:012d}",
                    "course_id": course_id,
                    "source_concept_id": concept_a,
                    "target_concept_id": concept_b,
                    "edge_type": "prerequisite_of",
                    "origin": "user",
                    "review_state": "accepted",
                    "confidence": None,
                    "evidence_ids": [evidence],
                    "locked": False,
                    "revision_no": 0,
                },
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 6:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": concept_a},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": concept_a,
                    "x": 0.0,
                    "y": 0.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 7:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": concept_b},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": concept_b,
                    "x": 220.0,
                    "y": 0.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
        ],
    }
    return {"draft": {"concepts": [], "relations": []}, "patch": patch}


def call_tool(server: object, tool: str, **kwargs: JsonObject) -> JsonObject:
    manager = server._tool_manager  # type: ignore[attr-defined]  # test-style introspection
    fn = manager.get_tool(tool).fn
    result = fn(**kwargs)
    return result if isinstance(result, dict) else {"ok": True, "result": result}


def history_count(root: Path) -> int:
    layout = create_workspace(root / WORKSPACE_ID)
    with sqlite3.connect(layout.db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM history_records").fetchone()[0])


def make_server(root: Path, **injected: object):
    return build_mcp_server(root, **injected)


def new_root(tag: str) -> Path:
    base = Path(tempfile.gettempdir()) / f"ztree-qa-010-{tag}"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True, exist_ok=True)
    return base


def free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def exe_count() -> int:
    out = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq zhizhi.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
    )
    rows = [r for r in out.stdout.splitlines() if r.strip() and "zhizhi.exe" in r]
    return len(rows)


# ---------------------------------------------------------------- P-001 toolset
def p001() -> None:
    root = new_root("p001")
    server = make_server(
        root,
        workspace_draft_generator=fake_workspace_draft,
        draft_generator=lambda text, rid, graph: fake_workspace_draft([(rid, text)], graph),
    )
    tools = {item.name for item in server._tool_manager.list_tools()}
    exact = tools == {"list_workspaces", "read_workspace", "preview_draft", "validate_patch"}
    forbidden = ("write", "apply", "submit", "commit", "save", "delete", "accept")
    no_write = not any(any(f in t for f in forbidden) for t in tools)
    check("P-001", exact and no_write, f"tools={sorted(tools)} exact4={exact} no_write={no_write}")


# ------------------------------------ P-002 preview_draft single-resource (md)
def p002() -> None:
    root = new_root("p002")
    seed_workspace(root)
    layout = create_workspace(root / WORKSPACE_ID)
    info = import_resource(layout, display_name="notes.md", content=b"# limit\n\ncontinuity")
    seen: dict[str, object] = {}

    def gen(text: str, rid: str, graph: JsonObject) -> JsonObject:
        seen["text"] = text
        seen["rid"] = rid
        return fake_workspace_draft([(rid, text)], graph)

    server = make_server(root, draft_generator=gen, workspace_draft_generator=fake_workspace_draft)
    res = call_tool(server, "preview_draft", workspace_id=WORKSPACE_ID, resource_id=info.id)
    ok = (
        res["ok"] is True
        and res["patch"]["requires_confirmation"] is True
        and res["patch"]["confirmed"] is False
        and isinstance(res["draft"], dict)
    )
    text_ok = seen.get("text") == "# limit\n\ncontinuity" and seen.get("rid") == info.id
    graph = call_tool(server, "read_workspace", workspace_id=WORKSPACE_ID)
    no_write = graph["ok"] is True and graph["graph"]["revision_no"] == 0 and graph["graph"]["concepts"] == []
    check(
        "P-002",
        ok and text_ok and no_write,
        f"ok={ok} gen_saw_text={text_ok} revision_unchanged={no_write} patch_req_conf={res['patch'].get('requires_confirmation')}",
    )


# ------------------------------------------------- P-003 preview_draft no key
def p003() -> None:
    root = new_root("p003")
    seed_workspace(root)
    server = make_server(root)  # no injection, no ai.json, no env key
    r1 = call_tool(server, "preview_draft", workspace_id=WORKSPACE_ID)
    layout = create_workspace(root / WORKSPACE_ID)
    info = import_resource(layout, display_name="notes.md", content=b"# limit\n\ncontinuity")
    r2 = call_tool(server, "preview_draft", workspace_id=WORKSPACE_ID, resource_id=info.id)
    structured = (
        r1.get("ok") is False
        and r1.get("code") == "ai_not_available"
        and r1.get("rule") == "key_required"
        and r2.get("ok") is False
        and r2.get("code") == "ai_not_available"
        and r2.get("rule") == "key_required"
    )
    still_healthy = call_tool(server, "list_workspaces").get("ok") is True
    check(
        "P-003",
        structured and still_healthy,
        f"ws={r1} single={r2} healthy_after={still_healthy}",
    )


# ------------------------------------------ P-004 unknown / corrupt workspace
def p004() -> None:
    root = new_root("p004")
    seed_workspace(root)
    server = make_server(root, workspace_draft_generator=fake_workspace_draft)
    # (a) completely unknown workspace id
    r1 = call_tool(server, "preview_draft", workspace_id=UNKNOWN_WS)
    r2 = call_tool(server, "read_workspace", workspace_id=UNKNOWN_WS)
    r3 = call_tool(server, "validate_patch", workspace_id=UNKNOWN_WS, patch={"x": 1})
    a = (
        r1.get("ok") is False
        and r1.get("code") == "workspace_missing"
        and r2.get("ok") is False
        and r2.get("code") == "workspace_missing"
        and r3.get("ok") is False
        and r3.get("code") == "workspace_missing"
    )
    # (b) UUIDv7 dir exists but no db file
    partial = root / "00000000-0000-7000-8000-000000000003"
    partial.mkdir()
    r4 = call_tool(server, "read_workspace", workspace_id=partial.name)
    b = r4.get("ok") is False and r4.get("code") == "workspace_missing" and r4.get("rule") == "database_file_absent"
    # (c) db exists but no saved graph
    layout = create_workspace(root / "00000000-0000-7000-8000-000000000004")
    migrate(layout.db_path)
    r5 = call_tool(server, "read_workspace", workspace_id=layout.root.name)
    c = r5.get("ok") is False
    check("P-004", a and b and c, f"unknown={r1} no_db={r4} no_graph={r5}")


# ------------------------------------------------- validate_patch all branches
def p005() -> None:
    root = new_root("p005")
    seed_workspace(root)
    server = make_server(root, workspace_draft_generator=fake_workspace_draft)
    draft = call_tool(server, "preview_draft", workspace_id=WORKSPACE_ID)
    patch = draft["patch"]

    # (a) legal draft -> requires_confirmation, no write
    r_a = call_tool(server, "validate_patch", workspace_id=WORKSPACE_ID, patch=patch)
    hist0 = history_count(root)
    graph_a = call_tool(server, "read_workspace", workspace_id=WORKSPACE_ID)
    a = r_a.get("ok") is True and r_a.get("status") == "requires_confirmation" and graph_a["graph"]["revision_no"] == 0 and hist0 == 0

    # (b) confirmed:true user patch -> ready_to_apply, still no write
    p_b = deepcopy(patch)
    p_b["confirmed"] = True
    r_b = call_tool(server, "validate_patch", workspace_id=WORKSPACE_ID, patch=p_b)
    hist_b = history_count(root)
    graph_b = call_tool(server, "read_workspace", workspace_id=WORKSPACE_ID)
    b = r_b.get("ok") is True and r_b.get("status") == "ready_to_apply" and graph_b["graph"]["revision_no"] == 0 and hist_b == 0

    # (c) actor mismatch -> structured fail-closed (record actual code/rule)
    p_c = deepcopy(patch)
    p_c["actor"] = {"type": "user", "id": "attacker"}
    r_c = call_tool(server, "validate_patch", workspace_id=WORKSPACE_ID, patch=p_c)
    c = r_c.get("ok") is False and isinstance(r_c.get("code"), str) and r_c.get("rule") == "actor_context_mismatch"
    p_c2 = deepcopy(patch)
    p_c2["actor"] = {"type": "system", "id": "local-user"}
    r_c2 = call_tool(server, "validate_patch", workspace_id=WORKSPACE_ID, patch=p_c2)
    c2 = r_c2.get("ok") is False and r_c2.get("rule") == "actor_context_mismatch"

    # (d) base_revision conflict
    p_d = deepcopy(patch)
    p_d["base_revision_no"] = 99
    r_d = call_tool(server, "validate_patch", workspace_id=WORKSPACE_ID, patch=p_d)
    d = r_d.get("ok") is False and r_d.get("code") == "patch_invalid" and r_d.get("rule") == "base_revision_mismatch"

    # (e) requires_confirmation=False rejected
    p_e = deepcopy(patch)
    p_e["requires_confirmation"] = False
    r_e = call_tool(server, "validate_patch", workspace_id=WORKSPACE_ID, patch=p_e)
    e = r_e.get("ok") is False and r_e.get("rule") == "confirmation_required"

    check(
        "P-005",
        a and b and c and c2 and d and e,
        f"legal={r_a.get('status')} confirmed_true={r_b.get('status')} actor={r_c} actor2={r_c2} rev_conflict={r_d} conf_false={r_e} hist_after_a={hist0} hist_after_b={hist_b}",
    )


# --------------------------------------------------- P-006 list_workspaces
def p006() -> None:
    root = new_root("p006")
    server = make_server(root)
    r_empty = call_tool(server, "list_workspaces")
    empty_ok = r_empty.get("ok") is True and r_empty.get("workspaces") == []
    # noise that must be ignored
    (root / "notes").mkdir()
    (root / "ai.json").write_text('{"api_key":"sk-no"}', encoding="utf-8")
    r_noise = call_tool(server, "list_workspaces")
    noise_ok = r_noise.get("ok") is True and r_noise.get("workspaces") == []
    seed_workspace(root)
    r_seeded = call_tool(server, "list_workspaces")
    seeded = r_seeded.get("ok") is True and len(r_seeded["workspaces"]) == 1 and r_seeded["workspaces"][0]["id"] == WORKSPACE_ID
    check("P-006", empty_ok and noise_ok and seeded, f"empty={r_empty} noise={r_noise} seeded={r_seeded['workspaces']}")


# ----------------------------------------------------- P-007 PDF single-resource
def p007() -> None:
    root = new_root("p007")
    seed_workspace(root, with_resource=False)
    layout = create_workspace(root / WORKSPACE_ID)
    pdf_bytes = (REPO / "evals" / "calculus-v1" / "source" / "mit-ocw-res-18-001-chapter-02-derivatives.pdf").read_bytes()
    info = import_resource(layout, display_name="book.pdf", content=pdf_bytes)
    seen: dict[str, object] = {}

    def gen(text: str, rid: str, graph: JsonObject) -> JsonObject:
        seen["text"] = text
        seen["rid"] = rid
        return fake_workspace_draft([(rid, text)], graph)

    server = make_server(root, draft_generator=gen, workspace_draft_generator=fake_workspace_draft)
    res = call_tool(server, "preview_draft", workspace_id=WORKSPACE_ID, resource_id=info.id)
    text = str(seen.get("text", ""))
    ok = (
        res.get("ok") is True
        and res["patch"]["requires_confirmation"] is True
        and res["patch"]["confirmed"] is False
        and len(text) > 50
        and "derivative" in text.lower()
    )
    graph = call_tool(server, "read_workspace", workspace_id=WORKSPACE_ID)
    no_write = graph["graph"]["revision_no"] == 0 and graph["graph"]["concepts"] == []
    check(
        "P-007",
        ok and no_write,
        f"ok={ok} pdf_text_len={len(text)} revision_unchanged={no_write} text_head={text[:60]!r}",
    )


# ------------------------------------- P-008/P-009 fail-closed generator paths
def p008_p009() -> None:
    root = new_root("p008")
    seed_workspace(root, with_resource=False)
    server = make_server(root, workspace_draft_generator=fake_workspace_draft)
    r = call_tool(server, "preview_draft", workspace_id=WORKSPACE_ID)
    a = r.get("ok") is False and r.get("code") == "draft_invalid" and r.get("rule") == "no_resources"
    check("P-008", a, f"empty_texts={r}")

    root9 = new_root("p009")
    seed_workspace(root9)

    def bad_gen_no_ops(texts, graph):
        return {"draft": {"concepts": []}, "patch": {"operations": []}}

    def bad_gen_no_patch(texts, graph):
        return {"draft": None}

    def bad_gen_bad_base(texts, graph):
        p = fake_workspace_draft(texts, graph)
        p["patch"]["base_revision_no"] = 99
        return p

    def bad_gen_raises(texts, graph):
        raise DraftError("draft_invalid", details={"rule": "simulated_ai_failure"})

    cases = [
        ("no_new_concepts", bad_gen_no_ops, "no_new_concepts"),
        ("patch_missing", bad_gen_no_patch, "patch_missing"),
        ("defense_base_mismatch", bad_gen_bad_base, "base_revision_mismatch"),
        ("generator_raises", bad_gen_raises, "simulated_ai_failure"),
    ]
    all_ok = True
    details = []
    for tag, gen, expected_rule in cases:
        srv = make_server(root9, workspace_draft_generator=gen)
        res = call_tool(srv, "preview_draft", workspace_id=WORKSPACE_ID)
        good = res.get("ok") is False and res.get("code") == "draft_invalid" and res.get("rule") == expected_rule
        all_ok = all_ok and good
        details.append(f"{tag}={res}")
    check("P-009", all_ok, "; ".join(details))


# ------------------------------------------- P-010 stdio protocol (source)
def p010() -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    root = new_root("p010")
    seed_workspace(root)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "apps.api.mcp_server", "--data-root", str(root)],
        cwd=str(REPO),
        env=CLEAN_ENV,
    )

    async def run() -> None:
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            exact = names == {"list_workspaces", "read_workspace", "preview_draft", "validate_patch"}
            listed = json.loads((await session.call_tool("list_workspaces", {})).content[0].text)
            read_res = json.loads((await session.call_tool("read_workspace", {"workspace_id": WORKSPACE_ID})).content[0].text)
            no_key = json.loads(
                (await session.call_tool("preview_draft", {"workspace_id": WORKSPACE_ID})).content[0].text
            )
            check(
                "P-010",
                exact
                and listed.get("ok") is True
                and len(listed["workspaces"]) == 1
                and read_res.get("ok") is True
                and read_res["graph"]["workspace_id"] == WORKSPACE_ID
                and no_key.get("ok") is False
                and no_key.get("code") == "ai_not_available",
                f"tools={sorted(names)} list={listed} read_ok={read_res.get('ok')} no_key={no_key}",
            )

    asyncio.run(run())


# ------------------------------------------------ P-011 error isolation (stdio)
def p011() -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    root = new_root("p011")
    seed_workspace(root)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "apps.api.mcp_server", "--data-root", str(root)],
        cwd=str(REPO),
        env=CLEAN_ENV,
    )

    async def run() -> None:
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            # failing call: unknown workspace -> structured error, not crash
            err1 = json.loads(
                (await session.call_tool("preview_draft", {"workspace_id": UNKNOWN_WS})).content[0].text
            )
            err2 = json.loads(
                (await session.call_tool("read_workspace", {"workspace_id": UNKNOWN_WS})).content[0].text
            )
            # after failures the session still works
            ok1 = json.loads((await session.call_tool("list_workspaces", {})).content[0].text)
            ok2 = json.loads(
                (await session.call_tool("read_workspace", {"workspace_id": WORKSPACE_ID})).content[0].text
            )
            # argument-level error (missing required arg) also must not kill the session
            bad = await session.call_tool("preview_draft", {})
            ok3 = json.loads((await session.call_tool("list_workspaces", {})).content[0].text)
            check(
                "P-011",
                err1.get("ok") is False
                and err1.get("code") == "workspace_missing"
                and err2.get("ok") is False
                and ok1.get("ok") is True
                and ok2.get("ok") is True
                and len(ok3["workspaces"]) == 1,
                f"err_unknown={err1} err_read={err2} after_ok={ok1['ok']} arg_err_isError={bad.isError} session_alive={ok3['ok']}",
            )

    asyncio.run(run())


# ------------------------------------------------- P-012 sidecar concurrency
def p012() -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    root = new_root("p012")
    seed_workspace(root)
    port = free_port()
    exe = REPO / "dist" / "zhizhi" / "zhizhi.exe"
    log_path = REPO / "evidence" / "TR-20260815-010" / "logs" / "sidecar-app.log"
    proc = subprocess.Popen(
        [str(exe), "--no-window", "--data-root", str(root), "--port", str(port)],
        stdout=open(log_path, "wb"),
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 40
        healthy = False
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.0) as resp:
                    if resp.status == 200:
                        healthy = True
                        break
            except OSError:
                time.sleep(0.3)
        if not healthy:
            check("P-012", False, f"sidecar health never OK (proc={proc.poll()})")
            return
        # app side: workspaces endpoint returns {"workspaces": [...]}
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/workspaces", timeout=5) as resp:
            app_payload = json.loads(resp.read().decode("utf-8"))
        app_ws = app_payload.get("workspaces", []) if isinstance(app_payload, dict) else app_payload
        # MCP stdio client on the SAME data root while the app runs
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "apps.api.mcp_server", "--data-root", str(root)],
            cwd=str(REPO),
            env=CLEAN_ENV,
        )

        async def run() -> None:
            async with (
                stdio_client(params) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                listed = json.loads((await session.call_tool("list_workspaces", {})).content[0].text)
                read_res = json.loads(
                    (await session.call_tool("read_workspace", {"workspace_id": WORKSPACE_ID})).content[0].text
                )
                return listed, read_res

        listed, read_res = asyncio.run(run())
        app_ids = [w["id"] for w in app_ws] if isinstance(app_ws, list) else []
        ok = (
            healthy
            and listed.get("ok") is True
            and len(listed["workspaces"]) == 1
            and read_res.get("ok") is True
            and read_res["graph"]["workspace_id"] == WORKSPACE_ID
            and WORKSPACE_ID in app_ids
        )
        check(
            "P-012",
            ok,
            f"sidecar_healthy={healthy} app_workspaces={app_ids} mcp_list={listed['workspaces']} mcp_read_ok={read_res['ok']}",
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
    # port must be released after exit
    released = True
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.0)
        released = False
    except OSError:
        pass
    check("P-012b", released and proc.poll() is not None, f"port_released={released} proc_exited={proc.poll() is not None}")


# ------------------------------------------------ P-013 frozen exe --mcp-stdio
def p013() -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    root = new_root("p013")
    exe = REPO / "dist" / "zhizhi" / "zhizhi.exe"
    before = exe_count()
    params = StdioServerParameters(
        command=str(exe),
        args=["--mcp-stdio", "--data-root", str(root)],
        env=CLEAN_ENV,
    )

    async def run() -> None:
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            exact4 = names == {"list_workspaces", "read_workspace", "preview_draft", "validate_patch"}
            empty_list = json.loads((await session.call_tool("list_workspaces", {})).content[0].text)
            pre_seed_no_key = json.loads(
                (await session.call_tool("preview_draft", {"workspace_id": WORKSPACE_ID})).content[0].text
            )  # workspace absent -> must fail closed (workspace_missing), not crash
            # seed a workspace WHILE the frozen server session is live
            seed_workspace(root)
            after_seed = json.loads((await session.call_tool("list_workspaces", {})).content[0].text)
            read_res = json.loads(
                (await session.call_tool("read_workspace", {"workspace_id": WORKSPACE_ID})).content[0].text
            )
            # now the workspace exists but there is no AI key -> ai_not_available
            no_key = json.loads(
                (await session.call_tool("preview_draft", {"workspace_id": WORKSPACE_ID})).content[0].text
            )
            during = exe_count()
            return {
                "exact4": exact4,
                "empty_list": empty_list,
                "pre_seed_no_key": pre_seed_no_key,
                "no_key": no_key,
                "after_seed": after_seed,
                "read_res": read_res,
                "during": during,
            }

    try:
        res = asyncio.run(run())
    finally:
        time.sleep(2.0)
    after = exe_count()
    ok = (
        res["exact4"]
        and res["empty_list"].get("ok") is True
        and res["empty_list"]["workspaces"] == []
        and res["pre_seed_no_key"].get("ok") is False
        and res["pre_seed_no_key"].get("code") == "workspace_missing"
        and res["no_key"].get("ok") is False
        and res["no_key"].get("code") == "ai_not_available"
        and res["after_seed"].get("ok") is True
        and len(res["after_seed"]["workspaces"]) == 1
        and res["read_res"].get("ok") is True
        and res["read_res"]["graph"]["workspace_id"] == WORKSPACE_ID
        and res["during"] >= before + 1
        and after <= before
    )
    check(
        "P-013",
        ok,
        f"exact4={res['exact4']} empty={res['empty_list']} pre_seed_no_key={res['pre_seed_no_key']} no_key={res['no_key']} seeded={res['after_seed']['workspaces']} read_ok={res['read_res']['ok']} exe_procs before={before} during={res['during']} after={after}",
    )


# ----------------------------------------------------- P-014 source entry help
def p014() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "apps.api.mcp_server", "--help"],
        cwd=str(REPO),
        env=CLEAN_ENV,
        capture_output=True,
        text=True,
        timeout=30,
    )
    ok = out.returncode == 0 and "--data-root" in out.stdout
    check("P-014", ok, f"exit={out.returncode} has_data_root_flag={ok} stdout={out.stdout.strip()[:120]!r}")


def main() -> None:
    print(f"QA probe run: repo={REPO} python={sys.version.split()[0]} env_key_absent={os.environ.get('DEEPSEEK_API_KEY') is None}")
    p001()
    p002()
    p003()
    p004()
    p005()
    p006()
    p007()
    p008_p009()
    p010()
    p011()
    p012()
    p013()
    p014()
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n=== SUMMARY: {len(RESULTS) - len(failed)}/{len(RESULTS)} PASS ===")
    for pid, ok, detail in RESULTS:
        print(f"{pid} {'PASS' if ok else 'FAIL'} {detail}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
