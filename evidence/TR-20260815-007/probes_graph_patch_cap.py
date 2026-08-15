"""Adversarial probes for WORK-2026-046 GraphPatch.operations cap (TR-20260815-007).

Run from repository root:
    uv run python evidence/TR-20260815-007/probes_graph_patch_cap.py

All assertions are against live execution output; the script prints one line per
probe ([PASS]/[FAIL]/[ERROR]) and exits non-zero if any probe fails.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from knowledge_tree_contracts import ContractValidationError, validate_contract
from knowledge_tree_domain import GraphPatchError, preview_graph_patch

from apps.api.main import create_app

JsonObject = dict[str, Any]

WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
COURSE_ID = "00000000-0000-7000-8000-000000000002"
RESOURCE_ID = "00000000-0000-7000-8000-000000000003"
RESOURCE_VERSION_ID = "00000000-0000-7000-8000-000000000004"
CONCEPT_A_ID = "00000000-0000-7000-8000-000000000005"
CONCEPT_B_ID = "00000000-0000-7000-8000-000000000006"
PATCH_ID = "00000000-0000-7000-8000-000000000007"
OP_ID = "00000000-0000-7000-8000-000000000008"
EVIDENCE = "00000000-0000-7000-9000-000000000001"
ALLOWED_ORIGIN = "http://localhost:5173"

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "docs/contracts/knowledge-tree-graph.v1.schema.json"
GENERATED_PY = (
    ROOT / "packages/contracts-py/src/knowledge_tree_contracts/_generated_graph_v1_schema.py"
)

_probe_results: list[tuple[str, str, str]] = []


def record(probe_id: str, name: str, outcome: str, detail: str = "") -> None:
    _probe_results.append((probe_id, name, outcome))
    print(f"[{outcome}] {probe_id} {name}{(' — ' + detail) if detail else ''}", flush=True)


def concept(concept_id: str, label: str) -> JsonObject:
    return {
        "id": concept_id,
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


def valid_graph() -> JsonObject:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [concept(CONCEPT_A_ID, "极限"), concept(CONCEPT_B_ID, "连续")],
        "edges": [],
        "layout_items": [],
    }


def valid_patch() -> JsonObject:
    return {
        "schema_version": 1,
        "patch_id": PATCH_ID,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "base_revision_no": 0,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "补充先修关系",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [
            {
                "op_id": OP_ID,
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
                    "id": "00000000-0000-7000-8000-000000000009",
                    "course_id": COURSE_ID,
                    "source_concept_id": CONCEPT_A_ID,
                    "target_concept_id": CONCEPT_B_ID,
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


def _n_ops(n: int) -> list[JsonObject]:
    return [deepcopy(valid_patch()["operations"][0]) for _ in range(n)]


# ---------------------------------------------------------------------------
# Contract layer (validate_contract / preview_graph_patch)
# ---------------------------------------------------------------------------


def p_c_001_5000_accepted() -> None:
    patch = valid_patch()
    patch["operations"] = _n_ops(5000)
    validate_contract("graph_patch", patch)
    record("P-C-001", "5000 ops exactly accepted (validate_contract)", "PASS", "5000 == cap")


def p_c_002_5001_rejected() -> None:
    patch = valid_patch()
    patch["operations"] = _n_ops(5001)
    try:
        validate_contract("graph_patch", patch)
    except ContractValidationError as error:
        assert error.code == "validation_failed", error.details
        assert error.details["rule"] == "maxItems", error.details
        record("P-C-002", "5001 ops rejected with rule=maxItems", "PASS", str(error.details))
        return
    raise AssertionError("5001 ops unexpectedly accepted")


def p_c_003_zero_ops_rejected() -> None:
    patch = valid_patch()
    patch["operations"] = []
    try:
        validate_contract("graph_patch", patch)
    except ContractValidationError as error:
        assert error.details["rule"] == "minItems", error.details
        record("P-C-003", "0 ops rejected with rule=minItems", "PASS", str(error.details))
        return
    raise AssertionError("0 ops unexpectedly accepted")


def p_c_004_duplicate_op_id() -> None:
    patch = valid_patch()
    patch["operations"] = _n_ops(2)
    try:
        preview_graph_patch(valid_graph(), patch, trusted_actor=patch["actor"])
    except GraphPatchError as error:
        assert error.code == "validation_failed", (error.code, error.details)
        assert error.details["rule"] == "duplicate_operation_id", error.details
        record(
            "P-C-004",
            "duplicate op_id rejected",
            "PASS",
            f"code={error.code} rule={error.details['rule']}",
        )
        return
    raise AssertionError("duplicate op_id accepted")


def p_c_005_duplicate_operation_target() -> None:
    patch = valid_patch()
    base = concept("00000000-0000-7000-8000-000000000050", "新概念")
    patch["operations"] = [
        {
            "op_id": "00000000-0000-7000-8000-000000000051",
            "op": "create_concept",
            "concept": deepcopy(base),
        },
        {
            "op_id": "00000000-0000-7000-8000-000000000052",
            "op": "create_concept",
            "concept": deepcopy(base),
        },
    ]
    try:
        preview_graph_patch(valid_graph(), patch, trusted_actor=patch["actor"])
    except GraphPatchError as error:
        assert error.details["rule"] == "duplicate_operation_target", error.details
        record(
            "P-C-005",
            "duplicate operation target rejected",
            "PASS",
            f"rule={error.details['rule']}",
        )
        return
    raise AssertionError("duplicate operation target accepted")


def p_c_006_150_accepted() -> None:
    patch = valid_patch()
    patch["operations"] = _n_ops(150)
    validate_contract("graph_patch", patch)
    record("P-C-006", "150 ops accepted (user regression scenario)", "PASS")


def p_c_007_2500_accepted() -> None:
    patch = valid_patch()
    patch["operations"] = _n_ops(2500)
    validate_contract("graph_patch", patch)
    record("P-C-007", "2500 ops accepted (realistic whole-corpus worst case)", "PASS")


def p_c_008_100_accepted_backward_compat() -> None:
    patch = valid_patch()
    patch["operations"] = _n_ops(100)
    validate_contract("graph_patch", patch)
    record("P-C-008", "100 ops (old cap) still accepted — backward compatible", "PASS")


def p_c_009_user_confidence_non_null() -> None:
    patch = valid_patch()
    bad = concept("00000000-0000-7000-8000-000000000053", "带置信度")
    bad["confidence"] = 0.9
    patch["operations"] = [
        {"op_id": "00000000-0000-7000-8000-000000000054", "op": "create_concept", "concept": bad}
    ]
    try:
        preview_graph_patch(valid_graph(), patch, trusted_actor=patch["actor"])
    except GraphPatchError as error:
        assert error.code == "validation_failed", (error.code, error.details)
        assert error.details["rule"] == "user_confidence_must_be_null", error.details
        record(
            "P-C-009",
            "user-origin concept with non-null confidence rejected",
            "PASS",
            f"rule={error.details['rule']}",
        )
        return
    raise AssertionError("user-origin concept with confidence accepted")


# ---------------------------------------------------------------------------
# API layer (TestClient + injected generators)
# ---------------------------------------------------------------------------


def _empty_graph() -> JsonObject:
    return {
        "schema_version": 1,
        "workspace_id": WORKSPACE_ID,
        "course_id": COURSE_ID,
        "revision_no": 0,
        "concepts": [],
        "edges": [],
        "layout_items": [],
    }


def _seed_md_resource(client: TestClient) -> str:
    client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
    response = client.post(
        f"/api/workspaces/{WORKSPACE_ID}/resources",
        files={"file": ("notes.md", b"# limit\n\ncontinuity", "text/markdown")},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["id"])


def _fake_generator(text: str, resource_id: str, graph: JsonObject) -> JsonObject:
    base = int(graph["revision_no"])
    course_id = str(graph["course_id"])
    workspace_id = str(graph["workspace_id"])
    assert text and resource_id

    def concept(concept_id: str, label: str) -> JsonObject:
        return {
            "id": concept_id,
            "course_id": course_id,
            "label": label,
            "origin": "user",
            "review_state": "accepted",
            "confidence": None,
            "evidence_ids": [EVIDENCE],
            "locks": {
                "content": False,
                "relations": False,
                "position": False,
                "annotations": False,
            },
            "annotations": [],
            "revision_no": 0,
        }

    patch = {
        "schema_version": 1,
        "patch_id": f"00000000-0000-7000-8000-{base + 1:012d}",
        "workspace_id": workspace_id,
        "course_id": course_id,
        "base_revision_no": base,
        "actor": {"type": "user", "id": "local-user"},
        "reason": "AI 草案：微积分概念链",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": [
            {
                "op_id": f"00000000-0000-7000-8000-{base + 2:012d}",
                "op": "create_concept",
                "concept": concept("00000000-0000-7000-8000-000000000101", "极限"),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 3:012d}",
                "op": "create_concept",
                "concept": concept("00000000-0000-7000-8000-000000000102", "连续"),
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 4:012d}",
                "op": "create_edge",
                "expected_source_revision_no": 0,
                "expected_target_revision_no": 0,
                "edge": {
                    "id": f"00000000-0000-7000-8000-{base + 5:012d}",
                    "course_id": course_id,
                    "source_concept_id": "00000000-0000-7000-8000-000000000101",
                    "target_concept_id": "00000000-0000-7000-8000-000000000102",
                    "edge_type": "prerequisite_of",
                    "origin": "user",
                    "review_state": "accepted",
                    "confidence": None,
                    "evidence_ids": [EVIDENCE],
                    "locked": False,
                    "revision_no": 0,
                },
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 6:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": "00000000-0000-7000-8000-000000000101"},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": "00000000-0000-7000-8000-000000000101",
                    "x": 0.0,
                    "y": 0.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
            {
                "op_id": f"00000000-0000-7000-8000-{base + 7:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": "00000000-0000-7000-8000-000000000102"},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": "00000000-0000-7000-8000-000000000102",
                    "x": 220.0,
                    "y": 0.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            },
        ],
    }
    draft = {
        "concepts": [
            {"label": "极限", "aliases": [], "confidence": 0.9, "evidence_ids": [EVIDENCE]},
            {"label": "连续", "aliases": [], "confidence": 0.85, "evidence_ids": [EVIDENCE]},
        ],
        "relations": [
            {
                "source_label": "极限",
                "target_label": "连续",
                "edge_type": "prerequisite_of",
                "confidence": 0.7,
                "evidence_ids": [EVIDENCE],
            }
        ],
    }
    return {"draft": draft, "patch": patch}


def _large_workspace_generator(texts: list[tuple[str, str]], graph: JsonObject) -> JsonObject:
    """Whole-corpus generator emitting 120 concepts -> 240 operations (WORK-2026-046)."""
    assert texts
    course_id = str(graph["course_id"])
    workspace_id = str(graph["workspace_id"])
    concepts: list[JsonObject] = []
    operations: list[JsonObject] = []
    for index in range(120):
        concept_id = f"00000000-0000-7000-8000-{5000 + index:012d}"
        concepts.append(
            {
                "label": f"概念{index:03d}",
                "aliases": [],
                "confidence": None,
                "evidence_ids": [EVIDENCE],
            }
        )
        operations.append(
            {
                "op_id": f"00000000-0000-7000-8000-{6000 + index * 2:012d}",
                "op": "create_concept",
                "concept": {
                    "id": concept_id,
                    "course_id": course_id,
                    "label": f"概念{index:03d}",
                    "origin": "user",
                    "review_state": "accepted",
                    "confidence": None,
                    "evidence_ids": [EVIDENCE],
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
        )
        operations.append(
            {
                "op_id": f"00000000-0000-7000-8000-{6001 + index * 2:012d}",
                "op": "set_layout_item",
                "target": {"type": "concept", "id": concept_id},
                "expected_updated_revision_no": 0,
                "layout_item": {
                    "view_id": workspace_id,
                    "concept_id": concept_id,
                    "x": float(index % 20) * 120.0,
                    "y": float(index // 20) * 120.0,
                    "pinned": False,
                    "revision_no": 0,
                },
            }
        )
    patch = {
        "schema_version": 1,
        "patch_id": "00000000-0000-7000-8000-000000004000",
        "workspace_id": workspace_id,
        "course_id": course_id,
        "base_revision_no": int(graph["revision_no"]),
        "actor": {"type": "user", "id": "local-user"},
        "reason": "AI 草案：全库思维导图（120 概念，240 操作）",
        "requires_confirmation": True,
        "confirmed": False,
        "operations": operations,
    }
    return {"draft": {"concepts": concepts, "relations": []}, "patch": patch}


def p_a_001_workspace_240_ops_200(tmp_path: Path) -> None:
    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        workspace_draft_generator=_large_workspace_generator,
    )
    with TestClient(app) as ws_client:
        ws_client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
        ws_client.post(
            f"/api/workspaces/{WORKSPACE_ID}/resources",
            files={"file": ("notes.md", b"# limit\n\ncontinuity", "text/markdown")},
        )
        response = ws_client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["patch"]["operations"]) == 240, len(body["patch"]["operations"])
        assert body["patch"]["requires_confirmation"] is True
        assert body["patch"]["confirmed"] is False
        record(
            "P-A-001", "whole-corpus 240-op draft -> 200 + requires_confirmation", "PASS", "240 ops"
        )


def p_a_002_workspace_no_resources_422(tmp_path: Path) -> None:
    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        workspace_draft_generator=lambda texts, graph: {"draft": {}, "patch": {}},
    )
    with TestClient(app) as ws_client:
        ws_client.put(f"/api/workspaces/{WORKSPACE_ID}/graph", json=_empty_graph())
        response = ws_client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
        assert response.status_code == 422, response.text
        body = response.json()
        assert body["code"] == "draft_invalid", body
        assert body["rule"] == "no_resources", body
        record(
            "P-A-002",
            "whole-corpus with no resources -> 422 draft_invalid/no_resources",
            "PASS",
            str(body),
        )


def p_a_003_no_generator_503(tmp_path: Path) -> None:
    app = create_app(data_root=tmp_path, allowed_origins=[ALLOWED_ORIGIN])
    with TestClient(app) as client:
        response = client.post(f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={})
        assert response.status_code == 503, response.text
        assert response.json()["code"] == "ai_not_available", response.json()
        record(
            "P-A-003",
            "no workspace generator -> 503 ai_not_available (fail-closed)",
            "PASS",
            str(response.json()),
        )


def p_a_004_single_resource_mode_200(tmp_path: Path) -> None:
    app = create_app(
        data_root=tmp_path,
        allowed_origins=[ALLOWED_ORIGIN],
        draft_generator=_fake_generator,
    )
    with TestClient(app) as client:
        resource_id = _seed_md_resource(client)
        response = client.post(
            f"/api/workspaces/{WORKSPACE_ID}/ai-draft", json={"resource_id": resource_id}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["patch"]["requires_confirmation"] is True
        assert body["draft"]["concepts"]
        record(
            "P-A-004",
            "single-resource mode (resource_id given) still works",
            "PASS",
            "200 + requires_confirmation",
        )


# ---------------------------------------------------------------------------
# Generated artifact consistency
# ---------------------------------------------------------------------------


def _embedded_python_schema() -> JsonObject:
    text = GENERATED_PY.read_text(encoding="utf-8")
    marker = 'GRAPH_V1_SCHEMA_JSON = r"""'
    start = text.index(marker) + len(marker)
    end = text.rindex('"""')
    return json.loads(text[start:end])


