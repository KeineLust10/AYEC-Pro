# -*- coding: utf-8 -*-
"""Remove module-level _on_ui_widget_changed; add in-class handler where needed."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "ui"
REPORT = ROOT / "scripts" / "fix_orphan_report.txt"

ORPHAN = re.compile(
    r"\n    def _on_ui_widget_changed\(self, \*args\):.*?(?=\nclass )",
    re.DOTALL,
)

METHOD = '''
    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
'''


def patch(text: str) -> str:
    if ORPHAN.search(text):
        text = ORPHAN.sub("\n", text, count=1)
    if "connect(self._on_ui_widget_changed)" in text and "    def _on_ui_widget_changed(self" not in text:
        text = re.sub(r"(\nclass \w+[^\n]*\n)", r"\1" + METHOD, text, count=1)
    return text


def main():
    changed = []
    for path in sorted(UI.rglob("*.py")):
        raw = path.read_text(encoding="utf-8", errors="replace")
        new = patch(raw)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
    REPORT.write_text("\n".join(changed), encoding="utf-8")
    print(len(changed))


if __name__ == "__main__":
    main()
