"""Local API launch entry point for manual verification (WORK-2026-014+).

Run from the repository root:

    uv run python -m apps.api --data-root <absolute-or-relative-dir>

The API binds loopback only and allows the Vite dev origins used by
`pnpm --filter @knowledge-tree/web dev`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

# The workspace packages are source trees, not installed distributions; add
# them so `python -m apps.api` resolves knowledge_tree_* like pytest does.
_ROOT = Path(__file__).resolve().parents[2]
for _src in ("packages/contracts-py/src", "packages/domain/src", "packages/infrastructure/src"):
    _path = str(_ROOT / _src)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from apps.api.main import create_app  # noqa: E402  (after sys.path setup)

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
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