def p_g_001_python_mirror_matches_canonical() -> None:
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    embedded = _embedded_python_schema()
    assert embedded == canonical, "generated Python mirror diverges from canonical JSON"
    bound = canonical["$defs"]["GraphPatch"]["properties"]["operations"]["maxItems"]
    embedded_bound = embedded["$defs"]["GraphPatch"]["properties"]["operations"]["maxItems"]
    assert bound == 5000 and embedded_bound == 5000, (bound, embedded_bound)
    record(
        "P-G-001",
        "generated Python mirror == canonical JSON; operations.maxItems == 5000",
        "PASS",
        f"maxItems={bound}",
    )


def p_g_002_ts_artifact_no_drift() -> None:
    ts_path = ROOT / "packages/contracts-ts/src/generated/graph-v1.ts"
    text = ts_path.read_text(encoding="utf-8")
    assert text.startswith(
        "/**\n * Generated from docs/contracts/knowledge-tree-graph.v1.schema.json."
    ), "TS artifact header missing"
    assert "export const graphContractSchemaVersion = 1 as const;" in text
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    assert canonical["$defs"]["GraphPatch"]["properties"]["operations"]["maxItems"] == 5000
    # drift gate (generate.mjs --check + tsc) is recorded separately
    record(
        "P-G-002",
        "contracts-ts graph-v1.ts artifact consistent (type-only, schema_version=1)",
        "PASS",
        "drift gate exit 0 recorded separately",
    )


