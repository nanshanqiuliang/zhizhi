"""Knowledge-tree PNG export (WORK-2026-051).

Deterministic server-side rendering of a CourseGraph to a PNG file:
BFS depth-based tree layout, tone-tinted rounded nodes, straight edges and a
CJK-safe font fallback chain (system fonts first, PIL bitmap font last).
Borrows the "server renders the mind map" idea from mind-map-mcp; no third
party rendering code is vendored.
"""

from __future__ import annotations

import os
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Never

from PIL import Image, ImageDraw, ImageFont

from knowledge_tree_infrastructure.workspace import WorkspaceError, WorkspaceLayout

JsonObject = dict[str, Any]

_NODE_W = 180
_NODE_H = 64
_GAP_X = 40
_GAP_Y = 90
_MARGIN = 40

_TONE_FILL = {"root": (37, 84, 168), "branch": (68, 120, 196), "leaf": (108, 152, 214)}
_TONE_TEXT = {"root": (255, 255, 255), "branch": (255, 255, 255), "leaf": (18, 24, 40)}

_FONT_CANDIDATES = (
    "msyh.ttc",
    "msyh.ttf",
    "simhei.ttf",
    "simsun.ttc",
    "NotoSansCJK-Regular.ttc",
    "wqy-microhei.ttc",
)


def _reject(code: str, *, rule: str, **details: Any) -> Never:
    raise WorkspaceError(code, details={"rule": rule, **details})


def layout_tree(
    concepts: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, float]]:
    """Depth-based tree layout: roots on top, one row per depth, spread by x.

    Roots are concepts with no incoming edge (first concept breaks ties);
    concepts unreachable from any root get their own bottom row. The result is
    a plain ``{concept_id: {x, y, depth}}`` mapping and fully deterministic.
    """

    if not concepts:
        return {}
    incoming: dict[str, int] = defaultdict(int)
    children: dict[str, list[str]] = defaultdict(list)
    targets = set()
    for edge in edges:
        source = str(edge.get("source_concept_id", ""))
        target = str(edge.get("target_concept_id", ""))
        if source and target and source != target:
            incoming[target] += 1
            children[source].append(target)
            targets.add(target)
    roots = [str(c.get("id", "")) for c in concepts if incoming[str(c.get("id", ""))] == 0]
    if not roots:
        first = str(concepts[0].get("id", ""))
        roots = [first]

    order: list[str] = []
    depth_of: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque((root, 0) for root in sorted(roots))
    while queue:
        node_id, depth = queue.popleft()
        if node_id in depth_of:
            continue
        depth_of[node_id] = depth
        order.append(node_id)
        for child in sorted(children.get(node_id, [])):
            if child not in depth_of:
                queue.append((child, depth + 1))

    # Unreachable concepts form one extra bottom row, deterministically sorted.
    bottom = sorted(str(c.get("id", "")) for c in concepts if str(c.get("id", "")) not in depth_of)
    bottom_depth = (max(depth_of.values()) + 1) if depth_of else 0
    for node_id in bottom:
        depth_of[node_id] = bottom_depth
    order.extend(bottom)

    by_depth: dict[int, list[str]] = defaultdict(list)
    for node_id in order:
        by_depth[depth_of[node_id]].append(node_id)

    positions: dict[str, dict[str, float]] = {}
    for depth in sorted(by_depth):
        row = by_depth[depth]
        for index, node_id in enumerate(row):
            positions[node_id] = {
                "x": _MARGIN + index * (_NODE_W + _GAP_X),
                "y": _MARGIN + depth * (_NODE_H + _GAP_Y),
                "depth": float(depth),
            }
    return positions


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    windir = os.environ.get("WINDIR", "C:\\Windows")
    for name in _FONT_CANDIDATES:
        for base in (str(Path(windir) / "Fonts"), str(Path.home() / ".fonts")):
            candidate = Path(base) / name
            if candidate.is_file():
                try:
                    return ImageFont.truetype(str(candidate), size)
                except OSError:
                    continue
    return ImageFont.load_default()


def _node_label(concept: Mapping[str, Any]) -> str:
    label = str(concept.get("label", "")).strip()
    if len(label) > 12:
        label = label[:11] + "…"
    return label or "（无标题）"


def render_graph_png(graph: Mapping[str, Any], out_path: Path) -> Path:
    """Render a CourseGraph to ``out_path`` (atomic write) and return it."""

    out_path = Path(out_path)
    concepts = graph.get("concepts")
    edges = graph.get("edges")
    concepts = concepts if isinstance(concepts, list) else []
    edges = edges if isinstance(edges, list) else []

    font_title = _load_font(20)
    font_placeholder = _load_font(28)

    if not concepts:
        image = Image.new("RGB", (900, 320), (250, 250, 252))
        draw = ImageDraw.Draw(image)
        draw.text(
            (60, 130),
            "这个工作区还没有节点。",
            fill=(90, 96, 128),
            font=font_placeholder,
        )
        _atomic_save(image, out_path)
        return out_path

    positions = layout_tree(concepts, edges)
    concept_by_id = {str(c.get("id", "")): c for c in concepts}
    max_x = max(pos["x"] for pos in positions.values()) + _NODE_W + _MARGIN
    max_y = max(pos["y"] for pos in positions.values()) + _NODE_H + _MARGIN

    image = Image.new("RGB", (int(max_x), int(max_y)), (250, 250, 252))
    draw = ImageDraw.Draw(image)
    for edge in edges:
        source = concept_by_id.get(str(edge.get("source_concept_id", "")))
        target = concept_by_id.get(str(edge.get("target_concept_id", "")))
        if source is None or target is None:
            continue
        start = positions[str(source["id"])]
        end = positions[str(target["id"])]
        draw.line(
            (start["x"] + _NODE_W / 2, start["y"] + _NODE_H, end["x"] + _NODE_W / 2, end["y"]),
            fill=(150, 156, 180),
            width=2,
        )
    for concept in concepts:
        node_id = str(concept.get("id", ""))
        pos = positions[node_id]
        tone = "root" if pos["depth"] == 0 else ("branch" if pos["depth"] == 1 else "leaf")
        box = (pos["x"], pos["y"], pos["x"] + _NODE_W, pos["y"] + _NODE_H)
        draw.rounded_rectangle(box, radius=12, fill=_TONE_FILL[tone])
        label = _node_label(concept)
        text_box = draw.textbbox((0, 0), label, font=font_title)
        text_w = text_box[2] - text_box[0]
        draw.text(
            (pos["x"] + (_NODE_W - text_w) / 2, pos["y"] + (_NODE_H - 26) / 2),
            label,
            fill=_TONE_TEXT[tone],
            font=font_title,
        )
    _atomic_save(image, out_path)
    return out_path


def _atomic_save(image: Image.Image, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(f"{out_path.name}.{os.getpid()}.tmp")
    image.save(tmp, format="PNG")
    os.replace(tmp, out_path)


def export_workspace_png(layout: WorkspaceLayout, graph: Mapping[str, Any]) -> Path:
    """Render a workspace graph into its exports dir as mindmap.png."""

    try:
        return render_graph_png(graph, layout.exports_dir / "mindmap.png")
    except (OSError, ValueError) as error:
        _reject("export_failed", rule="render_failed", detail=str(error))
