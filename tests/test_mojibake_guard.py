# -*- coding: utf-8 -*-

import subprocess
import sys
from pathlib import Path


def test_active_source_files_do_not_contain_mojibake():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "tools" / "mojibake_guard.py")],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_ascii_diff_guard_detects_non_ascii_added_lines():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from tools import ascii_diff_guard

    bad_label = "M" + chr(252) + chr(351) + "teri"
    diff = (
        "diff --git a/src/example.py b/src/example.py\n"
        "+++ b/src/example.py\n"
        "@@ -0,0 +1,2 @@\n"
        f"+label = \"{bad_label}\"\n"
        "+label = \"Musteri\"\n"
    )
    added = list(ascii_diff_guard.added_lines_from_diff(diff))

    assert len(added) == 2
    assert ascii_diff_guard.has_non_ascii(added[0][2])
    assert not ascii_diff_guard.has_non_ascii(added[1][2])
