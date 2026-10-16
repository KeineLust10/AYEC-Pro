"""Capture the absolute Admin Console HTML references with headless Edge."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageChops, ImageStat

from admin_web_offscreen_capture import DESIGN_REFERENCE_FILES, DESIGN_REFERENCE_ROOT


ROOT = Path(__file__).resolve().parents[2]


def _capture(screen: str, width: int, height: int, output: Path) -> dict:
    html_path = DESIGN_REFERENCE_ROOT / f"{DESIGN_REFERENCE_FILES[screen]}.html"
    md_path = DESIGN_REFERENCE_ROOT / f"{DESIGN_REFERENCE_FILES[screen]}.md"
    if not html_path.is_file() or not md_path.is_file():
        raise FileNotFoundError(f"The absolute design reference pair is incomplete for {screen}")

    source = html_path.read_text(encoding="utf-8")
    base = f'<base href="{DESIGN_REFERENCE_ROOT.as_uri()}/">'
    head_open = re.search(r"<head\b[^>]*>", source, re.IGNORECASE)
    body_open = re.search(r"<body\b[^>]*>", source, re.IGNORECASE)
    if not head_open or not body_open:
        raise ValueError(f"The HTML reference has no head or body element for {screen}")
    reference_html = source[:head_open.end()] + base + source[head_open.end():]
    fallback = (
        '<style>body,button,input,select,textarea'
        '{font-family:"Plus Jakarta Sans","Segoe UI",Arial,sans-serif}</style>'
    )
    if width <= 760:
        fallback += (
            '<style>@media(max-width:760px){aside.w-72,aside.w-64{display:none!important}'
            '.pl-72,.pl-64{width:100vw!important;padding-left:0!important}'
            'header.left-72,header.left-64{left:0!important;right:0!important;width:100vw!important}'
            'main{width:100vw!important;max-width:100vw!important}'
            'html,body{width:100vw!important;overflow-x:hidden!important}}</style>'
        )
    body_open = re.search(r"<body\b[^>]*>", reference_html, re.IGNORECASE)
    reference_html = reference_html[:body_open.end()] + fallback + reference_html[body_open.end():]

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ayec-admin-reference-") as temporary:
        temporary_path = Path(temporary)
        temporary_html = temporary_path / f"{screen}.html"
        temporary_html.write_text(reference_html, encoding="utf-8", newline="\n")
        npm = shutil.which("npm")
        if not npm:
            raise FileNotFoundError("npm is required for the headless DOM reference capture")
        command = [
            npm,
            "exec",
            "--yes",
            "--package=playwright@1.64.1",
            "--",
            "playwright",
            "screenshot",
            "--channel",
            "msedge",
            "--viewport-size",
            f"{width},{height}",
            "--wait-for-timeout",
            "5000",
            "--lang",
            "tr-TR",
            "--color-scheme",
            "dark",
            "--timeout",
            "60000",
            temporary_html.as_uri(),
            str(output.resolve()),
        ]
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )

    with Image.open(output) as image:
        if image.size != (width, height):
            raise RuntimeError("The headless reference capture returned an unexpected viewport size")
    return {
        "screen": screen,
        "width": width,
        "height": height,
        "html": str(html_path),
        "md": str(md_path),
        "reference_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest(),
        "saved": output.is_file(),
        "output": str(output),
    }


def _compare_content(
    reference: Path,
    application: Path,
    width: int,
    height: int,
    screen: str,
    app_left_override: int | None = None,
) -> dict:
    with Image.open(reference) as reference_image, Image.open(application) as app_image:
        ref = reference_image.convert("RGB")
        app = app_image.convert("RGB")
        if ref.size != (width, height) or app.size != (width, height):
            raise ValueError("Reference and application screenshots must use the requested viewport")
        if width >= 761:
            reference_left = 268 if screen == "license-requests" else 304
            app_left = 336
            if app_left_override is not None:
                app_left = app_left_override
        else:
            reference_left = app_left = 0
        region_width = min(width - reference_left, width - app_left)
        ref_crop = ref.crop((reference_left, 0, reference_left + region_width, height))
        app_crop = app.crop((app_left, 0, app_left + region_width, height))
        diff = ImageChops.difference(ref_crop, app_crop)
        values = diff.get_flattened_data()
        pixel_count = len(values)
        exact = sum(pixel == (0, 0, 0) for pixel in values) / pixel_count
        mae = sum(ImageStat.Stat(diff).mean) / 3
        return {
            "compared_region": {"width": region_width, "height": height, "reference_left": reference_left, "application_left": app_left},
            "exact_pixel_fraction": round(exact, 6),
            "mean_absolute_error": round(mae, 4),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen", choices=tuple(DESIGN_REFERENCE_FILES), required=True)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare-app", type=Path)
    parser.add_argument("--app-left", type=int)
    args = parser.parse_args()
    output = args.output or ROOT / "artifacts" / f"admin_{args.screen}_reference_{args.width}x{args.height}.png"
    report = _capture(args.screen, args.width, args.height, output)
    if args.compare_app:
        report["comparison"] = _compare_content(
            output, args.compare_app, args.width, args.height, args.screen, args.app_left
        )
    print(json.dumps(report, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
