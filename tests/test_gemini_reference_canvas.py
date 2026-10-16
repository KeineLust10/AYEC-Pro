import os
import json

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6 import sip
from PyQt6.QtWidgets import QApplication, QLineEdit, QDialog

from src.ui.pages.settings_widgets import gemini_settings_widget as gemini
from src.ui.pages.settings_widgets import gemini_reference_canvas as reference


class MemorySettings:
    def __init__(self):
        self.values = {"gemini_model": gemini.DEFAULT_GEMINI_MODEL, "unrelated": "keep"}

    def get_setting(self, key, default=""):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


class FakeTestWorker(QObject):
    finished = pyqtSignal(bool, dict)
    calls = []

    def __init__(self, model, keys):
        super().__init__()
        self.model, self.keys = model, keys

    def start(self):
        self.calls.append((self.model, self.keys))


def test_real_key_matrix_masking_drafts_selected_test_and_existing_save(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    db = MemorySettings()
    vault = {"gemini_api_key": "fixture-first,fixture-second", "whatsapp_api_token": "fixture-wa"}
    read_keys, writes = [], []

    def read(_db, key, default=""):
        read_keys.append(key)
        return vault.get(key, default)

    def save(_db, key, value):
        writes.append((key, value))
        vault[key] = value

    monkeypatch.setattr(gemini.SecureSettingStore, "get", read)
    monkeypatch.setattr(gemini.SecureSettingStore, "set", save)
    monkeypatch.setattr(gemini, "show_success", lambda *args: None)
    monkeypatch.setattr(gemini, "show_error", lambda *args: None)
    monkeypatch.setattr(gemini, "TestWorker", FakeTestWorker)
    monkeypatch.setattr(reference, "show_success", lambda *args: None)
    FakeTestWorker.calls = []
    page = gemini.GeminiSettingsWidget(db)
    canvas = reference.GeminiReferenceCanvas(page)
    canvas.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    canvas.resize(1088, 698)
    canvas.show()
    app.processEvents()
    try:
        assert read_keys == ["gemini_api_key", "whatsapp_api_token"]
        assert canvas.table.rowCount() == 2
        assert canvas.table.columnCount() == 6
        assert canvas.page.model_card.parentWidget() is canvas
        assert writes == []
        assert page.inp_wa_token.text() == "fixture-wa"
        page.toggles["jarvis_intel_enabled"].setChecked(False)
        assert db.values["jarvis_intel_enabled"] == "0"
        page.toggles["jarvis_intel_enabled"].setChecked(True)
        assert db.values["jarvis_intel_enabled"] == "1"
        displayed = " ".join(canvas.table.item(row, col).text() for row in range(2) for col in range(5))
        assert "fixture-first" not in displayed
        assert "fixture-second" not in displayed
        assert "Anthropic" not in displayed and "OpenAI" not in displayed
        assert canvas.max_tokens.value() == 8192
        assert canvas.temperature.value() == 2
        assert canvas.safety_toggle.isChecked()
        assert canvas.rotation_toggle.isChecked()
        assert canvas.feature_toggles["gemini_smart_token_compression"].isChecked()
        assert canvas.feature_toggles["gemini_cost_limit_protection"].isChecked()
        assert not canvas.feature_toggles["gemini_auto_load_shedding"].isChecked()
        canvas.feature_toggles["gemini_auto_load_shedding"].setChecked(True)
        assert db.values["gemini_auto_load_shedding"] == "1"
        canvas.max_tokens.setValue(4096)
        canvas.temperature.setValue(5)
        canvas.safety_toggle.setChecked(False)
        canvas.rotation_toggle.setChecked(False)
        canvas.table.cellWidget(1, 5).click()
        assert FakeTestWorker.calls == [(gemini.DEFAULT_GEMINI_MODEL, ["fixture-second"])]
        page.worker.finished.emit(True, {"key": "fixture-second", "answer": "fixture reply"})
        assert canvas.table.item(1, 3).text() == "Test ba\u015far\u0131l\u0131"
        assert canvas.table.item(1, 4).text().endswith(" ms")
        assert canvas.table.item(0, 3).text() == "Test edilmedi"
        page.cmb_model.setCurrentText("fixture-other-model")
        assert canvas.table.item(1, 3).text() == "Test edilmedi"
        page.cmb_model.setCurrentText(gemini.DEFAULT_GEMINI_MODEL)
        assert canvas.table.item(1, 3).text() == "Test ba\u015far\u0131l\u0131"

        def add_key(dialog):
            field = dialog.findChild(QLineEdit)
            assert field.echoMode() == QLineEdit.EchoMode.Password
            field.setText("fixture-third")
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(reference.ModernDialog, "exec", add_key)
        canvas.add_key_button.click()
        assert canvas.table.rowCount() == 3
        assert page.inp_api_key.toPlainText().splitlines() == ["fixture-first", "fixture-second", "fixture-third"]
        assert writes == []
        canvas.advanced_button.click()
        assert page.isVisible()
        assert page.inp_api_key.isVisible()
        assert page.inp_wa_token.isVisible()
        assert page.btn_test.isVisible()
        canvas.save_button.click()
        assert vault["gemini_api_key"] == "fixture-first,fixture-second,fixture-third"
        assert vault["whatsapp_api_token"] == "fixture-wa"
        assert db.values["gemini_max_output_tokens"] == "4096"
        assert db.values["gemini_temperature"] == "0.5"
        assert db.values["gemini_sensitive_data_masking"] == "0"
        assert db.values["gemini_zero_downtime_rotation"] == "0"
        assert db.values["unrelated"] == "keep"
        assert db.values["gemini_model"] == gemini.DEFAULT_GEMINI_MODEL
        report_path = tmp_path / "pool_report.json"
        monkeypatch.setattr(reference.QFileDialog, "getSaveFileName", lambda *args: (str(report_path), "JSON (*.json)"))
        canvas.export_button.click()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert len(report["keys"]) == 3
        assert report["token_usage"] is None and report["cost"] is None
        assert report["scope"] == "current_local_key_pool_snapshot"
        assert "fixture-first" not in report_path.read_text(encoding="utf-8")
        assert "fixture-second" not in report_path.read_text(encoding="utf-8")
        assert "fixture-third" not in report_path.read_text(encoding="utf-8")
        assert "fixture-wa" not in report_path.read_text(encoding="utf-8")
        canvas.advanced_button.click()
        assert not page.isVisible()
    finally:
        canvas.close()
        sip.delete(canvas)
        app.processEvents()
