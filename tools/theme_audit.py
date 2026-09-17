import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tools" / "theme_audit_report.txt"

SCAN_EXT = {".py", ".qss", ".json", ".ui"}
IGNORE = {".git", ".venv", ".venv_old", "__pycache__", "node_modules", "dist", "build", "_gereksiz_adaylari"}

color_re = re.compile(r"(#?[A-Fa-f0-9]{6}|#?[A-Fa-f0-9]{3}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)|QColor\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\))")
api_re = re.compile(r"(setStyleSheet\(|QPalette|setColor\(|setBackgroundRole\()")

hits = []
api_hits = []

for p in ROOT.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in SCAN_EXT:
        continue
    parts = set(p.parts)
    if parts & IGNORE:
        continue
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    rel = p.relative_to(ROOT)
    for i, line in enumerate(txt.splitlines(), 1):
        if color_re.search(line):
            hits.append((str(rel), i, line.strip()))
        if api_re.search(line):
            api_hits.append((str(rel), i, line.strip()))

with OUT.open("w", encoding="utf-8") as f:
    f.write("THEME AUDIT REPORT\n")
    f.write(f"color_hits={len(hits)}\n")
    f.write(f"theme_api_hits={len(api_hits)}\n\n")
    f.write("[COLOR HITS]\n")
    for file, ln, text in hits[:5000]:
        f.write(f"{file}:{ln}: {text}\n")
    f.write("\n[THEME API HITS]\n")
    for file, ln, text in api_hits[:5000]:
        f.write(f"{file}:{ln}: {text}\n")

print(f"wrote {OUT}")
print(f"color_hits={len(hits)}")
print(f"theme_api_hits={len(api_hits)}")
