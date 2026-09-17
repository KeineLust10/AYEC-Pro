"""Build GIF assets from a verified live desktop capture."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image


MENU_NAMES = (
    "dashboard",
    "customers",
    "stock",
    "appointments",
    "service_board",
    "finance",
)


def build(capture_dir: Path, web_assets: Path, desktop_assets: Path) -> list[Path]:
    web_assets.mkdir(parents=True, exist_ok=True)
    desktop_assets.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for name in MENU_NAMES:
        source = capture_dir / f"ayec_live_{name}.png"
        if not source.is_file():
            raise FileNotFoundError(source)
        gif_name = f"ayec-live-{name}.gif"
        web_target = web_assets / gif_name
        with Image.open(source) as image:
            frame = image.convert("RGB")
            frame.save(web_target, format="GIF", optimize=True)
        desktop_target = desktop_assets / gif_name
        shutil.copy2(web_target, desktop_target)
        created.extend((web_target, desktop_target))
    return created


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture_dir", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    created = build(
        args.capture_dir,
        args.root / "Web_Arayuzu" / "web" / "assets",
        args.root / "Masaustu" / "assets",
    )
    for path in created:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())