import sys

from src.desktop_runtime import prepare_external_runtime


def test_pythonw_runtime_keeps_python_site_packages(monkeypatch):
    import site

    original_user_site = site.USER_SITE
    original_site_packages = site.getsitepackages
    original_path = list(sys.path)
    monkeypatch.setattr(sys, "executable", r"C:\Python\pythonw3.13.exe")

    try:
        prepare_external_runtime()

        assert site.USER_SITE == original_user_site
        assert site.getsitepackages is original_site_packages
        assert sys.path == original_path
    finally:
        site.USER_SITE = original_user_site
        site.getsitepackages = original_site_packages
        sys.path[:] = original_path


def test_packaged_executable_still_uses_its_runtime_directory(monkeypatch, tmp_path):
    import site

    original_user_site = site.USER_SITE
    original_site_packages = site.getsitepackages
    original_path = list(sys.path)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "AYECPro.Core.exe"))

    try:
        prepare_external_runtime()

        assert site.USER_SITE == str(tmp_path)
        assert site.getsitepackages() == [str(tmp_path)]
        assert sys.path[0] == str(tmp_path)
    finally:
        site.USER_SITE = original_user_site
        site.getsitepackages = original_site_packages
        sys.path[:] = original_path
