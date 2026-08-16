"""Red-light tests for the vertical tidy-tree draft layout (WORK-2026-054).

The layout must stack parent-over-children (vertical first), center each
parent over its children block, spread siblings evenly, and keep concepts
without any prerequisite edge on a bottom row instead of crowding the top.
"""

from __future__ import annotations

from knowledge_tree_domain.ai_draft import (
    DraftConcept,
    DraftRelation,
    assign_draft_layout,
)

VIEW = "00000000-0000-7000-8000-000000000004"


def _concept(label: str) -> DraftConcept:
    return DraftConcept(label=label, aliases=(), confidence=0.9, evidence_ids=("e",))


def _rel(source: str, target: str) -> DraftRelation:
    return DraftRelation(source, target, "prerequisite_of", 0.8, ())


def _layout(concepts, relations, **kwargs):
    items = assign_draft_layout(concepts, relations, view_id=VIEW, **kwargs)
    return {item[0]: (item[1], item[2]) for item in items}


def test_parent_is_centered_over_its_children() -> None:
    concepts = tuple(_concept(label) for label in ("根", "子1", "子2"))
    positions = _layout(concepts, (_rel("根", "子1"), _rel("根", "子2")))

    child_mid = (positions["子1"][0] + positions["子2"][0]) / 2
    assert positions["根"][0] == child_mid


def test_children_stack_below_parent_with_spacious_gap() -> None:
    concepts = tuple(_concept(label) for label in ("根", "子1", "子2"))
    positions = _layout(concepts, (_rel("根", "子1"), _rel("根", "子2")))

    # Vertical-first: children exactly one (widened) gap below the parent.
    assert positions["子1"][1] - positions["根"][1] >= 200
    assert positions["子2"][1] == positions["子1"][1]
    # Even spread: sibling slots never crowd together.
    assert abs(positions["子2"][0] - positions["子1"][0]) >= 240


def test_wide_sibling_group_keeps_even_spacing() -> None:
    labels = ("根", "a", "b", "c", "d")
    concepts = tuple(_concept(label) for label in labels)
    relations = tuple(_rel("根", label) for label in labels[1:])
    positions = _layout(concepts, relations)

    xs = sorted(positions[label][0] for label in labels[1:])
    for left, right in zip(xs, xs[1:], strict=False):
        assert right - left >= 240
    # The parent sits over the middle of the sibling block.
    assert positions["根"][0] == (xs[0] + xs[-1]) / 2


def test_unrelated_concepts_form_a_bottom_row() -> None:
    concepts = tuple(_concept(label) for label in ("根", "子", "无关1", "无关2", "无关3"))
    relations = (_rel("根", "子"),)
    positions = _layout(concepts, relations)

    orphans_all = ("无关1", "无关2", "无关3")
    bottom = max(pos[1] for label, pos in positions.items() if label not in orphans_all)
    for orphan in orphans_all:
        assert positions[orphan][1] > bottom
    # The orphans spread evenly on their own row.
    orphans_x = sorted(positions[label][0] for label in orphans_all)
    for left, right in zip(orphans_x, orphans_x[1:], strict=False):
        assert right - left >= 240


def test_deep_chain_is_a_straight_vertical_line() -> None:
    labels = ("一", "二", "三", "四", "五")
    concepts = tuple(_concept(label) for label in labels)
    relations = tuple(_rel(a, b) for a, b in zip(labels, labels[1:], strict=False))
    positions = _layout(concepts, relations)

    for upper, lower in zip(labels, labels[1:], strict=False):
        assert positions[lower][1] - positions[upper][1] >= 200
        assert positions[lower][0] == positions[upper][0]


def test_layout_is_deterministic_and_dag_nodes_placed_once() -> None:
    concepts = tuple(_concept(label) for label in ("A", "B", "C", "D", "E"))
    relations = (
        _rel("A", "B"),
        _rel("A", "C"),
        _rel("B", "D"),
        _rel("C", "D"),  # DAG: D has two prerequisite parents
        _rel("D", "E"),
    )
    first = _layout(concepts, relations)
    second = _layout(concepts, relations)
    assert first == second
    assert len(first) == len(concepts)
    # D hangs under exactly one layout parent; its level comes from the
    # longest chain (A -> B -> D), so it sits strictly below B and C.
    assert first["D"][1] > first["B"][1]
    assert first["D"][1] > first["C"][1]
    assert first["E"][1] > first["D"][1]
