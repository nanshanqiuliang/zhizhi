"""Built-in MCP server for 知枝 (WORK-2026-048 + WORK-2026-050, Step 11).

Exposes read + AI-propose tools over the Model Context Protocol (stdio) so
external MCP clients (Cursor, Claude Desktop, ...) can enumerate workspaces,
read the knowledge tree, request an AI draft, validate a proposed patch, and
queue a patch as a PENDING proposal.

Hard harness rule (docs/ai-mindmap-agent-harness.md): no tool may write the
graph itself. `propose_patch` only queues an untrusted proposal file for the
in-app human confirmation flow (accept goes through the same commit gate as
the UI: locks / revision / history / undo); `proposal_status` is read-only
observation. External AI can never confirm its own proposal.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, cast


def _bootstrap_source_paths() -> None:
    """Source checkouts need `packages/*/src` on sys.path.

    pytest injects these via `[tool.pytest.ini_options] pythonpath`; the
    standalone entry `python -m apps.api.mcp_server` must do the same. Frozen
    builds (PyInstaller) already bundle the packages, so this is a no-op there.
    """

    if getattr(sys, "frozen", False):
        return
    repo = Path(__file__).resolve().parents[2]
    for name in ("contracts-py", "domain", "infrastructure"):
        src = repo / "packages" / name / "src"
        if src.is_dir() and str(src) not in sys.path:
            sys.path.insert(0, str(src))


_bootstrap_source_paths()

from knowledge_tree_domain import GraphPatchError, preview_graph_patch  # noqa: E402
from knowledge_tree_domain.ai_draft import DraftError  # noqa: E402
from knowledge_tree_infrastructure.ai_draft_llm import DraftExtractionError  # noqa: E402
from knowledge_tree_infrastructure.llm.errors import LLMProviderError  # noqa: E402
from knowledge_tree_infrastructure.png_export import export_workspace_png  # noqa: E402
from knowledge_tree_infrastructure.proposals import (  # noqa: E402
    read_proposal,
    save_proposal,
)
from knowledge_tree_infrastructure.web_search import WebSearchError  # noqa: E402
from knowledge_tree_infrastructure.workspace import (  # noqa: E402
    WorkspaceError,
    get_resource_mime,
    load_course_graph,
    parse_pdf_resource,
    read_resource_text,
    resolve_workspace,
)
from mcp.server.fastmcp import FastMCP  # noqa: E402

from apps.api.ai_config import load_api_key  # noqa: E402
from apps.api.main import (  # noqa: E402
    _LOCAL_ACTOR,
    _build_draft_generator,
    _build_web_searcher,
    _build_workspace_draft_generator,
    _list_workspaces,
    _read_workspace_texts,
)

JsonObject = dict[str, Any]
DraftGenerator = Any
WorkspaceDraftGenerator = Any


def _error(code: str, *, rule: str = "", **details: Any) -> JsonObject:
    return {"ok": False, "code": code, "rule": rule, **details}


def _error_from(error: Exception, *, code: str | None = None) -> JsonObject:
    """Map a domain error to the endpoint's stable shape: code + rule + safe details."""

    details = dict(getattr(error, "details", {}))
    return _error(
        code if code is not None else str(getattr(error, "code", "unknown_error")), **details
    )


# -- tool implementations (pure functions over a data root) --------------------


def tool_list_workspaces(root: Path) -> JsonObject:
    try:
        workspaces = _list_workspaces(root)
    except OSError as error:
        return _error("workspace_io", rule="list_failed", detail=str(error))
    return {"ok": True, "workspaces": workspaces}


def tool_read_workspace(root: Path, workspace_id: str) -> JsonObject:
    try:
        layout = resolve_workspace(root / workspace_id)
        graph = load_course_graph(layout)
    except WorkspaceError as error:
        return _error_from(error)
    return {"ok": True, "graph": graph}


