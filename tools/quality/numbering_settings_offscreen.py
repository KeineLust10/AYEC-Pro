"""Render the production numbering-settings helper in a hidden Edge instance."""

from __future__ import annotations

import html.parser
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
REPORT = ROOT / "output" / "playwright" / "numbering-settings-offscreen.json"


def _edge_path() -> Path:
    candidates = (
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


def _extract_helper(source: str) -> str:
    start = source.index("function numberingSettingsBody(){")
    end = source.index("\nfunction settingBody", start)
    return source[start:end]


def _result_from_dom(dom: str) -> dict[str, object]:
    match = re.search(r"<title>AYEC_NUMBERING_RESULT:(.*?)</title>", dom, re.DOTALL)
    if not match:
        raise RuntimeError("Headless Edge did not return the numbering result marker")
    return json.loads(html.unescape(match.group(1)))


def main() -> None:
    edge = _edge_path()
    if not edge.is_file():
        raise FileNotFoundError("Microsoft Edge executable was not found")
    helper = _extract_helper(APP.read_text(encoding="utf-8"))
    page_script = f"""
const desktopSettings = {{job_number_prefix:"JOBX",job_number_next:"18",service_number_prefix:"SRVX",service_number_next:"28",project_number_prefix:"PRJX",project_number_next:"38",reference_number_prefix:"REFX",reference_number_next:"48",payment_number_prefix:"PAYX",payment_number_next:"58"}};
function esc(value) {{ return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;"); }}
function exactSettingsField(field, scope) {{ return '<div><input class="exact-setting" data-setting-scope="' + scope + '" data-setting-key="' + field[0] + '" value="' + esc(desktopSettings[field[0]] ?? field[3]) + '"></div>'; }}
{helper}
document.body.innerHTML = numberingSettingsBody();
const result = {{
  keys: Array.from(document.querySelectorAll(".exact-setting")).map(input => input.dataset.settingKey),
  scopes: Array.from(document.querySelectorAll(".exact-setting")).map(input => input.dataset.settingScope),
  actions: Array.from(document.querySelectorAll("[data-numbering-action]")).map(button => button.dataset.numberingAction),
  sampleValue: document.querySelector('[data-setting-key="job_number_next"]')?.value
}};
document.title = "AYEC_NUMBERING_RESULT:" + JSON.stringify(result);
"""
    html = "<!doctype html><html><head><meta charset=\"utf-8\"></head><body><script>" + page_script + "</script></body></html>"
    with tempfile.TemporaryDirectory(prefix="ayec-numbering-edge-") as temporary:
        page = Path(temporary) / "numbering.html"
        profile = Path(temporary) / "profile"
        page.write_text(html, encoding="utf-8")
        command = [
            str(edge),
            "--headless=new",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-background-networking",
            "--no-first-run",
            "--no-default-browser-check",
            "--dump-dom",
            f"--user-data-dir={profile}",
            page.as_uri(),
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            stdout, stderr = process.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
            process.communicate()
            raise RuntimeError("Headless Edge timed out during the isolated render")
        if process.returncode != 0:
            raise RuntimeError(f"Headless Edge failed with exit code {process.returncode}: {stderr[-800:]}")
        result = _result_from_dom(stdout)
    expected = [
        "job_number_prefix",
        "job_number_next",
        "service_number_prefix",
        "service_number_next",
        "project_number_prefix",
        "project_number_next",
        "reference_number_prefix",
        "reference_number_next",
        "payment_number_prefix",
        "payment_number_next",
    ]
    if result.get("keys") != expected or result.get("scopes") != ["settings"] * 10:
        raise AssertionError(f"Numbering fields did not render as expected: {result}")
    if result.get("actions") != ["copy", "csv", "excel", "print"]:
        raise AssertionError(f"Numbering actions did not render as expected: {result}")
    if result.get("sampleValue") != "18":
        raise AssertionError(f"Numbering setting value was not loaded: {result}")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"ok": True, **result}, ensure_ascii=True, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
