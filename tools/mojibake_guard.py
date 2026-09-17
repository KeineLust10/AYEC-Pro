from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (
    ROOT / "src",
    ROOT / "core",
    ROOT / "Main.py",
)

TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".json",
    ".qss",
    ".txt",
    ".toml",
    ".yml",
    ".yaml",
    ".ini",
    ".cfg",
    ".spec",
}

SKIP_PARTS = {
    ".git",
    ".venv_active",
    "__pycache__",
    "build",
    "dist",
    "backups",
    ".claude",
    ".agent",
    "agent_orchestrator",
    "tools",
}

BAD_PATTERNS = (
    "Ã",
    "Ä",
    "Å",
    "â€™",
    "â€œ",
    "â€",
    "â€“",
    "â€”",
    "â„",
    "\u00e2\u0161",
    "\u00e2\u008f",
    "\u00f0\u0178",
    "\u011f\u0178",
    "Â ",
    "�",
)


def should_scan(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    lowered = {part.lower() for part in path.parts}
    return not any(skip.lower() in lowered for skip in SKIP_PARTS)


def iter_text_files():
    for root in SCAN_ROOTS:
        if root.is_file():
            if should_scan(root):
                yield root
            continue
        for path in root.rglob("*"):
            if path.is_file() and should_scan(path):
                yield path


def safe_print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="backslashreplace"))


def find_hits(path: Path) -> list[tuple[int, str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [(0, "", "UTF-8 decode failed")]

    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in BAD_PATTERNS:
            if pattern in line:
                hits.append((lineno, pattern, line.strip()))
                break
    return hits


def main() -> int:
    problem_files = []
    for path in iter_text_files():
        hits = find_hits(path)
        if hits:
            problem_files.append((path, hits))

    if not problem_files:
        safe_print("OK: no mojibake patterns found in active source files")
        return 0

    safe_print("MOJIBAKE_GUARD: suspicious text found")
    for path, hits in problem_files:
        safe_print(f"\n{path.relative_to(ROOT)}")
        for lineno, pattern, line in hits[:10]:
            if lineno == 0:
                safe_print(f"  [decode] {line}")
            else:
                safe_print(f"  L{lineno} [{pattern}] {line}")
        if len(hits) > 10:
            safe_print(f"  ... {len(hits) - 10} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
