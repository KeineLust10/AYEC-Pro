import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.pages.settings_widgets.voice_assistant_shortcuts import VoiceAssistantShortcutsWidget
from src.utils.path_helper import PathHelper


APP = QApplication.instance() or QApplication([])


def test_voice_shortcuts_reference_pagination(tmp_path, monkeypatch):
    shortcuts = {
        f"Command {index}": {
            "triggers": [f"trigger {index}"],
            "action": {"type": "builtin", "name": f"action_{index}"},
        }
        for index in range(1, 7)
    }
    (tmp_path / "asistan_ayarlari.json").write_text(
        json.dumps(shortcuts), encoding="utf-8"
    )
    monkeypatch.setattr(PathHelper, "get_app_data_dir", lambda: str(tmp_path))

    widget = VoiceAssistantShortcutsWidget(object())
    assert widget.proxy.rowCount() == 6
    assert [widget.table.isRowHidden(index) for index in range(6)] == [
        False, False, False, False, True, True
    ]
    assert widget.page_label.text() == "1 / 2"

    widget.next_page.click()
    assert [widget.table.isRowHidden(index) for index in range(6)] == [
        True, True, True, True, False, False
    ]
    widget.close()
