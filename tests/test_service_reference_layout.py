import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QPushButton

from src.database import Database
from src.ui.dialogs.new_service_dialog import NewServiceDialog
from src.ui.dialogs.technical_service_new_service_dialog import TechnicalServiceNewServiceDialog
from src.utils.reference_typography import apply_reference_font


def test_service_cards_preserve_empty_selectors_fault_signals_and_footer(tmp_path):
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    db = Database(str(tmp_path / "service_reference.db"))
    db.conn.execute("INSERT INTO customers (name, phone, tc_no) VALUES (?, ?, ?)",
                    ("Fixture Customer", "05550001122", "12345678901"))
    db.conn.commit()
    dialog = TechnicalServiceNewServiceDialog(db)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.set_dialog_size(1256, 960)
    dialog.show()
    for _ in range(5):
        app.processEvents()
    try:
        customer = dialog.findChild(QFrame, "serviceCustomerCard")
        device = dialog.findChild(QFrame, "serviceDeviceCard")
        fault = dialog.findChild(QFrame, "serviceFaultCard")
        delivery = dialog.findChild(QFrame, "serviceDeliveryCard")
        lock = dialog.findChild(QFrame, "serviceLockCard")
        shortcuts = dialog.findChild(QFrame, "serviceFaultShortcutsCard")
        assert all(card is not None for card in (customer, device, fault, delivery, lock)), [
            name for name, card in (("customer", customer), ("device", device), ("fault", fault),
                                    ("delivery", delivery), ("lock", lock)) if card is None
        ]
        left_edge = customer.mapTo(dialog, customer.rect().topLeft()).x()
        right_edge = fault.mapTo(dialog, fault.rect().topLeft()).x()
        assert 14 <= right_edge - left_edge - customer.width() <= 18
        assert dialog.cmb_customer.parentWidget() is customer
        assert dialog.logo_label.isHidden()
        assert dialog.lbl_title.text() == "YEN\u0130 SERV\u0130S KAYDI OLU\u015eTUR"
        for button in list(dialog.estimate_currency_buttons.values()) + [dialog.btn_close]:
            assert "padding: 0" in button.styleSheet()
        dialog.btn_reference_maximize.click()
        app.processEvents()
        assert dialog.isMaximized()
        dialog.btn_reference_maximize.click()
        app.processEvents()
        assert not dialog.isMaximized()
        dialog.btn_reference_minimize.click()
        app.processEvents()
        assert dialog.isMinimized()
        dialog.showNormal()
        app.processEvents()
        assert dialog.cmb_customer.currentIndex() == -1
        assert dialog.cmb_customer.isEditable()
        assert dialog.cmb_customer.lineEdit().placeholderText() == "Ad Soyad veya Firma \u00dcnvan\u0131 giriniz..."
        assert len(dialog.cmb_customer.lineEdit().actions()) == 1
        assert dialog.cmb_customer.itemData(dialog.cmb_customer.count() - 1) == "__new_customer__"
        assert dialog.inp_customer_phone.text() == ""
        dialog.btn_select_customer.click()
        dialog.cmb_customer.setCurrentIndex(0)
        app.processEvents()
        assert dialog.inp_customer_phone.text() == "05550001122"
        assert dialog.inp_customer_identity.text() == "12345678901"
        assert "Kay\u0131tl\u0131" in dialog.lbl_reference_customer_status.text()
        assert not dialog.inp_customer_phone.isReadOnly()
        dialog.cmb_customer.setCurrentIndex(-1)
        assert dialog.inp_customer_phone.text() == ""
        assert "Yeni M\u00fc\u015fteri Kayd\u0131" in dialog.lbl_reference_customer_status.text()
        dialog.cmb_customer.setCurrentIndex(0)
        assert dialog.inp_customer_phone.text() == "05550001122"
        assert dialog.cmb_model.parentWidget() is device
        assert dialog.cmb_model.lineEdit().placeholderText() == "\u00d6rn: Aspire 7 A715-42G"
        assert dialog.inp_serial.placeholderText() == "Seri Numaras\u0131 veya IMEI girin"
        assert device.layout().indexOf(dialog.acc_grid) >= 0
        assert device.isAncestorOf(delivery)
        assert dialog.btn_delivery_details.text() == "Ek Servis Bilgileri"
        assert delivery.isAncestorOf(dialog.cmb_personnel)
        assert not dialog.cmb_personnel.isVisible()
        dialog.btn_delivery_details.click()
        app.processEvents()
        assert dialog.btn_delivery_details.text() == "Ek Servis Bilgilerini Gizle"
        assert dialog.cmb_personnel.isVisible()
        assert "Servis ve teslim bilgileri" in {
            label.text() for label in delivery.findChildren(QLabel)
        }
        app.processEvents()
        dialog.scroll_area.verticalScrollBar().setValue(
            dialog.scroll_area.verticalScrollBar().maximum()
        )
        app.processEvents()
        dialog.grab().save(str(tmp_path / "service_delivery_details_expanded.png"))
        dialog.btn_delivery_details.click()
        app.processEvents()
        assert dialog.btn_delivery_details.text() == "Ek Servis Bilgileri"
        for combo in (dialog.cmb_customer, dialog.cmb_model, dialog.cmb_personnel, dialog.cmb_urgency):
            assert combo.height() == 32
        assert dialog.txt_fault.parentWidget() is fault
        assert dialog.cmb_service_profile.parentWidget() is shortcuts
        assert dialog.fault_shortcuts_container.parentWidget() is shortcuts
        assert shortcuts.isHidden()
        assert len(dialog.quick_issue_buttons) == 4
        assert not dialog.quick_issue_buttons[0].isVisible()
        dialog.quick_issue_buttons[0].click()
        assert "G\u00f6r\u00fcnt\u00fc Gelmiyor" in dialog.txt_fault.toPlainText()
        dialog.btn_fault_advanced.click()
        app.processEvents()
        assert shortcuts.isVisible()
        assert dialog.quick_issue_buttons[0].isVisible()
        dialog.btn_fault_advanced.click()
        app.processEvents()
        assert shortcuts.isHidden()
        assert dialog.inp_est_price.parentWidget() is fault
        assert dialog.inp_password.parentWidget() is lock
        assert dialog.inp_bios_password.parentWidget() is lock
        assert "bios_password" in {
            row[1] for row in db.cursor.execute("PRAGMA table_info(devices)").fetchall()
        }
        photo_card = dialog.findChild(QFrame, "servicePhotoCard")
        assert photo_card is not None
        assert dialog.btn_photo in photo_card.findChildren(QPushButton)
        assert dialog.btn_pattern_lock in lock.findChildren(QPushButton)
        assert dialog.btn_photo.width() >= photo_card.width() - 40
        assert dialog.btn_photo.height() == 138
        assert len(dialog.pattern_lock.points) == 9
        assert all(0 <= point.x() < dialog.pattern_lock.width() and 0 <= point.y() < dialog.pattern_lock.height() for point in dialog.pattern_lock.points)
        assert fault.layout().indexOf(dialog.txt_fault) == 4
        assert dialog.lbl_reference_fault_description.buddy() is dialog.txt_fault
        assert len(dialog.findChildren(QFrame, "serviceFaultCard")) == 1
        from src.ui.dialogs._new_service_dialog_widgets_mixin import ServiceSectionGlyph
        assert len(dialog.findChildren(ServiceSectionGlyph)) == 6
        changes = []
        dialog.txt_fault.textChanged.connect(lambda: changes.append(True))
        dialog.txt_fault.setPlainText("Fixture fault details")
        assert changes
        assert dialog.txt_fault.toPlainText() == "Fixture fault details"
        customers_before = [tuple(row) for row in db.conn.execute("SELECT * FROM customers")]
        dialog.inp_serial.setText("Changed serial")
        dialog.inp_est_price.setText("125.50")
        dialog.inp_delivered_by.setText("Fixture courier")
        dialog.inp_delivered_phone.setText("05550003344")
        dialog.pattern_lock.set_pattern_string("0-1-2")
        dialog.photo_paths = ["fixture-not-a-real-file.png"]
        dialog.photo_labels = ["Fixture photo"]
        toggle = next(iter(dialog.fault_toggles.values()), None)
        if toggle is not None:
            toggle.setChecked(True)
        assert dialog.btn_reset_form.isEnabled()
        dialog.btn_reset_form.click()
        assert dialog.txt_fault.toPlainText() == ""
        assert dialog.inp_serial.text() == ""
        assert dialog.inp_est_price.text() == ""
        assert dialog.inp_delivered_by.text() == ""
        assert dialog.inp_delivered_phone.text() == ""
        assert dialog.pattern_lock.get_pattern_string() == ""
        assert dialog.photo_paths == []
        assert not dialog.selected_fault_notes
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM customers")] == customers_before
        assert dialog.btn_add_customer.parentWidget() is customer
        for button in (dialog.btn_cancel, dialog.btn_save_and_form, dialog.btn_action):
            assert dialog.footer_layout.indexOf(button) >= 0
            assert button.receivers(button.clicked) > 0
        dialog.btn_cancel.click()
        assert db.conn.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0
    finally:
        dialog.close()
        db.close()


