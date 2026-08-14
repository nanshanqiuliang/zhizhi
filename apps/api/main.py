"""Local persistence API composition root (WORK-2026-014).

FastAPI sidecar exposing the WORK-2026-013 workspace adapter over loopback
HTTP. This file only wires approved use cases to adapters; all graph semantics
live in `packages/domain` and `packages/contracts-py`, and storage lives in
`packages/infrastructure`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from knowledge_tree_domain import GraphPatchError, validate_course_graph
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    WorkspaceLayout,
    apply_graph_patch,
    backup_workspace,
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
    redo_graph,
    register_anchor,
    resolve_workspace,
    restore_backup_by_name,
    save_course_graph,
    search_course_graph,
    undo_graph,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

JsonObject = dict[str, Any]
_LOCAL_ACTOR = {"type": "user", "id": "local-user"}
_MAX_JSON_BYTES = 10 * 1024 * 1024


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


def create_app(*, data_root: Path, allowed_origins: list[str]) -> FastAPI:
    """Build the persistence API with an explicit data root and CORS allowlist."""

    root = Path(data_root)
    app = FastAPI(title="knowledge-tree-local-api", version="0.1.0")

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
