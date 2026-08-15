"""Local persistence API composition root (WORK-2026-014).

FastAPI sidecar exposing the WORK-2026-013 workspace adapter over loopback
HTTP. This file only wires approved use cases to adapters; all graph semantics
live in `packages/domain` and `packages/contracts-py`, and storage lives in
`packages/infrastructure`.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from knowledge_tree_domain import GraphPatchError, preview_graph_patch, validate_course_graph
from knowledge_tree_domain.ai_draft import DraftError, uuid7
from knowledge_tree_infrastructure.ai_draft_llm import DraftExtractionError
from knowledge_tree_infrastructure.command import CommandError, build_command_patch
from knowledge_tree_infrastructure.llm.errors import LLMProviderError
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    WorkspaceLayout,
    accept_ai_draft,
    apply_graph_patch,
    backup_workspace,
    build_answer_context,
    create_workspace,
    get_page_text,
    get_resource_file_path,
    get_resource_mime,
    import_resource,
    list_anchors,
    list_backups,
    list_resources,
    load_course_graph,
    load_history_records,
    migrate,
    parse_pdf_resource,
    read_resource_text,
    redo_graph,
    register_anchor,
    resolve_workspace,
    restore_backup_by_name,
    save_course_graph,
    search_course_graph,
    undo_graph,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.ai_config import load_api_key, save_api_key

JsonObject = dict[str, Any]
_LOCAL_ACTOR = {"type": "user", "id": "local-user"}
_MAX_JSON_BYTES = 10 * 1024 * 1024

# Injected draft generator: (resource_text, resource_id, current_graph) -> {draft, patch}.
DraftGenerator = Callable[[str, str, JsonObject], JsonObject]

# Injected answer generator: (question, context, sources) -> {answer, sources}.
AnswerGenerator = Callable[[str, str, list[JsonObject]], JsonObject]

# Injected command generator: (command, concepts) -> {summary, operations}.
CommandGenerator = Callable[[str, list[JsonObject]], JsonObject]


def _is_uuidv7(value: str) -> bool:
    try:
        identifier = UUID(value)
    except ValueError:
        return False
    return identifier.version == 7 and identifier.variant == "specified in RFC 4122"


def _workspace_root(data_root: Path, workspace_id: str) -> Path:
    """Resolve the data directory for a workspace id, rejecting path traversal."""

    if not _is_uuidv7(workspace_id):
        raise HTTPException(status_code=404, detail={"code": "workspace_missing"})
    return data_root / workspace_id


def _recovery_layout(workspace_root: Path) -> WorkspaceLayout:
    """Resolve a workspace for backup/restore, tolerating a missing db file.

    A lost/corrupt database is exactly the crash-recovery case that backup and
    restore must handle, so they fall back to creating the layout instead of
    failing on `database_file_absent`.
    """

    try:
        return resolve_workspace(workspace_root)
    except WorkspaceError as error:
        if (
            error.code == "workspace_missing"
            and error.details.get("rule") == "database_file_absent"
        ):
            return create_workspace(workspace_root)
        raise


def _reveal_in_explorer(path: Path, *, select: bool) -> None:
    """Open the folder containing `path` in Explorer (no-op off Windows).

    `select=True` highlights the file (`explorer /select,`), `select=False`
    opens the directory itself. Used by the local-only reveal endpoints.
    """

    if os.name != "nt":
        return
    args = ["explorer", "/select,", str(path)] if select else ["explorer", str(path)]
    subprocess.Popen(args)


def _fresh_course_graph(workspace_id: str, name: str) -> JsonObject:
    """A minimal valid CourseGraph with a single root concept (new course)."""

    concept_id = str(uuid7())
    course_id = str(uuid7())
    return {
        "schema_version": 1,
        "workspace_id": workspace_id,
        "course_id": course_id,
        "revision_no": 0,
        "concepts": [
            {
                "id": concept_id,
                "course_id": course_id,
                "label": name,
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
        ],
        "edges": [],
        "layout_items": [
            {
                "view_id": workspace_id,
                "concept_id": concept_id,
                "x": 250,
                "y": 180,
                "pinned": False,
                "revision_no": 0,
            }
        ],
    }


def _list_workspaces(root: Path) -> list[JsonObject]:
    """Enumerate existing workspaces (UUIDv7 dirs with a saved graph)."""

    workspaces: list[JsonObject] = []
    if not root.is_dir():
        return workspaces
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not _is_uuidv7(entry.name):
            continue
        try:
            layout = resolve_workspace(entry)
            graph = load_course_graph(layout)
        except WorkspaceError:
            continue
        concepts = [c for c in graph.get("concepts", []) if isinstance(c, dict)]
        targets = {
            edge.get("target_concept_id")
            for edge in graph.get("edges", [])
            if isinstance(edge, dict)
        }
        label: Any = None
        for concept in concepts:
            if concept.get("id") not in targets:
                label = concept.get("label")
                break
        if label is None and concepts:
            label = concepts[0].get("label")
        updated_at: float | str = ""
        with suppress(OSError):
            updated_at = entry.joinpath("knowledge-tree.db").stat().st_mtime
        workspaces.append(
            {
                "id": entry.name,
                "name": str(label) if label else "未命名课程",
                "concept_count": len(concepts),
                "updated_at": updated_at,
            }
        )
    return workspaces


def _http_error(error: WorkspaceError) -> HTTPException:
    if error.code == "workspace_missing":
        return HTTPException(status_code=404, detail={"code": error.code, **error.details})
    if error.code == "graph_invalid":
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code == "search_invalid_query":
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code in {"import_type_rejected", "import_too_large", "import_failed"}:
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code in {"parse_failed", "parse_pending", "page_out_of_range", "source_changed"}:
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code == "draft_unsupported_resource":
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code == "file_not_found":
        return HTTPException(status_code=404, detail={"code": error.code, **error.details})
    if error.code in {"backup_invalid"}:
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code == "backup_checksum_mismatch":
        return HTTPException(status_code=409, detail={"code": error.code, **error.details})
    if error.code == "patch_invalid":
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code in {
        "patch_revision_conflict",
        "revision_conflict",
        "target_locked",
        "permission_denied",
        "history_empty",
        "history_conflict",
        "record_tampered",
        "record_invalid",
    }:
        return HTTPException(status_code=409, detail={"code": error.code, **error.details})
    if error.code == "workspace_corrupt" and error.details.get("rule") == "course_graph_absent":
        # A workspace without a saved graph is equivalent to "not found".
        return HTTPException(status_code=404, detail={"code": "workspace_missing"})
    return HTTPException(status_code=500, detail={"code": error.code, **error.details})


def _build_draft_generator(api_key: str | None) -> DraftGenerator | None:
    if not api_key:
        return None
    from apps.api.ai_draft import build_deepseek_draft_generator

    return build_deepseek_draft_generator(api_key)


def _build_answer_generator(api_key: str | None) -> AnswerGenerator | None:
    if not api_key:
        return None
    from apps.api.answer import build_deepseek_answer_generator

    return build_deepseek_answer_generator(api_key)


def _build_command_generator(api_key: str | None) -> CommandGenerator | None:
    if not api_key:
        return None
    from apps.api.command import build_deepseek_command_generator

    return build_deepseek_command_generator(api_key)


def create_app(
    *,
    data_root: Path,
    allowed_origins: list[str],
    draft_generator: DraftGenerator | None = None,
    answer_generator: AnswerGenerator | None = None,
    command_generator: CommandGenerator | None = None,
    web_dist: Path | None = None,
) -> FastAPI:
    """Build the persistence API with an explicit data root and CORS allowlist.

    `draft_generator`/`answer_generator`/`command_generator` are the AI
    composition roots; when None the corresponding endpoints fail closed with
    503 `ai_not_available`.

    `web_dist` optionally points at a built Web UI directory (`index.html` +
    `assets/`); when present it is served from the same origin as the API, so a
    frozen desktop build needs no separate Vite server and no cross-origin CORS.
    """

    root = Path(data_root)
    app = FastAPI(title="knowledge-tree-local-api", version="0.1.0")

    # AI generators are held in a mutable holder so the settings endpoint can
    # rebuild them after the key changes. Injected generators (tests/embedding)
    # win; otherwise build from the saved key (config file, then environment).
    saved_key = load_api_key(root)
    ai_state: dict[str, Any] = {
        "draft_generator": (
            draft_generator if draft_generator is not None else _build_draft_generator(saved_key)
        ),
        "answer_generator": (
            answer_generator if answer_generator is not None else _build_answer_generator(saved_key)
        ),
        "command_generator": (
            command_generator
            if command_generator is not None
            else _build_command_generator(saved_key)
        ),
    }

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "PUT", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.exception_handler(StarletteHTTPException)
    async def flatten_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail: Any = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "http_error", "detail": detail},
        )

    @app.get("/api/health")
    def health() -> JsonObject:
        return {"status": "ok"}

    @app.get("/api/workspaces")
    def get_workspaces() -> JsonObject:
        return {"workspaces": _list_workspaces(root)}

    @app.post("/api/workspaces")
    async def post_workspace(request: Request) -> JsonObject:
        payload = await _read_json(request)
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 50:
            raise HTTPException(
                status_code=422,
                detail={"code": "workspace_invalid", "rule": "name_invalid"},
            )
        workspace_id = str(uuid7())
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = create_workspace(workspace_root)
            migrate(layout.db_path)
            save_course_graph(layout, _fresh_course_graph(workspace_id, name.strip()))
        except WorkspaceError as error:
            raise _http_error(error) from error
        return {"id": workspace_id, "name": name.strip()}

    @app.get("/api/settings/ai")
    def get_ai_settings() -> JsonObject:
        key = load_api_key(root)
        return {
            "configured": bool(key),
            "enabled": ai_state["draft_generator"] is not None,
        }

    @app.put("/api/settings/ai")
    async def put_ai_settings(request: Request) -> JsonObject:
        payload = await _read_json(request)
        api_key = payload.get("api_key")
        if not isinstance(api_key, str) or not api_key.strip():
            raise HTTPException(
                status_code=422, detail={"code": "ai_key_invalid", "rule": "api_key_missing"}
            )
        save_api_key(root, api_key.strip())
        ai_state["draft_generator"] = _build_draft_generator(api_key.strip())
        ai_state["answer_generator"] = _build_answer_generator(api_key.strip())
        ai_state["command_generator"] = _build_command_generator(api_key.strip())
        return {"status": "saved", "configured": True}

    @app.delete("/api/settings/ai")
    def delete_ai_settings() -> JsonObject:
        save_api_key(root, None)
        ai_state["draft_generator"] = None
        ai_state["answer_generator"] = None
        ai_state["command_generator"] = None
        return {"status": "cleared", "configured": False}

    @app.get("/api/workspaces/{workspace_id}/graph")
    def get_graph(workspace_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            graph: JsonObject = load_course_graph(layout)
            return graph
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.put("/api/workspaces/{workspace_id}/graph")
    async def put_graph(workspace_id: str, request: Request) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        try:
            validate_course_graph(payload)
        except GraphPatchError as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "graph_invalid", "rule": error.code, **error.details},
            ) from error
        try:
            layout = create_workspace(workspace_root)
            migrate(layout.db_path)
            save_course_graph(layout, payload)
            return {"status": "saved", "workspace_id": workspace_id}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/graph/patches")
    async def post_graph_patch(workspace_id: str, request: Request) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        try:
            layout = resolve_workspace(workspace_root)
            record = apply_graph_patch(layout, payload, trusted_actor=_LOCAL_ACTOR)
            return {
                "status": "applied",
                "change_id": record.change_id,
                "revision_no": record.after_revision_no,
            }
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/graph/undo")
    def post_graph_undo(workspace_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            graph = undo_graph(layout)
            return {"status": "undone", "revision_no": graph["revision_no"]}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/graph/redo")
    def post_graph_redo(workspace_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            graph = redo_graph(layout)
            return {"status": "redone", "revision_no": graph["revision_no"]}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.get("/api/workspaces/{workspace_id}/history")
    def get_history(workspace_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            records = load_history_records(layout)
            return {
                "records": [
                    {
                        "change_id": record.change_id,
                        "before_revision_no": record.before_revision_no,
                        "after_revision_no": record.after_revision_no,
                        "source": record.source,
                    }
                    for record in records
                ]
            }
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/backup")
    def post_backup(workspace_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            # Do not silently create an empty workspace on backup: require an
            # existing saved graph, matching the GET semantics.
            layout = resolve_workspace(workspace_root)
            load_course_graph(layout)
            backup_path = backup_workspace(layout)
            return {"status": "backed_up", "backup_path": str(backup_path)}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.get("/api/workspaces/{workspace_id}/backups")
    def get_backups(workspace_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = _recovery_layout(workspace_root)
            return {"backups": list_backups(layout)}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/restore")
    async def post_restore(workspace_id: str, request: Request) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        filename = payload.get("filename")
        if not isinstance(filename, str) or not filename:
            raise HTTPException(
                status_code=422, detail={"code": "backup_invalid", "rule": "filename_missing"}
            )
        try:
            layout = _recovery_layout(workspace_root)
            restore_backup_by_name(layout, filename)
            return {"status": "restored", "filename": filename}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.get("/api/workspaces/{workspace_id}/search")
    def search_graph(workspace_id: str, q: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            results = search_course_graph(layout, q)
            return {
                "results": [
                    {"id": result.id, "label": result.label, "snippet": result.snippet}
                    for result in results
                ]
            }
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/resources")
    async def post_resource(workspace_id: str, request: Request) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = create_workspace(workspace_root)
            migrate(layout.db_path)
        except WorkspaceError as error:
            raise _http_error(error) from error
        try:
            form = await request.form()
            upload = form.get("file")
            if upload is None or not hasattr(upload, "filename") or not hasattr(upload, "read"):
                raise HTTPException(
                    status_code=422, detail={"code": "import_type_rejected", "rule": "file_missing"}
                )
            content = await upload.read()
            info = import_resource(
                layout,
                display_name=str(upload.filename or "upload"),
                content=content,
            )
            return {
                "id": info.id,
                "display_name": info.display_name,
                "mime": info.mime,
                "byte_size": info.byte_size,
                "content_hash": info.content_hash,
                "created_at": info.created_at,
            }
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.get("/api/workspaces/{workspace_id}/resources")
    def get_resources(workspace_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            resources = list_resources(layout)
            return {
                "resources": [
                    {
                        "id": info.id,
                        "display_name": info.display_name,
                        "mime": info.mime,
                        "byte_size": info.byte_size,
                        "content_hash": info.content_hash,
                        "created_at": info.created_at,
                    }
                    for info in resources
                ]
            }
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/resources/{resource_id}/parse")
    def post_parse(workspace_id: str, resource_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            page_count = parse_pdf_resource(layout, resource_id)
            return {"status": "parsed", "resource_id": resource_id, "page_count": page_count}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.get("/api/workspaces/{workspace_id}/resources/{resource_id}/pages/{page}")
    def get_page(workspace_id: str, resource_id: str, page: int) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            segment = get_page_text(layout, resource_id, page)
            return {
                "resource_version_id": segment.resource_version_id,
                "page": segment.page,
                "text": segment.text,
                "text_hash": segment.text_hash,
            }
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.get("/api/workspaces/{workspace_id}/resources/{resource_id}/file")
    def get_file(workspace_id: str, resource_id: str) -> FileResponse:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            mime = get_resource_mime(layout, resource_id)
            file_path = get_resource_file_path(layout, resource_id)
            return FileResponse(file_path, media_type=mime, filename=Path(resource_id).name)
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/resources/open-dir")
    def post_resources_open_dir(workspace_id: str) -> JsonObject:
        """Open this workspace's `resources/` directory in the file explorer."""
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            resources_dir = layout.root / "resources"
            if not resources_dir.is_dir():
                raise HTTPException(
                    status_code=422,
                    detail={"code": "file_not_found", "rule": "resources_dir_absent"},
                )
            _reveal_in_explorer(resources_dir, select=False)
            return {"status": "revealed", "path": str(resources_dir)}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/resources/{resource_id}/reveal")
    def post_resource_reveal(workspace_id: str, resource_id: str) -> JsonObject:
        """Reveal a resource's stored file in the file explorer (selected)."""
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            file_path = get_resource_file_path(layout, resource_id)
            _reveal_in_explorer(file_path, select=True)
            return {"status": "revealed", "path": str(file_path)}
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.get("/api/workspaces/{workspace_id}/resources/{resource_id}/anchors")
    def get_anchors(workspace_id: str, resource_id: str) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            layout = resolve_workspace(workspace_root)
            anchors = list_anchors(layout, resource_id)
            return {
                "anchors": [
                    {
                        "id": anchor.id,
                        "resource_id": anchor.resource_id,
                        "page": anchor.page,
                        "payload": anchor.payload,
                    }
                    for anchor in anchors
                ]
            }
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/resources/{resource_id}/anchors")
    async def post_anchor(workspace_id: str, resource_id: str, request: Request) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        page = payload.get("page")
        anchor_payload = payload.get("payload")
        if not isinstance(page, int) or page < 1 or not isinstance(anchor_payload, dict):
            raise HTTPException(
                status_code=422,
                detail={"code": "anchor_invalid", "rule": "page_or_payload_invalid"},
            )
        try:
            layout = resolve_workspace(workspace_root)
            anchor = register_anchor(
                layout,
                resource_id=resource_id,
                page=page,
                payload=anchor_payload,
            )
            return {
                "id": anchor.id,
                "resource_id": anchor.resource_id,
                "page": anchor.page,
                "payload": anchor.payload,
            }
        except WorkspaceError as error:
            raise _http_error(error) from error

    @app.post("/api/workspaces/{workspace_id}/ai-draft")
    async def post_ai_draft(workspace_id: str, request: Request) -> JsonObject:
        if ai_state["draft_generator"] is None:
            raise HTTPException(status_code=503, detail={"code": "ai_not_available"})
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        resource_id = payload.get("resource_id")
        if not isinstance(resource_id, str) or not resource_id:
            raise HTTPException(
                status_code=422,
                detail={"code": "draft_invalid", "rule": "resource_id_missing"},
            )
        try:
            layout = resolve_workspace(workspace_root)
            graph = load_course_graph(layout)
            text = read_resource_text(layout, resource_id)
            result = cast(DraftGenerator, ai_state["draft_generator"])(text, resource_id, graph)
        except WorkspaceError as error:
            raise _http_error(error) from error
        except (DraftError, DraftExtractionError) as error:
            raise HTTPException(
                status_code=422, detail={"code": error.code, **error.details}
            ) from error
        except LLMProviderError as error:
            raise HTTPException(
                status_code=502, detail={"code": error.code, **error.details}
            ) from error

        patch = result.get("patch")
        if not isinstance(patch, dict):
            raise HTTPException(
                status_code=500, detail={"code": "draft_invalid", "rule": "patch_missing"}
            )
        # Defense in depth: the returned patch must be a legal proposed
        # (unconfirmed) user-authored patch the commit gate would preview as
        # `requires_confirmation`; anything else fails closed before returning.
        try:
            preview = preview_graph_patch(graph, patch, trusted_actor=_LOCAL_ACTOR)
        except GraphPatchError as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "draft_invalid", "rule": error.code, **error.details},
            ) from error
        if preview.status != "requires_confirmation":
            raise HTTPException(
                status_code=500,
                detail={"code": "draft_invalid", "rule": "patch_not_proposed"},
            )
        return result

    @app.post("/api/workspaces/{workspace_id}/ai-draft/accept")
    async def post_ai_draft_accept(workspace_id: str, request: Request) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        patch = payload.get("patch")
        evidence = payload.get("evidence")
        if not isinstance(patch, dict):
            raise HTTPException(
                status_code=422, detail={"code": "draft_invalid", "rule": "patch_missing"}
            )
        if not isinstance(evidence, list):
            raise HTTPException(
                status_code=422, detail={"code": "draft_invalid", "rule": "evidence_missing"}
            )
        anchors: list[JsonObject] = []
        for item in evidence:
            anchor_id = item.get("anchor_id") if isinstance(item, dict) else None
            resource_id = item.get("resource_id") if isinstance(item, dict) else None
            if (
                not isinstance(anchor_id, str)
                or not _is_uuidv7(anchor_id)
                or not isinstance(resource_id, str)
                or not _is_uuidv7(resource_id)
            ):
                raise HTTPException(
                    status_code=422,
                    detail={"code": "draft_invalid", "rule": "evidence_item_invalid"},
                )
            anchors.append(
                {
                    "id": anchor_id,
                    "resource_id": resource_id,
                    "page": 0,
                    "label": item.get("label", "AI 草案来源"),
                }
            )
        try:
            layout = resolve_workspace(workspace_root)
            record = accept_ai_draft(layout, patch, trusted_actor=_LOCAL_ACTOR, anchors=anchors)
        except WorkspaceError as error:
            raise _http_error(error) from error
        return {
            "status": "applied",
            "change_id": record.change_id,
            "revision_no": record.after_revision_no,
        }

    @app.post("/api/workspaces/{workspace_id}/interpret/accept")
    async def post_interpret_accept(workspace_id: str, request: Request) -> JsonObject:
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        patch = payload.get("patch")
        if not isinstance(patch, dict):
            raise HTTPException(
                status_code=422, detail={"code": "command_invalid", "rule": "patch_missing"}
            )
        try:
            layout = resolve_workspace(workspace_root)
            record = apply_graph_patch(
                layout, patch, trusted_actor=_LOCAL_ACTOR, source="ai_command"
            )
        except WorkspaceError as error:
            raise _http_error(error) from error
        return {
            "status": "applied",
            "change_id": record.change_id,
            "revision_no": record.after_revision_no,
        }

    @app.post("/api/workspaces/{workspace_id}/answer")
    async def post_answer(workspace_id: str, request: Request) -> JsonObject:
        if ai_state["answer_generator"] is None:
            raise HTTPException(status_code=503, detail={"code": "ai_not_available"})
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            raise HTTPException(
                status_code=422, detail={"code": "answer_invalid", "rule": "question_empty"}
            )
        if len(question) > 100:
            raise HTTPException(
                status_code=422, detail={"code": "answer_invalid", "rule": "question_too_long"}
            )
        try:
            layout = resolve_workspace(workspace_root)
            context_obj = build_answer_context(layout, question)
        except WorkspaceError as error:
            raise _http_error(error) from error
        sources = [
            {"id": source.id, "label": source.label, "kind": "concept"}
            for source in context_obj.sources
        ]
        if not sources:
            return {"answer": "", "sources": [], "note": "no_matches"}
        try:
            return cast(AnswerGenerator, ai_state["answer_generator"])(
                question, context_obj.context, sources
            )
        except LLMProviderError as error:
            raise HTTPException(
                status_code=502, detail={"code": error.code, **error.details}
            ) from error

    @app.post("/api/workspaces/{workspace_id}/interpret")
    async def post_interpret(workspace_id: str, request: Request) -> JsonObject:
        if ai_state["command_generator"] is None:
            raise HTTPException(status_code=503, detail={"code": "ai_not_available"})
        workspace_root = _workspace_root(root, workspace_id)
        try:
            payload = await _read_json(request)
        except HTTPException as error:
            raise error
        command = payload.get("command")
        if not isinstance(command, str) or not command.strip():
            raise HTTPException(
                status_code=422, detail={"code": "command_invalid", "rule": "command_empty"}
            )
        if len(command) > 500:
            raise HTTPException(
                status_code=422, detail={"code": "command_invalid", "rule": "command_too_long"}
            )
        try:
            layout = resolve_workspace(workspace_root)
            graph = load_course_graph(layout)
        except WorkspaceError as error:
            raise _http_error(error) from error
        concepts = [
            {"id": concept["id"], "label": concept["label"]}
            for concept in graph.get("concepts", [])
        ]
        try:
            interpreted = cast(CommandGenerator, ai_state["command_generator"])(command, concepts)
        except LLMProviderError as error:
            raise HTTPException(
                status_code=502, detail={"code": error.code, **error.details}
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "command_invalid", "rule": getattr(error, "args", ("parse",))[0]},
            ) from error
        try:
            patch = build_command_patch(
                graph, interpreted.get("operations", []), id_factory=uuid7, reason=command
            )
        except CommandError as error:
            raise HTTPException(
                status_code=422, detail={"code": error.code, **error.details}
            ) from error
        try:
            preview = preview_graph_patch(graph, patch, trusted_actor=_LOCAL_ACTOR)
        except GraphPatchError as error:
            raise HTTPException(
                status_code=422,
                detail={"code": "command_invalid", "rule": error.code, **error.details},
            ) from error
        if preview.status != "requires_confirmation":
            raise HTTPException(
                status_code=500,
                detail={"code": "command_invalid", "rule": "patch_not_proposed"},
            )
        return {"summary": interpreted.get("summary", ""), "patch": patch}

    if web_dist is not None and Path(web_dist).is_dir():
        # Serve the built Web UI from the same origin as the API. API routes
        # registered above take precedence over this catch-all mount.
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="web")

    return app


async def _read_json(request: Request) -> JsonObject:
    body = await request.body()
    if len(body) > _MAX_JSON_BYTES:
        raise HTTPException(
            status_code=422, detail={"code": "graph_invalid", "rule": "body_too_large"}
        )
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=422, detail={"code": "graph_invalid"}) from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail={"code": "graph_invalid"})
    return payload
