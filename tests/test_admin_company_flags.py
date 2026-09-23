import importlib.util
import sys
from pathlib import Path


COMPANIES = Path(__file__).resolve().parents[1] / "Admin_Konsol" / "pages" / "companies.py"


def test_company_status_flags_normalize_string_zero_and_one():
    sys.path.insert(0, str(COMPANIES.parents[1]))
    spec = importlib.util.spec_from_file_location("companies_flags", COMPANIES)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module._flag("0", True) is False
    assert module._flag("1") is True
    assert module._flag("false") is False
    assert module._flag("true") is True