def test_new_service_saves_inline_customer_identity_and_contact(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "inline_customer_service.db"))
    dialog = TechnicalServiceNewServiceDialog(db)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    for _ in range(5):
        app.processEvents()
    try:
        dialog.cmb_customer.setEditText("Inline Test Customer")
        dialog.inp_customer_identity.setText("12345678901")
        dialog.inp_customer_phone.setText("05550001122")
        dialog.cmb_brand.setEditText("ASUS")
        dialog.txt_fault.setPlainText("Power issue")
        dialog.save()

        saved = db.cursor.execute(
            "SELECT id, phone, tc_no FROM customers WHERE name=?",
            ("Inline Test Customer",),
        ).fetchone()
        assert saved is not None
        assert saved[1:] == ("05550001122", "12345678901")
        device = db.cursor.execute(
            "SELECT customer_id FROM devices WHERE customer_name=?",
            ("Inline Test Customer",),
        ).fetchone()
        assert tuple(device) == (saved[0],)
    finally:
        dialog.close()
        dialog.deleteLater()
        db.close()


def test_edit_reset_restores_saved_operational_fields_without_database_writes(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "service_edit_reference.db"))
    db.conn.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", ("Saved Customer", "05550001122"))
    cursor = db.conn.execute(
        "INSERT INTO devices (tracking_no, customer_name, device_type, device_brand, device_model, "
        "serial_no, fault_description, device_password, price, delivery_method, service_location, other_info, delivered_by_name, delivered_by_phone) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("REF-EDIT-001", "Saved Customer", "Laptop", "ASUS", "Saved Model", "Saved Serial", "Saved fault", "2468", "125.50",
         "Kargo ile Geldi", "Saved location", "Saved handover notes", "Saved courier", "05550003344"))
    db.conn.commit()
    before = [tuple(row) for row in db.conn.execute("SELECT * FROM devices")]
    dialog = TechnicalServiceNewServiceDialog(db, device_data=(cursor.lastrowid, "REF-EDIT-001"))
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.show()
    for _ in range(5):
        app.processEvents()
    try:
        assert dialog.inp_password.text() == "2468"
        assert float(dialog.inp_est_price.text()) == 125.50
        assert dialog.cmb_delivery_method.currentText() == "Kargo ile Geldi"
        assert dialog.inp_service_location.text() == "Saved location"
        assert dialog.inp_other_info.text() == "Saved handover notes"
        assert dialog.inp_delivered_by.text() == "Saved courier"
        assert dialog.inp_delivered_phone.text() == "05550003344"
        dialog.inp_password.setText("Changed")
        dialog.inp_other_info.setText("Changed notes")
        dialog.inp_delivered_by.setText("Changed courier")
        dialog.txt_fault.setPlainText("Changed fault")
        dialog.cmb_service_profile.setCurrentIndex(1)
        dialog.btn_reset_form.click()
        assert dialog.inp_password.text() == "2468"
        assert dialog.inp_other_info.text() == "Saved handover notes"
        assert dialog.inp_delivered_by.text() == "Saved courier"
        assert dialog.txt_fault.toPlainText() == "Saved fault"
        assert dialog.cmb_service_profile.currentText() == "Bilgisayar"
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM devices")] == before
        from src.utils.toast_notification import ToastManager
        monkeypatch.setattr(ToastManager, "success", lambda *args, **kwargs: None)
        dialog.inp_delivered_by.setText("Updated courier")
        dialog.inp_delivered_phone.setText("05550005566")
        dialog.btn_action.click()
        row = db.conn.execute("SELECT delivered_by_name, delivered_by_phone, device_password, other_info FROM devices WHERE tracking_no=?",
                              ("REF-EDIT-001",)).fetchone()
        assert tuple(row) == ("Updated courier", "05550005566", "2468", "Saved handover notes")
        assert dialog.result() == dialog.DialogCode.Accepted
    finally:
        dialog.close()
        db.close()


