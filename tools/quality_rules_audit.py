from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


def scan(root: Path) -> dict:
    py_files = list((root / "src").rglob("*.py"))
    line_violations = []
    broad = []
    silent = []

    for path in py_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        if len(lines) > 1000:
            line_violations.append((str(path.relative_to(root)), len(lines)))

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if re.match(r"^except\s+Exception\b.*:", stripped) or re.match(r"^except\s*:\s*$", stripped):
                broad.append((str(path.relative_to(root)), lineno, stripped))

            if re.match(r"^except(?:\s+[^:]+)?\s*:\s*$", stripped):
                next_idx = lineno
                while next_idx < len(lines) and lines[next_idx].strip() == "":
                    next_idx += 1
                if next_idx < len(lines) and lines[next_idx].strip() in {"pass", "return", "return None", "continue", "..."}:
                    silent.append((str(path.relative_to(root)), lineno, lines[next_idx].strip()))

    return {
        "py_count": len(py_files),
        "line_violations": sorted(line_violations, key=lambda x: x[1], reverse=True),
        "broad": broad,
        "silent": silent,
        "broad_by_file": Counter([f for f, _, _ in broad]),
        "silent_by_file": Counter([f for f, _, _ in silent]),
    }


def write_markdown(report: dict, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as w:
        w.write("# Quality Rules Audit\n\n")
        w.write(f"- Python dosyasi: {report['py_count']}\n")
        w.write(f"- 1000+ satir dosya: {len(report['line_violations'])}\n")
        w.write(f"- Genis except: {len(report['broad'])}\n")
        w.write(f"- Sessiz except: {len(report['silent'])}\n\n")

        w.write("## 1000+ Satir\n")
        for file, lines in report["line_violations"]:
            w.write(f"- `{file}`: {lines}\n")
        w.write("\n")

        w.write("## Genis Except Top 20\n")
        for file, count in report["broad_by_file"].most_common(20):
            w.write(f"- `{file}`: {count}\n")
        w.write("\n")

        w.write("## Sessiz Except Top 20\n")
        for file, count in report["silent_by_file"].most_common(20):
            w.write(f"- `{file}`: {count}\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = scan(root)
    write_markdown(result, root / "docs" / "QUALITY_RULES_AUDIT.md")
    print("docs/QUALITY_RULES_AUDIT.md olusturuldu")