def tool_preview_draft(
    root: Path,
    workspace_id: str,
    resource_id: str | None,
    draft_generator: DraftGenerator | None,
    workspace_draft_generator: WorkspaceDraftGenerator | None,
) -> JsonObject:
    """Run the AI draft pipeline without writing anything (untrusted proposal)."""
    try:
        layout = resolve_workspace(root / workspace_id)
        graph = load_course_graph(layout)
    except WorkspaceError as error:
        return _error_from(error)

    try:
        if resource_id:
            # Fail closed before touching storage when the generator is absent.
            if draft_generator is None:
                return _error("ai_not_available", rule="key_required")
            if get_resource_mime(layout, resource_id) == "application/pdf":
                parse_pdf_resource(layout, resource_id)
            text = read_resource_text(layout, resource_id)
            result = cast(JsonObject, draft_generator(text, resource_id, graph))
        else:
            if workspace_draft_generator is None:
                return _error("ai_not_available", rule="key_required")
            texts = _read_workspace_texts(layout)
            if not texts:
                return _error("draft_invalid", rule="no_resources")
            result = cast(JsonObject, workspace_draft_generator(texts, graph))
    except WorkspaceError as error:
        return _error_from(error)
    except (DraftError, DraftExtractionError) as error:
        return _error_from(error)
    except LLMProviderError as error:
        return _error_from(error)

    patch = result.get("patch")
    if not isinstance(patch, dict):
        return _error("draft_invalid", rule="patch_missing")
    operations = patch.get("operations")
    if not isinstance(operations, list) or not operations:
        return _error("draft_invalid", rule="no_new_concepts")
    # Defense in depth: the proposed patch must pass the same preview gate the
    # in-app flow uses; anything else fails closed before being returned.
    try:
        preview = preview_graph_patch(graph, patch, trusted_actor=_LOCAL_ACTOR)
    except GraphPatchError as error:
        return _error_from(error, code="draft_invalid")
    if preview.status != "requires_confirmation":
        return _error("draft_invalid", rule="patch_not_proposed")
    return {"ok": True, "draft": result.get("draft"), "patch": patch}


def tool_validate_patch(root: Path, workspace_id: str, patch: JsonObject) -> JsonObject:
    """Dry-run the commit gate on a caller-supplied patch (no write)."""
    try:
        layout = resolve_workspace(root / workspace_id)
        graph = load_course_graph(layout)
    except WorkspaceError as error:
        return _error_from(error)
    try:
        preview = preview_graph_patch(graph, patch, trusted_actor=_LOCAL_ACTOR)
    except GraphPatchError as error:
        return _error_from(error, code="patch_invalid")
    return {"ok": True, "status": preview.status, "snapshot": preview.snapshot}


def tool_propose_patch(
    root: Path, workspace_id: str, patch: JsonObject, note: str = ""
) -> JsonObject:
    """Queue a patch as a PENDING proposal file; never write the graph.

    The patch must pass the same defensive preview gate as the in-app flow and
    stay an unconfirmed draft (`requires_confirmation` / `confirmed=false`);
    a pre-confirmed or invalid patch fails closed before anything is queued.
    """

    try:
        layout = resolve_workspace(root / workspace_id)
        graph = load_course_graph(layout)
    except WorkspaceError as error:
        return _error_from(error)
    try:
        preview = preview_graph_patch(graph, patch, trusted_actor=_LOCAL_ACTOR)
    except GraphPatchError as error:
        return _error_from(error, code="patch_invalid")
    if preview.status != "requires_confirmation":
        return _error("patch_invalid", rule="patch_not_proposed")
    try:
        record = save_proposal(layout, patch, origin="mcp", note=note)
    except WorkspaceError as error:
        return _error_from(error)
    return {
        "ok": True,
        "proposal_id": record["proposal_id"],
        "status": record["status"],
        "requires_confirmation": True,
        "confirmed": False,
    }


def tool_proposal_status(root: Path, workspace_id: str, proposal_id: str) -> JsonObject:
    """Read-only observation of a queued proposal (no self-confirmation)."""
    try:
        layout = resolve_workspace(root / workspace_id)
    except WorkspaceError as error:
        return _error_from(error)
    try:
        record = read_proposal(layout, proposal_id)
    except WorkspaceError as error:
        return _error_from(error)
    return {
        "ok": True,
        "proposal_id": record["proposal_id"],
        "status": record["status"],
        "change_id": record.get("change_id"),
        "created_at": record.get("created_at"),
    }


def tool_export_png(root: Path, workspace_id: str) -> JsonObject:
    """Render the workspace graph to exports/mindmap.png (never the graph db)."""
    try:
        layout = resolve_workspace(root / workspace_id)
        graph = load_course_graph(layout)
    except WorkspaceError as error:
        return _error_from(error)
    try:
        exported = export_workspace_png(layout, graph)
    except WorkspaceError as error:
        return _error_from(error)
    return {"ok": True, "path": str(exported)}


