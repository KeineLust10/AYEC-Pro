import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QListWidget, QLineEdit, QWidget

from src.ui.pages.settings_widgets.autonomous_agents_widget import AutonomousAgentsWidget
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.database import Database


APP = QApplication.instance() or QApplication([])


class _Db:
    def __init__(self):
        self.settings = {"agent_voice_feedback": "0"}

    def get_internal_setting(self, key, default=""):
        return self.settings.get(key, default)

    def set_internal_setting(self, key, value):
        self.settings[key] = value


def test_autonomous_agent_scenarios_load_and_persist():
    db = _Db()
    widget = AutonomousAgentsWidget(db)
    toggles = widget.findChildren(AnimatedToggle)

    assert len(toggles) == 7
    assert sum(toggle.isChecked() for toggle in toggles) == 6
    assert widget.active_rules_label.text() == "6 Kural Aktif"
    assert widget.validate_webhook_button.text() == "Test Paketi G\u00f6nder"

    disabled = next(toggle for toggle in toggles if not toggle.isChecked())
    disabled.setChecked(True)
    assert db.settings["agent_voice_feedback"] == "1"
    assert widget.active_rules_label.text() == "7 Kural Aktif"
    widget.close()


def test_runtime_status_polling_runs_only_while_widget_is_visible():
    widget = AutonomousAgentsWidget(_Db())

    assert not widget.status_timer.isActive()
    widget.show()
    APP.processEvents()
    assert widget.status_timer.isActive()

    widget.hide()
    APP.processEvents()
    assert not widget.status_timer.isActive()
    widget.close()


def test_autonomous_agent_log_action_opens_audit_settings_page():
    host = QWidget()
    rows = [None, 17]
    sidebar_list = QListWidget(host)
    sidebar_list.addItem("")
    sidebar_list.addItem("")
    selected_pages = []
    sidebar_list.currentRowChanged.connect(
        lambda row: selected_pages.append(rows[row]) if row >= 0 else None
    )
    search = QLineEdit(host)
    search.setText("log")
    host.sidebar = SimpleNamespace(
        items_map=rows,
        list_widget=sidebar_list,
        search_inp=search,
    )
    widget = AutonomousAgentsWidget(_Db())
    widget.setParent(host)

    widget.btn_audit_log.click()

    assert selected_pages == [17]
    assert search.text() == ""
    widget.close()
    host.close()


def test_voice_feature_button_opens_the_feature_switch_dialog(tmp_path, monkeypatch):
    from src.services.voice_feature_settings import VoiceFeatureSettingsDialog

    db = Database(str(tmp_path / "voice_feature_button.db"))
    widget = AutonomousAgentsWidget(db, SimpleNamespace(db=db, assistant=None))
    calls = []
    dialog = SimpleNamespace(exec=lambda: calls.append("exec"))

    monkeypatch.setattr(
        VoiceFeatureSettingsDialog,
        "create",
        lambda parent, dialog_db: (calls.append((parent, dialog_db)), dialog)[1],
    )

    try:
        widget.voice_features_button.click()
        assert calls == [(widget, db), "exec"]
    finally:
        widget.status_timer.stop()
        widget.close()
        db.conn.close()


def test_floating_assistant_toggle_hides_widget_immediately():
    db = _Db()
    db.settings["assistant_fab_enabled"] = "1"
    db.get_setting = lambda key, default="": db.settings.get(key, default)
    db.set_setting = lambda key, value: db.settings.__setitem__(key, value)
    visibility = []
    main = SimpleNamespace(
        _current_page_index=0,
        assistant_fab=SimpleNamespace(setVisible=visibility.append),
    )
    widget = AutonomousAgentsWidget(db, main)
    try:
        widget.scenario_toggles["assistant_fab_enabled"].setChecked(False)
        assert db.settings["assistant_fab_enabled"] == "0"
        assert main._assistant_fab_enabled is False
        assert visibility[-1] is False
    finally:
        widget.status_timer.stop()
        widget.close()


