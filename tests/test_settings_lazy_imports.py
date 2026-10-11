import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_settings_page_import_defers_unopened_settings_modules():
    script = (
        "import sys; from src.ui.pages.settings_page import SettingsPage; "
        "names=('src.ui.pages.settings_widgets.bank_settings', "
        "'src.ui.pages.settings_widgets.sms_settings', "
        "'src.ui.pages.settings_widgets.backup_settings', "
        "'src.ui.pages.settings_widgets.integration_hub', "
        "'src.ui.pages.settings_widgets.gemini_settings_widget'); "
        "assert not any(name in sys.modules for name in names)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_settings_widget_package_exports_remain_lazy_and_compatible():
    script = (
        "import sys; from src.ui.pages.settings_widgets import BackupSettingsWidget; "
        "assert BackupSettingsWidget.__name__ == 'BackupSettingsWidget'; "
        "assert 'src.ui.pages.settings_widgets.backup_settings' in sys.modules; "
        "assert 'src.ui.pages.settings_widgets.integration_hub' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
