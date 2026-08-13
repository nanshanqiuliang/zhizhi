from pathlib import Path

from scripts.repository_validation import missing_required_paths


def test_repository_skeleton_has_required_paths() -> None:
    root = Path(__file__).resolve().parents[2]

    assert missing_required_paths(root) == []


def test_missing_required_path_is_reported(tmp_path: Path) -> None:
    missing = missing_required_paths(tmp_path)

    assert "AGENTS.md" in missing
    assert "apps/web" in missing
