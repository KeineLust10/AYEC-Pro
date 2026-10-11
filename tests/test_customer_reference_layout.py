import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QDialog
from PyQt6.QtNetwork import QNetworkReply
from unittest.mock import patch

from src.database import Database
from src.ui.dialogs.add_customer_dialog import AddCustomerDialog, CustomerReferenceInput, CustomerReferenceGlyph
from src.services.tomtom_geocoder import TomTomGeocoder


class CustomerFields:
    def get_customer_fields(self):
        return [
            {"name": "device_type", "title": "Device Type", "type": "select", "options": ["Laptop", "Phone"]},
            {"name": "brand", "title": "Brand", "type": "text"},
            {"name": "model", "title": "Model", "type": "text"},
        ]


def test_customer_density_keeps_validators_footer_type_flags_and_sector_fields(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "customer_reference.db"))
    before = [tuple(row) for row in db.conn.execute("SELECT * FROM customers")]
    dialog = AddCustomerDialog(db, sector_manager=CustomerFields())
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.set_dialog_size(864, 820)
    dialog.show()
    app.processEvents()
    try:
        assert len(dialog.findChildren(QFrame, "customerReferenceCard")) == 6
        assert len(dialog.findChildren(CustomerReferenceGlyph)) == 7
        assert dialog.logo_label.isHidden()
        assert dialog.reference_header_badge.text() == "Cari Kart Tan\u0131m\u0131"
        assert dialog.btn_close.width() == 28
        type_bar = dialog.findChild(QFrame, "customerTypeBar")
        assert dialog.card_layout.indexOf(type_bar) == 1
        assert type_bar.height() == 48
        assert dialog.txt_note.height() == 72
        assert dialog.footer_layout.indexOf(dialog.btn_save) >= 0
        assert dialog.footer_layout.indexOf(dialog.btn_cancel) >= 0
        assert dialog.rb_individual.isChecked()
        assert dialog.inp_tc.isEnabled()
        assert not dialog.inp_tax_no.isEnabled()
        dialog.rb_corporate.setChecked(True)
        assert not dialog.inp_tc.isEnabled()
        assert dialog.inp_tax_no.isEnabled()
        assert dialog.inp_tax_office.isEnabled()
        assert dialog.inp_company.isEnabled()
        dialog.rb_individual.setChecked(True)
        assert dialog.inp_tc.isEnabled()
        assert isinstance(dialog.inp_phone, CustomerReferenceInput)
        dialog.inp_phone.setText("invalid phone")
        assert dialog.inp_phone.is_valid is False
        dialog.inp_phone.setText("05550001122")
        assert dialog.inp_phone.is_valid is True
        assert dialog.inp_phone.styleSheet().count(CustomerReferenceInput.DENSITY_MARKER) == 1
        assert 24 <= dialog.inp_phone.height() <= 34
        dialog.inp_email.setText("not-an-email")
        assert not dialog.inp_email.is_valid
        dialog.inp_email.setText("fixture@example.test")
        assert dialog.inp_email.is_valid
        dialog.chk_sms.setChecked(False)
        assert "kapal\u0131" in dialog.chk_sms.toolTip()
        dialog.chk_problem.setChecked(True)
        assert dialog.chk_problem.toolTip() == "Sorunlu kay\u0131t"
        assert set(dialog.plugin_customer_widgets) == {"device_type", "brand", "model"}
        dialog.plugin_customer_widgets["device_type"].setCurrentText("Phone")
        dialog.plugin_customer_widgets["brand"].setText("Fixture Brand")
        model = dialog.plugin_customer_widgets["model"]
        model.setText("Fixture Model")
        assert dialog._collect_plugin_customer_values() == {
            "device_type": "Phone", "brand": "Fixture Brand", "model": "Fixture Model",
        }
        grid = model.parentWidget().layout().itemAt(1).layout()
        assert grid.getItemPosition(grid.count() - 1) == (1, 0, 1, 2)
        dialog.btn_cancel.click()
        assert dialog.result() == QDialog.DialogCode.Rejected
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM customers")] == before
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        db.conn.close()


def test_customer_reference_toolbar_stays_pinned_and_close_keeps_reject_mapping(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "customer_pinned_toolbar.db"))
    dialog = AddCustomerDialog(db, sector_manager=CustomerFields())
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.set_dialog_size(600, 520)
    dialog.show()
    for _ in range(5):
        app.processEvents()
    rejected = []
    dialog.rejected.connect(lambda: rejected.append(True))
    try:
        toolbar = dialog.findChild(QFrame, "customerTypeBar")
        position = toolbar.mapTo(dialog, toolbar.rect().topLeft())
        bar = dialog.scroll_area.verticalScrollBar()
        assert bar.maximum() > 0
        bar.setValue(bar.maximum())
        app.processEvents()
        assert toolbar.mapTo(dialog, toolbar.rect().topLeft()) == position
        assert toolbar.isVisible()
        assert dialog.content_container is dialog.scroll_area.widget()
        assert dialog.content_layout is dialog.content_container.layout()
        assert dialog.btn_save.isVisible()
        dialog.btn_close.click()
        assert rejected == [True]
        assert dialog.result() == QDialog.DialogCode.Rejected
        assert db.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        db.conn.close()


def test_customer_location_coordinates_persist_and_reverse_address_fills_fields(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "customer_location.db"))
    dialog = AddCustomerDialog(db)
    try:
        app.processEvents()
        dialog.inp_name.setText("Location Test")
        assert dialog._set_location_coordinates(40.1044, 27.6564)
        dialog._apply_reverse_geocode(
            {
                "address": {
                    "countrySubdivision": "Balikesir",
                    "municipality": "Gonen",
                    "municipalitySubdivision": "Akcaali",
                    "street": "Ornek Sokak",
                    "streetNumber": "12",
                    "postalCode": "10900",
                    "freeformAddress": "Ornek Sokak 12, Gonen, Balikesir",
                }
            }
        )

        with patch("src.ui.dialogs.add_customer_dialog.show_success"), patch(
            "src.ui.dialogs.add_customer_dialog.show_error"
        ):
            dialog.save()

        row = db.conn.execute(
            "SELECT latitude, longitude, street, zip_code FROM customers WHERE id=?",
            (dialog.saved_customer_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == 40.1044
        assert row[1] == 27.6564
        assert row[2] == "Ornek Sokak 12"
        assert row[3] == "10900"
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_tomtom_geocoder_accepts_qt_no_error_enum_and_parses_reverse_address():
    app = QApplication.instance() or QApplication([])
    client = TomTomGeocoder("fixture-key")

    class Reply:
        def property(self, name):
            return "reverse:test"

        def error(self):
            return QNetworkReply.NetworkError.NoError

        def errorString(self):
            return "Unknown error"

        def readAll(self):
            return (
                b'{"addresses":[{"address":{"freeformAddress":"Gonen, Balikesir"}}]}'
            )

        def deleteLater(self):
            pass

    received = []
    client.resolved.connect(lambda *args: received.append(args))
    client._finish(Reply())

    assert len(received) == 1
    assert received[0][0] == "reverse:test"
    assert received[0][1]["address"]["freeformAddress"] == "Gonen, Balikesir"
    assert received[0][2] == ""