def test_legacy_handover_columns_are_added_idempotently_without_replacing_records(tmp_path):
    db = Database(str(tmp_path / "legacy_handover.db"))
    try:
        db.conn.execute("INSERT INTO devices (tracking_no, customer_name, other_info) VALUES (?, ?, ?)",
                        ("LEGACY-001", "Legacy Customer", "Preserved notes"))
        db.conn.execute("ALTER TABLE devices DROP COLUMN delivered_by_name")
        db.conn.execute("ALTER TABLE devices DROP COLUMN delivered_by_phone")
        db.conn.commit()
        for _ in range(2):
            db._maint_run_migrations()
        row = db.conn.execute("SELECT customer_name, other_info, delivered_by_name, delivered_by_phone FROM devices WHERE tracking_no=?",
                              ("LEGACY-001",)).fetchone()
        assert tuple(row) == ("Legacy Customer", "Preserved notes", None, None)
    finally:
        db.close()


def test_pattern_dialog_shared_footer_commits_only_on_accept(tmp_path, monkeypatch):
    from src.ui.widgets.modern_dialog import ModernDialog
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    db = Database(str(tmp_path / "pattern_reference.db"))
    owner = TechnicalServiceNewServiceDialog(db)
    owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    for _ in range(5):
        app.processEvents()
    owner.pattern_lock.set_pattern_string("0-1")
    preview = owner._create_pattern_lock_dialog()
    preview.pattern_editor.set_pattern_string("0-2-4-6-8")
    preview.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    preview.show()
    app.processEvents()
    preview.grab().save(str(tmp_path / "pattern_lock_dialog.png"))
    preview.close()
    outcomes = iter((False, True))

    def controlled_exec(dialog):
        assert dialog.footer_layout.indexOf(dialog.btn_cancel) >= 0
        assert dialog.footer_layout.indexOf(dialog.btn_save) >= 0
        assert not dialog.footer.isHidden()
        assert dialog.pattern_editor.get_pattern_string() == "0-1"
        dialog.pattern_editor.set_pattern_string("0-2-4")
        (dialog.btn_save if next(outcomes) else dialog.btn_cancel).click()
        return dialog.result()

    monkeypatch.setattr(ModernDialog, "exec", controlled_exec)
    try:
        owner.open_pattern_lock_dialog()
        assert owner.pattern_lock.get_pattern_string() == "0-1"
        owner.open_pattern_lock_dialog()
        assert owner.pattern_lock.get_pattern_string() == "0-2-4"
        assert db.conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] == 0
    finally:
        owner.close()
        db.close()


