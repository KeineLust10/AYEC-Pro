from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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
    ".venv_ai",
    "__pycache__",
    "build",
    "dist",
    "backups",
    ".claude",
    ".agent",
    ".agents",
    "agent_orchestrator",
}

BAD_PATTERNS = (
    chr(0x00C3),
    chr(0x00C4),
    chr(0x00C5),
    chr(0x00E2),
    chr(0xFFFD),
)


def safe_print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="backslashreplace"))


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def should_scan_path(path_text: str) -> bool:
    path = Path(path_text.replace("/", "\\"))
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    lowered = {part.lower() for part in path.parts}
    return not any(skip.lower() in lowered for skip in SKIP_PARTS)


def added_lines_from_diff(diff_text: str):
    current_file = None
    new_lineno = None
    for raw in diff_text.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
            continue
        if raw.startswith("@@"):
            marker = raw.split("+", 1)[1].split(" ", 1)[0]
            start = marker.split(",", 1)[0]
            try:
                new_lineno = int(start)
            except ValueError:
                new_lineno = None
            continue
        if current_file is None or new_lineno is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            yield current_file, new_lineno, raw[1:]
            new_lineno += 1
        elif not raw.startswith("-"):
            new_lineno += 1


def has_non_ascii(text: str) -> bool:
    return any(ord(ch) > 127 for ch in text)


def has_mojibake(text: str) -> bool:
    return any(pattern in text for pattern in BAD_PATTERNS)


def collect_diff(base: str | None) -> str:
    if base:
        result = run_git(["diff", "--unified=0", f"{base}...HEAD"])
        if result.returncode != 0:
            result = run_git(["diff", "--unified=0", base])
        return result.stdout

    result = run_git(["diff", "--unified=0", "HEAD"])
    if result.returncode == 0:
        return result.stdout

    # Repositories without an initial commit still need a useful staged check.
    result = run_git(["diff", "--cached", "--unified=0"])
    return result.stdout if result.returncode == 0 else ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when newly added source lines contain non-ASCII text or mojibake."
    )
    parser.add_argument("--base", help="Git base ref for diff checks, for example origin/main.")
    args = parser.parse_args()

    diff_text = collect_diff(args.base)
    if not diff_text.strip():
        safe_print("OK: no added source lines to check")
        return 0

    problems = []
    for file_name, lineno, line in added_lines_from_diff(diff_text):
        if not should_scan_path(file_name):
            continue
        if has_non_ascii(line) or has_mojibake(line):
            reason = "mojibake" if has_mojibake(line) else "non-ascii"
            problems.append((file_name, lineno, reason, line))

    if not problems:
        safe_print("OK: added source lines are ASCII-clean")
        return 0

    safe_print("ASCII_DIFF_GUARD: added source lines must be ASCII-only")
    safe_print("Use Unicode escapes for Turkish UI text, for example M\\u00fc\\u015fteri.")
    for file_name, lineno, reason, line in problems[:80]:
        safe_print(f"{file_name}:L{lineno} [{reason}] {line}")
    if len(problems) > 80:
        safe_print(f"... {len(problems) - 80} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