def tool_search_draft(
    root: Path,
    workspace_id: str,
    query: str,
    searcher: Any,
    workspace_draft_generator: Any,
) -> JsonObject:
    """Topic -> web search -> untrusted draft; never writes the graph.

    Search snippets are untrusted external input used only as draft material;
    the returned patch stays `requires_confirmation` / `confirmed=false` behind
    the same preview gate as every other AI draft.
    """

    if not isinstance(query, str) or not query.strip() or len(query.strip()) > 200:
        return _error("web_search_invalid_query", rule="query_invalid")
    if searcher is None:
        return _error("web_search_not_available", rule="key_required")
    if workspace_draft_generator is None:
        return _error("ai_not_available", rule="key_required")
    try:
        hits = searcher(query.strip())
    except WebSearchError as error:
        return _error(error.code, **error.details)
    if not hits:
        return _error("web_search_failed", rule="no_results")

    try:
        layout = resolve_workspace(root / workspace_id)
        graph = load_course_graph(layout)
    except WorkspaceError as error:
        return _error_from(error)
    texts = [(f"web:{hit['url']}", f"{hit['title']}\n{hit['snippet']}") for hit in hits]
    try:
        result = cast(JsonObject, workspace_draft_generator(texts, graph))
    except WorkspaceError as error:
        return _error_from(error)
    except (DraftError, DraftExtractionError) as error:
        return _error_from(error)
    except LLMProviderError as error:
        return _error_from(error)

    patch = result.get("patch")
    if not isinstance(patch, dict):
        return _error("draft_invalid", rule="patch_missing")
    operations = patch.get("operations")
    if not isinstance(operations, list) or not operations:
        return _error("draft_invalid", rule="no_new_concepts")
    try:
        preview = preview_graph_patch(graph, patch, trusted_actor=_LOCAL_ACTOR)
    except GraphPatchError as error:
        return _error_from(error, code="draft_invalid")
    if preview.status != "requires_confirmation":
        return _error("draft_invalid", rule="patch_not_proposed")
    return {
        "ok": True,
        "draft": result.get("draft"),
        "patch": patch,
        "sources": [{"title": hit["title"], "url": hit["url"]} for hit in hits],
    }


# -- server assembly ------------------------------------------------------------


def build_mcp_server(
    data_root: Path,
    *,
    draft_generator: DraftGenerator | None = None,
    workspace_draft_generator: WorkspaceDraftGenerator | None = None,
    web_searcher: Any = None,
) -> FastMCP:
    """Build the MCP server bound to a data root.

    Mirrors `apps.api.main.create_app`: injected generators win (tests/embedding),
    otherwise generators are built from the saved key (config file, then
    environment). Missing key makes `preview_draft` fail closed.
    """

    root = Path(data_root)
    saved_key = load_api_key(root)
    state: dict[str, Any] = {
        "draft": (
            draft_generator if draft_generator is not None else _build_draft_generator(saved_key)
        ),
        "workspace": (
            workspace_draft_generator
            if workspace_draft_generator is not None
            else _build_workspace_draft_generator(saved_key)
        ),
        "search": (web_searcher if web_searcher is not None else _build_web_searcher(root)),
    }

    server = FastMCP(
        "zhizhi",
        instructions=(
            "知枝本地知识树。本服务器只读并提出 AI 草案：list_workspaces / "
            "read_workspace / preview_draft / validate_patch；propose_patch 可把补丁"
            "提交为待确认提议（pending），proposal_status 只读查询提议结果；"
            "export_png 把当前知识树渲染为 exports/mindmap.png；search_draft 用"
            "网络搜索主题生成待确认草案。"
            "AI 输出永远是不授信草案：确认与写库仅在应用内由用户完成，"
            "本服务器没有任何写图库或自确认工具。"
        ),
    )

    @server.tool()
    def list_workspaces() -> JsonObject:
        return tool_list_workspaces(root)

    @server.tool()
    def read_workspace(workspace_id: str) -> JsonObject:
        return tool_read_workspace(root, workspace_id)

    @server.tool()
    def preview_draft(workspace_id: str, resource_id: str | None = None) -> JsonObject:
        return tool_preview_draft(
            root,
            workspace_id,
            resource_id,
            state["draft"],
            state["workspace"],
        )

    @server.tool()
    def validate_patch(workspace_id: str, patch: JsonObject) -> JsonObject:
        return tool_validate_patch(root, workspace_id, patch)

    @server.tool()
    def propose_patch(workspace_id: str, patch: JsonObject, note: str = "") -> JsonObject:
        return tool_propose_patch(root, workspace_id, patch, note)

    @server.tool()
    def proposal_status(workspace_id: str, proposal_id: str) -> JsonObject:
        return tool_proposal_status(root, workspace_id, proposal_id)

    @server.tool()
    def export_png(workspace_id: str) -> JsonObject:
        return tool_export_png(root, workspace_id)

    @server.tool()
    def search_draft(workspace_id: str, query: str) -> JsonObject:
        return tool_search_draft(root, workspace_id, query, state["search"], state["workspace"])

    return server


def _default_data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "知枝" / "data"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="知枝 MCP server（stdio）")
    parser.add_argument("--data-root", type=Path, default=None, help="数据目录")
    args = parser.parse_args(argv)
    data_root = args.data_root or _default_data_root()
    data_root.mkdir(parents=True, exist_ok=True)
    server = build_mcp_server(data_root)
    # FastMCP run() defaults to the stdio transport; stdout must stay clean for
    # the JSON-RPC channel (logs go to stderr via the logging module).
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