def test_fault_dictation_reuses_worker_appends_draft_and_discards_late_results(tmp_path, monkeypatch):
    from PyQt6.QtCore import QObject, pyqtSignal
    from src.utils.toast_notification import ToastManager

    class ControlledVoiceWorker(QObject):
        text_received = pyqtSignal(str)
        error_occurred = pyqtSignal(str)
        finished = pyqtSignal()

        def __init__(self):
            super().__init__()
            self.start_count = 0

        def start(self):
            self.start_count += 1

    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "fault_dictation.db"))
    owner = TechnicalServiceNewServiceDialog(db)
    owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    owner.show()
    for _ in range(5):
        app.processEvents()
    workers = []
    warnings = []

    def create_worker():
        worker = ControlledVoiceWorker()
        workers.append(worker)
        return worker

    monkeypatch.setattr(owner, "_voice_input_available", lambda: True)
    monkeypatch.setattr(owner, "_create_fault_voice_worker", create_worker)
    monkeypatch.setattr(ToastManager, "warning", lambda _owner, message: warnings.append(message))
    try:
        placeholder = owner.txt_fault.placeholderText()
        owner.txt_fault.setPlainText("Existing manual note")
        owner.btn_fault_voice.click()
        assert len(workers) == 1 and workers[0].start_count == 1
        assert not owner.btn_fault_voice.isEnabled()
        owner._start_fault_dictation()
        assert len(workers) == 1
        workers[0].text_received.emit("Captured fault")
        assert owner.txt_fault.toPlainText() == "Existing manual note\nCaptured fault"
        workers[0].finished.emit()
        assert owner.btn_fault_voice.isEnabled()
        assert owner.txt_fault.placeholderText() == placeholder
        monkeypatch.setattr(owner, "_voice_input_available", lambda: False)
        owner.btn_fault_voice.click()
        assert len(workers) == 1
        assert owner.btn_fault_voice.isEnabled()
        assert "PyAudio" in warnings[-1]
        monkeypatch.setattr(owner, "_voice_input_available", lambda: True)
        owner.btn_fault_voice.click()
        owner.btn_reset_form.click()
        workers[1].text_received.emit("Discarded after reset")
        assert owner.txt_fault.toPlainText() == ""
        workers[1].finished.emit()
        owner.btn_fault_voice.click()
        workers[2].error_occurred.emit("Controlled microphone failure")
        assert "Controlled microphone failure" in warnings[-1]
        owner.reject()
        workers[2].text_received.emit("Discarded after cancel")
        assert owner.txt_fault.toPlainText() == ""
        workers[2].finished.emit()
        assert db.conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] == 0
    finally:
        owner.close()
        db.close()