def test_agent_runtime_is_observed_and_configuration_preserves_local_values(tmp_path):
    db = Database(str(tmp_path / "agent_reference.db"))
    db.set_internal_setting("agent_voice_feedback", "0")
    db.set_internal_setting("ultramsg_instance", "fixture-instance")
    db.set_internal_setting("ultramsg_token", "fixture-token-not-a-secret")
    db.set_internal_setting("ultramsg_phone", "fixture-phone")
    db.set_internal_setting("unrelated_internal_key", "keep-value")
    before = [tuple(row) for row in db.conn.execute("SELECT * FROM internal_settings ORDER BY key")]
    notifications = []
    runtime = {"voice": False, "monitor": False}
    calls = []
    worker = SimpleNamespace(isRunning=lambda: runtime["voice"])
    monitor = SimpleNamespace(isRunning=lambda: runtime["monitor"])
    manager = SimpleNamespace(
        voice_assistant_thread=worker,
        assistant_monitor_worker=monitor,
        stop_voice_assistant=lambda: calls.append("stop"),
        start_voice_assistant=lambda: (calls.append("start"), runtime.update(voice=True)),
        run_assistant_monitoring=lambda: calls.append("monitor"),
    )
    main = SimpleNamespace(
        db=db, assistant=manager, _ensure_assistant_manager=lambda: manager,
        show_notification=lambda *args: notifications.append(args),
    )
    host = QWidget()
    host.db = db
    opened = []
    host.open_tab_by_key = lambda key: (opened.append(key), True)[-1]
    widget = AutonomousAgentsWidget(db, main)
    widget.setParent(host)
    try:
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM internal_settings ORDER BY key")] == before
        assert "6/7" in widget.configured_count.text()
        assert "HAZIR" in widget.runtime_title.text()
        assert "Durduruldu" in widget.runtime_states["voice"][1].text()
        assert "Ayarland" in widget.runtime_states["whatsapp"][1].text()
        assert "Bagli" not in widget.runtime_states["whatsapp"][1].text()
        assert widget.inp_ultra_token.echoMode() == QLineEdit.EchoMode.Password
        widget.scenario_toggles["agent_voice_feedback"].setChecked(True)
        assert db.get_internal_setting("agent_voice_feedback") == "1"
        assert "7/7" in widget.configured_count.text()
        assert db.get_internal_setting("unrelated_internal_key") == "keep-value"
        assert db.get_internal_setting("ultramsg_token") == "fixture-token-not-a-secret"
        widget.restart_button.click()
        assert calls == ["stop", "start", "monitor"]
        assert "\u00c7ALI\u015eIYOR" in widget.runtime_title.text()
        runtime["voice"] = False
        widget._refresh_runtime_status()
        assert "HAZIR" in widget.runtime_title.text()
        widget.new_agent_button.click()
        assert opened == ["voice_training"]
        widget.inp_ultra_instance.setText("new-fixture-instance")
        widget.inp_ultra_token.setText("new-fixture-token")
        widget.inp_ultra_phone.setText("new-fixture-phone")
        widget.save_webhook_button.click()
        assert db.get_internal_setting("ultramsg_instance") == "new-fixture-instance"
        assert db.get_internal_setting("ultramsg_token") == "new-fixture-token"
        assert db.get_internal_setting("ultramsg_phone") == "new-fixture-phone"
        assert db.get_internal_setting("unrelated_internal_key") == "keep-value"
        after_save = [tuple(row) for row in db.conn.execute("SELECT * FROM internal_settings ORDER BY key")]
        widget.validate_webhook_button.click()
        assert "yap\u0131lmad\u0131" in notifications[-1][0]
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM internal_settings ORDER BY key")] == after_save
    finally:
        widget.status_timer.stop()
        widget.close()
        host.close()
        widget.deleteLater()
        host.deleteLater()
        APP.processEvents()
        db.conn.close()
