import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QPushButton, QStyleOptionViewItem

from src.ui.pages.settings_widgets import voice_assistant_shortcuts as shortcuts
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.user_permission_catalog import USER_PERMISSION_SECTIONS


def test_native_shortcut_reference_keeps_all_fields_filters_and_actions(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "shortcuts.json"
    config = {
        f"Command {index}": {
            "triggers": [f"Command trigger {index}"],
            "action": {"type": "page", "index": 100 + index},
        }
        for index in range(7)
    }
    config["Command 0"] = {
        "triggers": ["Asistan finans \u00f6zet"],
        "action": {"type": "builtin", "name": "accounting_summary"},
    }
    path.write_text(json.dumps(config, ensure_ascii=True), encoding="utf-8")
    before = path.read_bytes()
    page = shortcuts.VoiceAssistantShortcutsWidget(None, config_path=str(path))
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    page.resize(1088, 642)
    page.show()
    app.processEvents()
    try:
        assert page.model.columnCount() == 6
        assert page.model.rowCount() == 7
        badge_option = QStyleOptionViewItem()
        status_index = page.proxy.index(0, 4)
        page.table.itemDelegate().initStyleOption(badge_option, status_index)
        assert badge_option.text == ""
        assert status_index.data() == "Aktif"
        assert "7 Kay" in page.matrix_title.text()
        cards = page.findChildren(QFrame, "voiceFeaturedCard")
        assert len(cards) == 4
        assert all(card.height() == 147 for card in cards)
        assert sum(not page.table.isRowHidden(row) for row in range(7)) == 4
        page.next_page.click()
        assert page.current_page == 1
        assert sum(not page.table.isRowHidden(row) for row in range(7)) == 3
        assert not page.next_page.isEnabled()
        page.cmb_filter.setCurrentText("Fonksiyon")
        assert page.proxy.rowCount() == 1
        assert page.current_page == 0
        messages = []
        monkeypatch.setattr(shortcuts, "show_success", lambda *args: messages.append(args[-1]))
        monkeypatch.setattr(shortcuts, "show_error", lambda *args: messages.append(args[-1]))
        cards[0].findChild(QPushButton).click()
        assert page.proxy.rowCount() == 1
        assert page.inp_search.text() == "Asistan finans \u00f6zet"
        assert page.cmb_filter.currentIndex() == 0
        assert messages and "bulundu" in messages[-1]
        edits = []
        monkeypatch.setattr(page, "_edit_shortcut", lambda index: edits.append(
            page.model.item(page.proxy.mapToSource(index).row(), 0).text()
        ))
        page.table.clicked.emit(page.proxy.index(0, 5))
        assert edits == ["Command 0"]
        page.table.clicked.emit(page.proxy.index(0, 0))
        assert len(edits) == 1
        page.inp_search.setText("unknown trigger")
        assert page.proxy.rowCount() == 0
        assert not page.next_page.isEnabled()
        assert not page.previous_page.isEnabled()
        assert "0-0" in page.page_result_label.text()
        page.inp_search.clear()
        page._load_shortcuts()
        assert page.model.rowCount() == 7
        assert path.read_bytes() == before
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()


def test_explicit_missing_config_does_not_read_unrelated_legacy_file(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    legacy = tmp_path / "asistan_ayarlari.json"
    legacy.write_text('{"unrelated": ["private trigger"]}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    page = shortcuts.VoiceAssistantShortcutsWidget(None, config_path=str(tmp_path / "missing.json"))
    try:
        assert page.model.rowCount() == 0
        assert "0 Kay" in page.matrix_title.text()
        assert not page.next_page.isEnabled()
        assert not (tmp_path / "missing.json").exists()
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()


def test_shortcut_editor_shared_footer_real_page_ids_and_metadata_preservation(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / "editor.json"
    original = {
        "existing": {
            "triggers": ["old trigger"],
            "action": {"type": "page", "index": 201},
            "requires_confirmation": True,
            "scope": "warehouse-3",
        },
        "untouched": {"triggers": ["leave alone"], "action": {"type": "builtin", "name": "panel_ac"}},
    }
    path.write_text(json.dumps(original, ensure_ascii=True), encoding="utf-8")
    page = shortcuts.VoiceAssistantShortcutsWidget(None, config_path=str(path))
    dialog = shortcuts.ShortcutEditDialog("existing", "new trigger, second trigger", "Sayfa", "201", page)
    try:
        assert isinstance(dialog, ModernDialog)
        choices = [dialog.cmb_action.itemText(index) for index in range(dialog.cmb_action.count())]
        assert choices == [f"{page_id} - {label}" for _section, entries in USER_PERMISSION_SECTIONS for page_id, label in entries]
        assert dialog.footer_layout.indexOf(dialog.save_button) >= 0
        assert dialog.footer_layout.indexOf(dialog.cancel_button) >= 0
        dialog.inp_name.setText("renamed")
        dialog.save_button.click()
        assert dialog.result() == shortcuts.QDialog.DialogCode.Accepted
        data = dialog.get_data()
        assert data["action"] == "201"
        page._update_shortcut_in_config("existing", data)
        page._load_shortcuts()
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert "existing" not in saved
        assert saved["renamed"]["action"] == {"type": "page", "index": 201}
        assert saved["renamed"]["triggers"] == ["new trigger", "second trigger"]
        assert saved["renamed"]["requires_confirmation"] is True
        assert saved["renamed"]["scope"] == "warehouse-3"
        assert saved["untouched"] == original["untouched"]
        dialog.cmb_type.setCurrentText("Fonksiyon")
        dialog.cmb_action.setCurrentText("accounting_summary")
        assert dialog.get_data()["action"] == "accounting_summary"
        dialog.cancel_button.click()
        assert dialog.result() == shortcuts.QDialog.DialogCode.Rejected
    finally:
        dialog.close()
        page.close()
        dialog.deleteLater()
        page.deleteLater()
        app.processEvents()
