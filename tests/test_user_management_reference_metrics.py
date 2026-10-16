from datetime import datetime

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt

from src.database import Database
from src.ui.pages.settings_widgets.user_management import UserManagementWidget
from src.ui.pages.settings_widgets.user_management_dialogs import UserDialog
from src.utils.user_permission_catalog import USER_PERMISSION_SECTIONS, parse_saved_page_permissions
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.role_utils import normalize_role
from src.utils.design_system import DesignTokens
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_account_metrics_are_real_and_not_filtered_or_online_claims(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "user_reference.db"))
    seed_visual_fixture(db)
    page = UserManagementWidget(db)
    try:
        before = [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
        page.load_users()
        assert len(page.user_card_buttons) == page.table.rowCount()
        for combo in (page.cmb_role_filter, page.cmb_status_filter, page.user_sort_order):
            assert combo.property("referenceChevron")
        for value in page.reference_metric_values.values():
            assert isinstance(value, ReferenceMetricValueLabel)
            assert value.textFormat() == Qt.TextFormat.PlainText
            assert value.toolTip() == value.text()
        assert [page.table.item(row, 0).text() for row in range(6)] == ["1", "2", "3", "4", "5", "6"]
        assert page.detail_title.text() == "Selim Celik"
        for row in range(page.table.rowCount()):
            for column in (0, 4):
                item = page.table.item(row, column)
                assert item.font().family() == DesignTokens.MONO_FONT_NAME
                assert item.toolTip() == item.text()
        assert page.cmb_role_filter.findText("Depo") >= 0
        page.user_sort_order.setCurrentIndex(1)
        assert page.table.item(0, 0).text() == str(max(row[0] for row in before))
        page.user_sort_order.setCurrentIndex(0)
        selected_id = page.table.item(1, 0).text()
        page.user_card_buttons[selected_id].click()
        assert page._selected_user_id == selected_id
        assert page.user_card_buttons[selected_id].isChecked()
        assert page.user_card_buttons[selected_id].parentWidget().property("selected") is True
        assert sum(button.isChecked() for button in page.user_card_buttons.values()) == 1
        edits = []
        monkeypatch.setattr(page, "edit_user", edits.append)
        page.detail_edit_button.click()
        assert edits == [selected_id]
        page.user_table_toggle.setChecked(True)
        assert not page.table.isHidden()
        assert page.user_cards_scroll.isHidden()
        assert all(not page.table.isColumnHidden(column) for column in range(9))
        page.user_table_toggle.setChecked(False)
        assert page.table.isHidden()
        assert not page.user_cards_scroll.isHidden()
        roles = {normalize_role(row[0] or "Personel") for row in db.conn.execute("SELECT role FROM users")}
        assert page.reference_metric_values[0].text() == str(len(before))
        assert page.reference_metric_values[1].text() == str(len(roles))
        assert page.reference_metric_values[2].text() == "-"
        assert page.reference_metric_values[3].text() == "-"
        expected_ids = {page_id for _section, entries in USER_PERMISSION_SECTIONS for page_id, _title in entries}
        assert set(page.detail_permission_checks) == expected_ids
        dialog = UserDialog(db, user_id=int(selected_id), parent=page)
        assert set(dialog.perm_toggles) == expected_ids
        try:
            for raw, expected in (
                ('{"pages":[30,62,101]}', {30, 62, 101}),
                ('[50,105]', {50, 105}),
                ('{"services":true,"financial":true}', {41, 60, 61, 30, 101}),
                ('{"mode":"all"}', expected_ids),
                ('{}', set()),
            ):
                assert parse_saved_page_permissions(raw) == expected
                assert dialog._apply_saved_permissions(raw)
                assert {page_id for page_id, toggle in dialog.perm_toggles.items() if toggle.isChecked()} == expected
                db.conn.execute("UPDATE users SET permissions=? WHERE id=?", (raw, selected_id))
                page._select_user_card(selected_id)
                assert {page_id for page_id, indicator in page.detail_permission_checks.items() if indicator.isChecked()} == expected
            assert parse_saved_page_permissions("invalid-json") is None
            assert not dialog._apply_saved_permissions("invalid-json")
            db.conn.rollback()
        finally:
            dialog.close()
            dialog.deleteLater()
        assert "ONLINE" not in page.detail_status.text()
        assert "OFFLINE" not in page.detail_status.text()
        page.inp_search.setText("unmatched-account-query")
        assert page.table.rowCount() == 0
        assert page._selected_user_id is None
        assert not page.detail_active_button.isEnabled()
        assert not page.detail_edit_button.isEnabled()
        assert page.detail_title.text() == "Kullanici secin"
        assert page.users_count_label.text() == f"{len(before)} Kay\u0131t"
        assert page.reference_metric_values[0].text() == str(len(before))
        assert before == [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()

def test_security_report_opens_real_tenant_audit_view_without_account_writes(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "audit_reference.db"))
    seed_visual_fixture(db)
    db.conn.execute("INSERT INTO audit_logs (user_id, table_name, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    ("audit-user", "users", "UPDATE", "reference-audit-entry", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.conn.commit()
    page = UserManagementWidget(db)
    users = [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
    opened = []

    def inspect_report(dialog):
        assert dialog.audit_page.db is db
        assert dialog.audit_page.audit_logger.db is db
        assert dialog.audit_page.table.rowCount() > 0
        values = [dialog.audit_page.table.item(0, column).text() for column in range(dialog.audit_page.table.columnCount())]
        assert "audit-user" in values
        assert "reference-audit-entry" in values
        assert dialog.audit_page.inspector_details.text() == "reference-audit-entry"
        assert "UPDATE" in dialog.audit_page.inspector_metadata.text()
        assert "users" in dialog.audit_page.inspector_metadata.text()
        assert "HWID" not in dialog.audit_page.inspector_metadata.text()
        assert dialog.audit_page._audit_metric_cards[3][0].text() == "-"
        opened.append(dialog)
        return 0

    monkeypatch.setattr(ModernDialog, "exec", inspect_report)
    try:
        page.security_report_button.click()
        assert len(opened) == 1
        assert users == [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_inline_permissions_are_explicit_scoped_and_preserve_unknown_ids(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
    db = Database(str(tmp_path / "inline_permissions.db"))
    seed_visual_fixture(db)
    db.conn.execute("UPDATE users SET permissions=? WHERE id=2", ('{"pages":[40,7777]}',))
    db.conn.commit()
    before = {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
    page = UserManagementWidget(db)
    owner = QWidget()
    owner.db = db
    owner.current_user = {"id": 3, "role": "Master"}
    owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    page.setParent(owner)
    page.show()
    owner.show()
    page.load_users()
    app.processEvents()
    try:
        page._select_user_card("2")
        assert page.detail_permission_checks[105].isEnabled()
        assert not page.permission_save_button.isEnabled()
        page.detail_permission_checks[105].setChecked(True)
        assert page.permission_save_button.isEnabled()
        monkeypatch.setattr(ModernConfirmDialog, "exec", lambda _dialog: 0)
        page._select_user_card("3")
        assert page._selected_user_id == "2"
        assert page.table.item(page.table.currentRow(), 0).text() == "2"
        page.inp_search.setText("unmatched-query")
        assert page.inp_search.text() == ""
        assert page.search_text == ""
        page.user_sort_order.setCurrentIndex(1)
        assert page.user_sort_order.currentIndex() == 0
        page.cmb_role_filter.setCurrentText("Master")
        assert page.cmb_role_filter.currentIndex() == 0
        page.btn_next.click()
        assert page.page == 1
        page.btn_refresh.click()
        assert page.detail_permission_checks[105].isChecked()
        assert before == {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        page.permission_cancel_button.click()
        assert not page.detail_permission_checks[105].isChecked()
        assert before == {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        page.detail_permission_checks[105].setChecked(True)
        page.permission_save_button.click()
        expected = {key: dict(value) for key, value in before.items()}
        expected[2]["permissions"] = '{"pages": [40, 105, 7777]}'
        assert expected == {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        page.detail_permission_checks[101].setChecked(True)
        monkeypatch.setattr(ModernConfirmDialog, "exec", lambda _dialog: 1)
        page._select_user_card("4")
        assert page._selected_user_id == "4"
        assert expected == {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        page._select_user_card("2")
        page.detail_permission_checks[101].setChecked(True)
        owner.current_user = {"id": 4, "role": "Muhasebe"}
        page._save_permission_changes()
        assert expected == {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        assert not page.permission_save_button.isEnabled()
        page._cancel_permission_changes()
        page._select_user_card("3")
        assert all(not check.isEnabled() for check in page.detail_permission_checks.values())
    finally:
        page.close()
        page.deleteLater()
        owner.close()
        owner.deleteLater()
        app.processEvents()
        db.close()
