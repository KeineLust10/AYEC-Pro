import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.dialogs.setup_wizard.company_info_step import CompanyInfoStep


def test_desktop_setup_requires_company_address():
    app = QApplication.instance() or QApplication([])
    step = CompanyInfoStep()
    step.company_name.setText("Example Company")
    step.authorized_person.setText("Example Admin")
    step.phone.setText("05551234567")
    step.email.setText("admin@example.com")
    step.installation_lat = 39.6484
    step.installation_lng = 27.8826
    step.show()
    app.processEvents()

    assert step.validate() is False
    assert step.address.hasFocus()
    step.close()
    app.processEvents()


def test_desktop_setup_accepts_address_for_server_geocoding():
    app = QApplication.instance() or QApplication([])
    step = CompanyInfoStep()
    step.company_name.setText("Example Company")
    step.authorized_person.setText("Example Admin")
    step.phone.setText("05551234567")
    step.email.setText("admin@example.com")
    step.address.setPlainText("Main street 1, Balikesir")

    assert step.validate() is True
    assert step.get_data()["company_info"]["installation_lat"] is None
    step.close()
    app.processEvents()
