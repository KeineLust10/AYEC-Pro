# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT / "frontend" / "src"
REPORT = PROJECT_ROOT / "docs" / "WEB_TURKISH_QUALITY_REPORT.md"
EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".json"}
MOJIBAKE_PATTERN = re.compile(r"[ÃÄÅÂ�]|â[\w€™œ“”€“]")


def scan_file(path: Path) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), start=1):
        if MOJIBAKE_PATTERN.search(line):
            findings.append((i, line.strip()))
    return findings


def main() -> int:
    rows: list[str] = []
    total = 0

    for path in sorted(ROOT.rglob("*")):
        if path.suffix.lower() not in EXTENSIONS or not path.is_file():
            continue
        findings = scan_file(path)
        if not findings:
            continue
        rel = path.as_posix()
        rows.append(f"## `{rel}`")
        for ln, content in findings:
            rows.append(f"- `{rel}:{ln}` -> `{content}`")
            total += 1
        rows.append("")

    lines = [
        "# Web Türkçe Kalite Raporu",
        "",
        f"- Tarama kökü: `{ROOT.as_posix()}`",
        f"- Toplam bulgu: **{total}**",
        "",
    ]
    if rows:
        lines.extend(rows)
    else:
        lines.append("Bozuk Türkçe/encoding bulgusu tespit edilmedi.")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written: {REPORT} (findings={total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
