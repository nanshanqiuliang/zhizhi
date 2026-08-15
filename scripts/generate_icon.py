"""Generate the application icon for the desktop bundle (WORK-2026-035 slice 3b).

Writes `apps/desktop/icon.png` (256x256) and a multi-size `apps/desktop/icon.ico`.
Run: `uv run python scripts/generate_icon.py`.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

_ROOT = Path(__file__).resolve().parents[1]
_OUT_PNG = _ROOT / "apps" / "desktop" / "icon.png"
_OUT_ICO = _ROOT / "apps" / "desktop" / "icon.ico"

_SIZE = 256
_BG = (79, 70, 229, 255)  # indigo-600 badge
_EDGE = (199, 210, 254, 255)  # indigo-200 edges
_NODE = (255, 255, 255, 255)  # white child nodes
_ROOT_NODE = (165, 243, 252, 255)  # cyan-200 root node


def _draw() -> Image.Image:
    image = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, _SIZE - 1, _SIZE - 1], radius=56, fill=_BG)

    root = (_SIZE // 2, 176)
    children = [(64, 92), (128, 92), (192, 92)]
    for child in children:
        draw.line([root, child], fill=_EDGE, width=8)
    for child in children:
        draw.ellipse([child[0] - 16, child[1] - 16, child[0] + 16, child[1] + 16], fill=_NODE)
    draw.ellipse([root[0] - 26, root[1] - 26, root[0] + 26, root[1] + 26], fill=_ROOT_NODE)
    return image


def main() -> None:
    image = _draw()
    image.save(_OUT_PNG, format="PNG")
    image.save(
        _OUT_ICO,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"wrote {_OUT_PNG} and {_OUT_ICO}")


if __name__ == "__main__":
    main()
