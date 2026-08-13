from __future__ import annotations

from copy import deepcopy

import pytest
from knowledge_tree_domain import GraphHistory, GraphHistoryError, GraphPatchError

from tests.contract.test_graph_contracts import valid_graph, valid_patch


@pytest.mark.parametrize("actor_type", ["ai", "import", "system"])
def test_non_user_patch_never_enters_history(actor_type: str) -> None:
    graph = valid_graph()
    patch = valid_patch()
    patch["confirmed"] = True
    patch["actor"] = {"type": actor_type, "id": f"{actor_type}-actor"}
    patch["operations"][0]["edge"]["origin"] = actor_type
    if actor_type == "ai":
        patch["operations"][0]["edge"]["evidence_ids"] = ["00000000-0000-7000-8300-000000000001"]
    graph_before = deepcopy(graph)
    history = GraphHistory.start(graph)

    with pytest.raises(GraphHistoryError) as raised:
        history.apply_patch(patch, trusted_actor=patch["actor"])

    assert raised.value.code == "permission_denied"
    assert history.snapshot == graph_before
    assert history.undo_records == ()


def test_unconfirmed_user_patch_never_enters_history() -> None:
    history = GraphHistory.start(valid_graph())

    with pytest.raises(GraphHistoryError) as raised:
        history.apply_patch(valid_patch(), trusted_actor={"type": "user", "id": "local-user"})

    assert raised.value.code == "permission_denied"
    assert history.undo_records == ()


def test_actor_spoof_is_rejected_before_history_record_is_created() -> None:
    patch = valid_patch()
    patch["confirmed"] = True
    history = GraphHistory.start(valid_graph())

    with pytest.raises(GraphPatchError) as raised:
        history.apply_patch(patch, trusted_actor={"type": "user", "id": "other-user"})

    assert raised.value.code == "permission_denied"
    assert history.undo_records == ()
