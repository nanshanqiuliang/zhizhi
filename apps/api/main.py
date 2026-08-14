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
from fastapi.responses import JSONResponse
from knowledge_tree_domain import GraphPatchError, validate_course_graph
from knowledge_tree_infrastructure.workspace import (
    WorkspaceError,
    backup_workspace,
    create_workspace,
    import_resource,
    list_resources,
    load_course_graph,
    migrate,
    resolve_workspace,
    save_course_graph,
    search_course_graph,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

JsonObject = dict[str, Any]


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


def _http_error(error: WorkspaceError) -> HTTPException:
    if error.code == "workspace_missing":
        return HTTPException(status_code=404, detail={"code": error.code, **error.details})
    if error.code == "graph_invalid":
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code == "search_invalid_query":
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
    if error.code in {"import_type_rejected", "import_too_large", "import_failed"}:
        return HTTPException(status_code=422, detail={"code": error.code, **error.details})
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
                mime=None,
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

    return app


async def _read_json(request: Request) -> JsonObject:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=422, detail={"code": "graph_invalid"}) from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail={"code": "graph_invalid"})
    return payload
