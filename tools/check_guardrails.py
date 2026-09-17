from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_LINES = 1000
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    violations = []
    broad_excepts = []
    silent_excepts = []

    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        rel = path.relative_to(ROOT)

        if len(lines) > MAX_LINES:
            violations.append((str(rel), len(lines)))

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if re.match(r"^except\s+Exception\b.*:", stripped) or re.match(r"^except\s*:\s*$", stripped):
                broad_excepts.append((str(rel), lineno, stripped))
            if re.match(r"^except(?:\s+[^:]+)?\s*:\s*$", stripped):
                j = lineno
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines) and lines[j].strip() in {"pass", "return", "return None", "continue", "..."}:
                    silent_excepts.append((str(rel), lineno, lines[j].strip()))

    if violations:
        print("[ERROR] 1000 satir limit ihlali:")
        for file, count in sorted(violations, key=lambda x: x[1], reverse=True):
            print(f"- {file}: {count}")

    if broad_excepts:
        print(f"[WARN] Genis except sayisi: {len(broad_excepts)}")
        for item in broad_excepts[:30]:
            print(f"- {item[0]}:{item[1]} -> {item[2]}")

    if silent_excepts:
        print(f"[WARN] Sessiz except sayisi: {len(silent_excepts)}")
        for item in silent_excepts[:30]:
            print(f"- {item[0]}:{item[1]} -> {item[2]}")

    if violations:
        return 2
    if silent_excepts:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
