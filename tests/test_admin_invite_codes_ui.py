import sys
from pathlib import Path

from PyQt6.QtWidgets import QComboBox, QSpinBox
from PyQt6.QtGui import QFontInfo

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.invite_codes import InviteCodesPage
from src.ui.components.modern_dialog import ModernDialog


def test_invite_create_dialog_binds_expiry_and_use_limit_to_shared_footer(
    persistent_qapplication, monkeypatch
):
    monkeypatch.setattr(InviteCodesPage, "reload", lambda self: None)
    page = InviteCodesPage()
    page.hours = QComboBox()
    page.hours.addItem("24 Hours", 24)
    page.hours.addItem("7 Days", 168)
    page.hours.setCurrentIndex(1)
    page.max_uses = QSpinBox()
    page.max_uses.setRange(1, 20)
    page.max_uses.setValue(4)
    submitted = []
    monkeypatch.setattr(page, "create_code", lambda hours, uses: submitted.append((hours, uses)))
    accepted = []

    class DialogState:
        def accept(self):
            accepted.append(True)

    page._submit_create_dialog(DialogState())

    assert submitted == [(168, 4)]
    assert accepted == [True]


def test_invite_dialog_footer_uses_legible_system_font(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(InviteCodesPage, "reload", lambda self: None)
    dialogs = []
    monkeypatch.setattr(ModernDialog, "exec", lambda dialog: dialogs.append(dialog) or 0)
    page = InviteCodesPage()

    page._open_create_dialog()

    assert len(dialogs) == 1
    buttons = [dialogs[0].footer_layout.itemAt(index).widget() for index in range(2)]
    assert [button.text() for button in buttons] == ["Cancel", "Generate Invite Code"]
    assert QFontInfo(dialogs[0].font()).family() in {"Segoe UI", "Arial"}
    assert QFontInfo(dialogs[0].lbl_title.font()).family() in {"Segoe UI", "Arial"}
    assert all(QFontInfo(button.font()).family() in {"Segoe UI", "Arial"} for button in buttons)
