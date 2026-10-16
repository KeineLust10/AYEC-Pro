"""Capture notification content with headless DOM rendering and the admin shell."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "Admin_Konsol") not in sys.path:
    sys.path.insert(0, str(ROOT / "Admin_Konsol"))

from PIL import Image
from pages.notifications import REFERENCE


def _edge_executable() -> Path:
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Microsoft Edge is required for the headless DOM screenshot pipeline")


def _reference_document() -> str:
    source = REFERENCE.read_text(encoding="utf-8")
    head = re.search(r"<head\b[^>]*>(.*?)</head>", source, re.IGNORECASE | re.DOTALL)
    main = re.search(r"<main\b([^>]*)>(.*?)</main>", source, re.IGNORECASE | re.DOTALL)
    if not head or not main:
        raise RuntimeError("Notification reference is missing required document sections")
    attrs = re.sub(r"\bpt-14\b", "", main.group(1))
    fallback = (
        '<style>.font-display,.font-headline-lg,.font-headline-md,.font-body-default'
        '{font-family:"Plus Jakarta Sans","Segoe UI",Arial,sans-serif!important}'
        '.font-label-code,.font-badge-status'
        '{font-family:"JetBrains Mono","Segoe UI",Arial,monospace!important}'
        'body{font-family:"Segoe UI",Arial,sans-serif}</style>'
    )
    return (
        '<!doctype html><html lang="tr" class="dark"><head><meta charset="UTF-8">'
        + head.group(1) + fallback + '</head><body class="bg-background font-body-default text-on-surface">'
        + '<main' + attrs + '>' + main.group(2) + '</main></body></html>'
    )


def _capture(edge: Path, html: Path, screenshot: Path, width: int, height: int, profile: Path) -> None:
    command = [
        str(edge), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
        "--no-default-browser-check", "--lang=tr-TR", "--force-device-scale-factor=1",
        "--window-size=%d,%d" % (width, height), "--user-data-dir=" + str(profile),
        "--screenshot=" + str(screenshot), html.as_uri(),
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    with Image.open(screenshot) as image:
        if image.size != (width, height):
            raise RuntimeError("Headless browser returned an unexpected viewport size")


def main() -> int:
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    shell_capture = ROOT / "tools" / "quality" / "admin_dashboard_offscreen_capture.py"
    subprocess.run(
        [sys.executable, str(shell_capture)], check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
    )
    web_capture = ROOT / "tools" / "quality" / "admin_web_offscreen_capture.py"
    for width, height in ((1440, 1000), (390, 844)):
        subprocess.run(
            [sys.executable, str(web_capture), "--screen", "notifications", "--width", str(width),
             "--height", str(height), "--output", str(output / ("admin_notifications_web_mobile.png" if width < 500 else "admin_notifications_web_desktop.png"))],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
        )
    edge = _edge_executable()
    with tempfile.TemporaryDirectory(prefix="ayec-notifications-") as temp:
        temp_path = Path(temp)
        html = temp_path / "notifications.html"
        html.write_text(_reference_document(), encoding="utf-8")
        desktop_content = output / "admin_notifications_content_desktop.png"
        _capture(edge, html, desktop_content, 1176, 944, temp_path / "profile-desktop")
    shell = output / "admin_notifications_offscreen.png"
    if shell.is_file():
        with Image.open(shell) as shell_image, Image.open(desktop_content) as content_image:
            composite = shell_image.convert("RGBA")
            composite.alpha_composite(content_image.convert("RGBA"), (264, 56))
            composite.convert("RGB").save(shell, "PNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