def test_estimate_currency_uses_local_rates_preserves_roundtrip_and_saves_base_amount(tmp_path, monkeypatch):
    from decimal import Decimal
    from src.utils.toast_notification import ToastManager
    from src.utils.exchange_rate_manager import ExchangeRateManager
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "estimate_currency.db"))
    db.set_setting("currency", "TRY")
    db.conn.execute("INSERT INTO customers(name) VALUES ('Estimate Customer')")
    cursor = db.conn.execute(
        "INSERT INTO devices(tracking_no,customer_name,device_type,device_brand,device_model,fault_description,price) "
        "VALUES ('EST-001','Estimate Customer','Laptop','ASUS','Fixture Model','Fixture fault',125.5)")
    db.conn.commit()
    owner = TechnicalServiceNewServiceDialog(db, device_data=(cursor.lastrowid, "EST-001"))
    owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    owner.show()
    for _ in range(5):
        app.processEvents()
    warnings = []
    monkeypatch.setattr(ToastManager, "warning", lambda _owner, message: warnings.append(message))
    monkeypatch.setattr(ToastManager, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(ExchangeRateManager, "_rates_cache", {"USD": 999, "EUR": 999})
    try:
        original = owner.inp_est_price.text()
        owner.estimate_currency_buttons["USD"].click()
        assert warnings and owner._estimate_currency == "TRY"
        assert owner.estimate_currency_buttons["TRY"].isChecked()
        assert owner.inp_est_price.text() == original
        for code, rate in (("USD", 40), ("EUR", 50)):
            db.conn.execute("INSERT INTO exchange_rates(currency,buying_rate,selling_rate,effective_date,created_at) VALUES (?,?,?,?,?)",
                            (code, rate, rate, "2026-10-01", "2026-10-01 10:00:00"))
        db.conn.commit()
        owner.estimate_currency_buttons["USD"].click()
        assert owner.inp_est_price.text() == "3.14"
        assert owner._estimate_price_in_base() == Decimal("125.5")
        owner.estimate_currency_buttons["EUR"].click()
        assert owner.inp_est_price.text() == "2.51"
        owner.btn_reset_form.click()
        assert owner._estimate_currency == "TRY"
        assert owner.inp_est_price.text() == original
        owner.estimate_currency_buttons["USD"].click()
        for invalid in ("-1", "NaN", "1e999"):
            owner.inp_est_price.setText(invalid)
            owner.btn_action.click()
            assert db.conn.execute("SELECT price FROM devices WHERE tracking_no='EST-001'").fetchone()[0] == 125.5
            assert owner.result() != owner.DialogCode.Accepted
        owner.inp_est_price.setText("2.00")
        db.conn.execute("UPDATE exchange_rates SET selling_rate=80 WHERE currency='USD'")
        db.conn.commit()
        owner.btn_action.click()
        assert owner.result() == owner.DialogCode.Accepted
        assert db.conn.execute("SELECT price FROM devices WHERE tracking_no='EST-001'").fetchone()[0] == 80.0
    finally:
        owner.close()
        db.close()


def test_reference_photo_panel_keeps_upload_and_gallery_state(tmp_path, monkeypatch):
    from PyQt6.QtGui import QImage, QColor
    from PyQt6.QtWidgets import QFileDialog
    from src.utils.toast_notification import ToastManager

    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "service_photo_panel.db"))
    dialog = TechnicalServiceNewServiceDialog(db)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.show()
    for _ in range(12):
        app.processEvents()
    image_path = tmp_path / "native_fixture.png"
    image = QImage(8, 8, QImage.Format.Format_RGB32)
    image.fill(QColor("#3B82F6"))
    assert image.save(str(image_path))
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args, **kwargs: ([str(image_path)], ""))
    monkeypatch.setattr(ToastManager, "success", lambda *args, **kwargs: None)
    changes_before = db.conn.total_changes
    try:
        dialog.btn_photo.click()
        assert dialog.photo_paths == [str(image_path)]
        assert dialog.photo_path == str(image_path)
        assert "1 g\u00f6rsel" in dialog.btn_photo.text()
        assert not dialog.btn_photo_count.isHidden()
        assert "dashed" in dialog.btn_photo.styleSheet()
        add_photo_tile = dialog.reference_photo_preview_layout.itemAt(1).widget()
        assert isinstance(add_photo_tile, QPushButton)
        assert "Ekle" in add_photo_tile.text()
        add_photo_tile.click()
        assert dialog.photo_paths == [str(image_path)]
        assert db.conn.total_changes == changes_before
        dialog._remove_photo(0)
        assert dialog.photo_paths == []
        assert dialog.photo_path == ""
        assert dialog.btn_photo_count.isHidden()
        assert "Hen\u00fcz" in dialog.btn_photo.text()
        assert db.conn.total_changes == changes_before
    finally:
        dialog.close()
        db.close()


