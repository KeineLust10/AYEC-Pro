# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re


DEFAULT_ROOT = Path("src/ui")
DEFAULT_REPORT_PATH = Path("tools/turkish_quality_report.md")
FILE_EXTS = {".py", ".qss", ".json", ".md", ".txt"}

# Keep this list conservative to avoid false positives.
MOJIBAKE_RE = re.compile(r"(Ã|Ä|Å|ğŸ|�)")
WORD_TYPO_MAP = {
    "Seilmedi": "Seçilmedi",
    "Secilmedi": "Seçilmedi",
    "Musteri": "Müşteri",
    "Gorunum": "Görünüm",
    "Yonetim": "Yönetim",
    "Guncelle": "Güncelle",
    "Islem": "İşlem",
    "Islemler": "İşlemler",
    "Iptal": "İptal",
}


@dataclass
class Finding:
    file: Path
    line: int
    kind: str
    detail: str


def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in FILE_EXTS:
            yield p


def scan_file(path: Path) -> tuple[list[Finding], str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[Finding] = []
    for i, line in enumerate(text.splitlines(), 1):
        if MOJIBAKE_RE.search(line):
            findings.append(Finding(path, i, "mojibake", line.strip()))
        for bad, good in WORD_TYPO_MAP.items():
            if bad in line:
                findings.append(Finding(path, i, "typo", f"{bad} -> {good}"))
    return findings, text


def apply_fixes(text: str) -> tuple[str, int]:
    count = 0
    fixed = text
    for bad, good in WORD_TYPO_MAP.items():
        n = fixed.count(bad)
        if n:
            fixed = fixed.replace(bad, good)
            count += n
    return fixed, count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Apply conservative typo fixes.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Scan root directory (default: src/ui).")
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Report output path (default: tools/turkish_quality_report.md).",
    )
    args = parser.parse_args()

    root = Path(args.root)
    report_path = Path(args.report)
    if not root.exists():
        raise SystemExit(f"scan root not found: {root}")

    all_findings: list[Finding] = []
    fixed_files: list[tuple[Path, int]] = []

    for path in iter_files(root):
        findings, text = scan_file(path)
        all_findings.extend(findings)
        if args.fix:
            fixed, changed = apply_fixes(text)
            if changed:
                path.write_text(fixed, encoding="utf-8", newline="\n")
                fixed_files.append((path, changed))

    # Re-scan after fix for final report
    final_findings: list[Finding] = []
    for path in iter_files(root):
        findings, _ = scan_file(path)
        final_findings.extend(findings)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Türkçe Kalite Taraması ({root})\n\n")
        f.write(f"- Taranan kök: `{root}`\n")
        f.write(f"- Taranan uzantılar: `{', '.join(sorted(FILE_EXTS))}`\n")
        f.write(f"- İlk bulgu sayısı: **{len(all_findings)}**\n")
        f.write(f"- Otomatik düzeltme aktif: **{'Evet' if args.fix else 'Hayır'}**\n")
        f.write(f"- Düzeltme sonrası bulgu sayısı: **{len(final_findings)}**\n\n")

        if fixed_files:
            f.write("## Otomatik Düzeltilen Dosyalar\n")
            for path, cnt in fixed_files:
                f.write(f"- `{path}` ({cnt} değişim)\n")
            f.write("\n")

        f.write("## Kalan Bulgular\n")
        if not final_findings:
            f.write("- Kalan bulgu yok.\n")
        else:
            for item in final_findings:
                f.write(f"- `{item.file}:{item.line}` [{item.kind}] {item.detail}\n")

    print(f"report: {report_path}")
    print(f"initial_findings={len(all_findings)} final_findings={len(final_findings)} fixed_files={len(fixed_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