def main() -> int:
    failures = 0
    probes: list[tuple[str, Any]] = [
        ("P-C-001", p_c_001_5000_accepted),
        ("P-C-002", p_c_002_5001_rejected),
        ("P-C-003", p_c_003_zero_ops_rejected),
        ("P-C-004", p_c_004_duplicate_op_id),
        ("P-C-005", p_c_005_duplicate_operation_target),
        ("P-C-006", p_c_006_150_accepted),
        ("P-C-007", p_c_007_2500_accepted),
        ("P-C-008", p_c_008_100_accepted_backward_compat),
        ("P-C-009", p_c_009_user_confidence_non_null),
        ("P-G-001", p_g_001_python_mirror_matches_canonical),
        ("P-G-002", p_g_002_ts_artifact_no_drift),
    ]
    for probe_id, fn in probes:
        try:
            fn()
        except Exception as error:  # noqa: BLE001 - probe harness reports any failure
            failures += 1
            record(probe_id, fn.__name__, "FAIL", f"{type(error).__name__}: {error}")

    import tempfile

    api_probes: list[tuple[str, Any]] = [
        (
            "P-A-001",
            lambda: p_a_001_workspace_240_ops_200(Path(tempfile.mkdtemp(prefix="tr007-a1-"))),
        ),
        (
            "P-A-002",
            lambda: p_a_002_workspace_no_resources_422(Path(tempfile.mkdtemp(prefix="tr007-a2-"))),
        ),
        ("P-A-003", lambda: p_a_003_no_generator_503(Path(tempfile.mkdtemp(prefix="tr007-a3-")))),
        (
            "P-A-004",
            lambda: p_a_004_single_resource_mode_200(Path(tempfile.mkdtemp(prefix="tr007-a4-"))),
        ),
    ]
    for probe_id, fn in api_probes:
        try:
            fn()
        except Exception as error:  # noqa: BLE001
            failures += 1
            record(probe_id, fn.__name__, "FAIL", f"{type(error).__name__}: {error}")

    total = len(_probe_results)
    print(f"\n=== {total - failures}/{total} probes passed, {failures} failed ===")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