def test_reference_reset_does_not_trigger_accessory_live_write(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "accessory_reset.db"))
    db.conn.execute("INSERT INTO customers(name) VALUES ('Accessory Customer')")
    db.conn.execute("INSERT INTO fast_notes(category,label,is_active,display_order) VALUES ('Aksesuar','Fixture Cable',1,0)")
    cursor = db.conn.execute("INSERT INTO devices(tracking_no,customer_name,device_type,device_brand,device_model,fault_description) "
                             "VALUES ('ACC-RESET','Accessory Customer','Laptop','ASUS','Fixture Model','Fixture fault')")
    db.conn.commit()
    owner = TechnicalServiceNewServiceDialog(db, device_data=(cursor.lastrowid, "ACC-RESET"))
    owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    for _ in range(5):
        app.processEvents()
    try:
        toggle = owner.accessory_checkboxes["Fixture Cable"]
        toggle.setChecked(True)
        assert "Fixture Cable" in db.conn.execute("SELECT accessories FROM devices WHERE tracking_no='ACC-RESET'").fetchone()[0]
        changes = db.conn.total_changes
        owner.btn_reset_form.click()
        assert not toggle.isChecked()
        assert db.conn.total_changes == changes
        assert not owner._restoring_reference_form
    finally:
        owner.close()
        db.close()
