"""Compatibility import for the shared AYEC parser."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
for _candidate in (_project_root, _project_root / "ecosystem" / "src"):
    if (_candidate / "ayec_core" / "__init__.py").is_file():
        _candidate_text = str(_candidate)
        if _candidate_text not in sys.path:
            sys.path.insert(0, _candidate_text)
        break

from ayec_core.smart_import import StockImportParser

__all__ = ["StockImportParser"]
