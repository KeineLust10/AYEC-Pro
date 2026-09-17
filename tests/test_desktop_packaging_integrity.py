from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

from core.plugin_loader import PluginLoader
from src.utils.page_config import PAGE_MAPPING


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_discovers_every_mapped_page():
    mapped_modules = {entry[0] for entry in PAGE_MAPPING.values()}
    packaged_modules = set(collect_submodules("src.ui.pages"))

    assert mapped_modules <= packaged_modules


def test_builtin_sector_plugins_are_always_available():
    PluginLoader.clear_cache()

    assert set(PluginLoader.get_available_sectors()) == {
        "teknik_servis",
        "otomotiv",
    }


def test_installer_shortcuts_use_the_embedded_executable_icon():
    script = (PROJECT_ROOT / "AYECPro_Modern_Setup.iss").read_text(
        encoding="utf-8"
    )

    assert 'Source: "assets\\app_icon.ico"' in script
    assert script.count('IconFilename: "{app}\\{#MyAppExeName}"') == 3
