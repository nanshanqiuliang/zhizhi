"""QA TR-20260815-009 probe: edge_type persistence through the real API.

End-to-end proof for WORK-2026-047 AC-5: a canonical CourseGraph carrying a
prerequisite_of edge (exactly what the web `snapshotToGraph` now produces) is
PUT to the real backend and read back with the type preserved. The second PUT
exercises the diff-save path (label change + new part_of edge through the
protected patch gate), proving the diff save no longer rewrites typed edges
to related_to.

Run from the repo root:  uv run python evidence/TR-20260815-009/probes/qa_probe_edge_type_backend.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for _path in (
    REPO,
    REPO / "packages" / "contracts-py" / "src",
    REPO / "packages" / "domain" / "src",
    REPO / "packages" / "infrastructure" / "src",
):
    sys.path.insert(0, str(_path))

from fastapi.testclient import TestClient  # noqa: E402

from apps.api.main import create_app  # noqa: E402

COURSE_ID = "00000000-0000-7000-8000-000000000002"
WS_ID = "00000000-0000-7000-8000-000000000001"
A = "00000000-0000-7000-8000-000000000101"
B = "00000000-0000-7000-8000-000000000102"
C = "00000000-0000-7000-8000-000000000103"
E1 = "00000000-0000-7000-8000-000000000201"
E2 = "00000000-0000-7000-8000-000000000202"


def concept(cid: str, label: str) -> dict:
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


def edge(eid: str, src: str, dst: str, etype: str) -> dict:
    return {
        "id": eid,
        "course_id": COURSE_ID,
        "source_concept_id": src,
        "target_concept_id": dst,
        "edge_type": etype,
        "origin": "user",
        "review_state": "accepted",
        "confidence": None,
        "evidence_ids": [],
        "locked": False,
        "revision_no": 0,
    }


def layout_item(cid: str) -> dict:
    return {
        "view_id": WS_ID,
        "concept_id": cid,
        "x": 100,
        "y": 100,
        "pinned": False,
        "revision_no": 0,
    }


def graph(concepts: list[dict], edges: list[dict], revision_no: int = 0) -> dict:
    return {
        "schema_version": 1,
        "workspace_id": WS_ID,
        "course_id": COURSE_ID,
        "revision_no": revision_no,
        "concepts": concepts,
        "edges": edges,
        "layout_items": [layout_item(c["id"]) for c in concepts],
    }


def main() -> int:
    checks: list[tuple[str, bool, object]] = []
    with tempfile.TemporaryDirectory(prefix="kt-qa-047-") as tmp:
        app = create_app(data_root=Path(tmp), allowed_origins=[])
        with TestClient(app) as client:
            # 1. First save (whole-graph replace) with a prerequisite_of edge.
            g1 = graph(
                [concept(A, "A"), concept(B, "B")],
                [edge(E1, A, B, "prerequisite_of")],
            )
            r1 = client.put(f"/api/workspaces/{WS_ID}/graph", json=g1)
            checks.append(("PUT graph (first save) returns 200", r1.status_code == 200, r1.status_code))
            got1 = client.get(f"/api/workspaces/{WS_ID}/graph").json()
            et1 = got1["edges"][0]["edge_type"]
            checks.append(
                ("GET edge_type preserved after first save (prerequisite_of)",
                 et1 == "prerequisite_of", et1),
            )

            # 2. Second save: diff path through the patch gate. Change B's label
            #    and add a part_of edge B -> C; both types must survive.
            g2 = graph(
                [concept(A, "A"), concept(B, "B2"), concept(C, "C")],
                [edge(E1, A, B, "prerequisite_of"), edge(E2, B, C, "part_of")],
                revision_no=1,
            )
            r2 = client.put(f"/api/workspaces/{WS_ID}/graph", json=g2)
            checks.append(("PUT graph (diff save) returns 200", r2.status_code == 200, r2.status_code))
            got2 = client.get(f"/api/workspaces/{WS_ID}/graph").json()
            types2 = sorted(e["edge_type"] for e in got2["edges"])
            checks.append(
                ("GET edge types after diff save == [part_of, prerequisite_of]",
                 types2 == ["part_of", "prerequisite_of"], types2),
            )
            checks.append(
                ("diff save updated the label", any(c["label"] == "B2" for c in got2["concepts"]),
                 [c["label"] for c in got2["concepts"]]),
            )

            # 3. History recorded the diff save as a real patch application.
            history = client.get(f"/api/workspaces/{WS_ID}/history").json()["records"]
            checks.append(
                ("history records exist after diff save", len(history) >= 1, len(history)),
            )

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  (detail={detail})")
    print(f"RESULT: {len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
