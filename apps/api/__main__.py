"""Local API launch entry point for manual verification (WORK-2026-014+).

Run from the repository root:

    uv run python -m apps.api --data-root <absolute-or-relative-dir>

The API binds loopback only and allows the Vite dev origins used by
`pnpm --filter @knowledge-tree/web dev`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from apps.api._runtime import ensure_source_paths

ensure_source_paths()

from apps.api.ai_draft import build_deepseek_draft_generator  # noqa: E402
from apps.api.answer import build_deepseek_answer_generator  # noqa: E402
from apps.api.command import build_deepseek_command_generator  # noqa: E402
from apps.api.main import create_app  # noqa: E402

DEFAULT_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge Tree local API")
    parser.add_argument(
        "--data-root",
        default=str(Path.home() / "knowledge-tree-data"),
        help="directory that holds workspace subdirectories (created on demand)",
    )
    parser.add_argument("--port", type=int, default=8000, help="loopback port")
    parser.add_argument(
        "--origin",
        action="append",
        default=[],
        help="extra allowed CORS origin (repeatable); dev origins are always allowed",
    )
    args = parser.parse_args()

    app = create_app(
        data_root=Path(args.data_root),
        allowed_origins=[*DEFAULT_ORIGINS, *args.origin],
        draft_generator=build_deepseek_draft_generator(),
        answer_generator=build_deepseek_answer_generator(),
        command_generator=build_deepseek_command_generator(),
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
