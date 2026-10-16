import sys
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.license_requests import LicenseRequestsPage, _LicensesWorker
import api_client


@pytest.fixture(autouse=True)
def disable_external_invite_fetch(monkeypatch):
    monkeypatch.setattr(LicenseRequestsPage, "_load_provision_invites", lambda self: None)


def test_license_request_metrics_search_and_invite_navigation(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "license_orders", lambda status="", product_code="": [])
    monkeypatch.setattr(api_client, "provision_invites", lambda: {"invites": []})
    monkeypatch.setattr(LicenseRequestsPage, "reload", lambda self: None)
    monkeypatch.setattr(LicenseRequestsPage, "_load_licenses", lambda self: None)
    page = LicenseRequestsPage()
    assert page._page_title.text() == "Lisans & Yetki Da\u011f\u0131t\u0131m \u0130stasyonu"
    assert page._page_subtitle.text() == "Donan\u0131m kilitli istemci anahtarlar\u0131, uzaktan lisans sa\u011flama ve kriptografik davet t\u00fcnel"
    assert page._invite_button.text() == "+  Yeni Davet Kodu \u00dcret"
    assert page.findChild(QLabel, "licenseHsmBadge").text() == "HSM-VAULT v2.5"
    page.populate(
        [
            {"id": 1, "request_no": "REQ-001", "company_name": "ASLAN TIC", "requester_name": "Engin", "plan_label": "3 Yillik", "amount_try": 15990, "status": "payment_reported"},
            {"id": 2, "request_no": "REQ-002", "company_name": "Babali Servis", "requester_name": "Bora", "plan_label": "Lifetime", "amount_try": 4500, "status": "active"},
        ]
    )

    assert page.table.rowCount() == 2
    page._populate_invite_metrics({"invites": [
        {"expires_at": "2099-01-01T00:00:00+00:00", "use_count": 0, "max_uses": 1},
        {"expires_at": "2099-01-01T00:00:00+00:00", "use_count": 1, "max_uses": 1},
        {"expires_at": "2000-01-01T00:00:00+00:00", "use_count": 0, "max_uses": 1},
    ]})
    assert page._summary_labels["total"].text() == "3"
    assert page._summary_labels["paid"].text() == "1"
    assert page._summary_labels["active"].text() == "1"
    assert page._summary_labels["pending"].text() == "1"
    page.populate_inventory([{"company_name": "ASLAN TIC", "license_code": "AYEC-CORE-001", "status": "active"}])
    assert page.selected_order_id() == 1
    assert len(page._request_cards) == 2
    assert page._inventory_count.text() == "1 Kayit"
    page._request_cards[1].findChild(QPushButton, "requestPreviewBtn").click()
    assert page.selected_order_id() == 2

    page.search_field.setText("ASLAN")
    assert not page.table.isRowHidden(0)
    assert page.table.isRowHidden(1)

    destinations = []
    page.navigate_requested.connect(destinations.append)
    page.findChild(QPushButton, "primaryBtn").click()
    assert destinations == ["invite_codes"]
    page.close()
    page.deleteLater()
    persistent_qapplication.processEvents()


def test_request_card_actions_bind_approve_and_reject(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "license_orders", lambda status="", product_code="": [])
    monkeypatch.setattr(LicenseRequestsPage, "_load_licenses", lambda self: None)
    page = LicenseRequestsPage()
    page.populate([{"id": 7, "request_no": "REQ-007", "company_name": "ASLAN TIC", "status": "payment_reported"}])
    calls = []
    monkeypatch.setattr(page, "decide", lambda approved: calls.append((page.selected_order_id(), approved)))

    page._request_cards[0].findChild(QPushButton, "requestApproveBtn").click()
    page._request_cards[0].findChild(QPushButton, "requestRejectBtn").click()

    assert calls == [(7, True), (7, False)]
    page.close()
    page.deleteLater()
    persistent_qapplication.processEvents()


def test_license_telemetry_binds_by_tenant_id_without_cross_tenant_mix(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(
        api_client,
        "licenses",
        lambda product_code="": [
            {"tenant_id": "tenant-1", "company_name": "Shared Name", "product_code": "teknik_servis"}
        ],
    )
    monkeypatch.setattr(
        api_client,
        "live_status",
        lambda: [
            {"id": "tenant-1", "company_name": "Shared Name", "online": True, "active_users": 2},
            {"id": "tenant-2", "company_name": "Shared Name", "online": False, "active_users": 0},
        ],
    )
    received = []
    worker = _LicensesWorker("teknik_servis")
    worker.done.connect(received.append)
    worker.run()

    assert received[0][0]["online"] is True
    assert received[0][0]["active_users"] == 2


def test_license_inventory_binds_status_remaining_and_search(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(LicenseRequestsPage, "reload", lambda self: None)
    page = LicenseRequestsPage()
    page.populate_inventory(
        [
            {"company_name": "ASLAN TIC", "product_code": "teknik_servis", "license_code": "AYEC-001", "license_type": "Lifetime", "status": "Aktif", "online": True, "active_users": 2},
            {"company_name": "Babali Servis", "product_code": "otomotiv", "license_code": "AYEC-002", "license_type": "Pro", "license_end": "2020-01-01", "status": "Pasif"},
        ]
    )

    assert page.inventory_table.rowCount() == 2
    assert page.inventory_table.item(0, 4).text() == ""
    assert page.inventory_table.cellWidget(0, 4).findChild(QLabel).text() == "\u00d6m\u00fcr Boyu"
    assert page.inventory_table.item(1, 4).text() == ""
    assert page.inventory_table.cellWidget(1, 4).findChild(QLabel).text() == "S\u00fcresi Doldu"
    assert page._inventory_count.text() == "2 Kayit"
    detail_button = page.inventory_table.cellWidget(0, 6)
    assert isinstance(detail_button, QPushButton)
    detail_button.click()
    assert "AYEC-001" in page.status_label.text()
    telemetry = page.inventory_table.cellWidget(0, 5)
    assert telemetry.findChild(QLabel).text() == "ONLINE  (2)"
    page.inventory_table.cellWidget(0, 2).findChild(QPushButton).click()
    assert QApplication.clipboard().text() == "AYEC-001"
    page.inventory_search.setText("AYEC-002")
    assert page.inventory_table.isRowHidden(0)
    assert not page.inventory_table.isRowHidden(1)
    page.close()
    page.deleteLater()
    persistent_qapplication.processEvents()


def test_license_requests_fills_desktop_viewport_without_horizontal_overflow(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(LicenseRequestsPage, "reload", lambda self: None)
    monkeypatch.setattr(api_client, "license_orders", lambda status="", product_code="": [])
    monkeypatch.setattr(LicenseRequestsPage, "_load_licenses", lambda self: None)
    page = LicenseRequestsPage()
    page.resize(1176, 800)
    page.show()
    persistent_qapplication.processEvents()
    scroll = page.findChild(QScrollArea, "licenseScroll")
    assert scroll is not None
    assert scroll.widget().width() == scroll.viewport().width()
    assert page.inventory_table.width() <= scroll.viewport().width()
    assert all(card.height() <= 100 for card in page._metric_cards)
    page.resize(390, 800)
    persistent_qapplication.processEvents()
    assert scroll.widget().width() == scroll.viewport().width()
    assert scroll.horizontalScrollBar().maximum() == 0
    page.close()
    page.deleteLater()
    persistent_qapplication.processEvents()


def test_license_inventory_heading_tracks_selected_product(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(LicenseRequestsPage, "reload", lambda self: None)
    page = LicenseRequestsPage()
    page.set_product_filter("AYEC Pro Teknik Servis")

    assert page._inventory_title.text() == "AYEC Pro Teknik Servis \u2014 Lisans Envanteri"


def test_license_request_desktop_reference_hero_and_cards_use_full_width(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "license_orders", lambda status="", product_code="": [])
    monkeypatch.setattr(api_client, "provision_invites", lambda: {"invites": []})
    monkeypatch.setattr(LicenseRequestsPage, "reload", lambda self: None)
    monkeypatch.setattr(LicenseRequestsPage, "_load_licenses", lambda self: None)
    page = LicenseRequestsPage()
    page.resize(1160, 900)
    page.populate(
        [
            {"id": 1, "request_no": "REQ-001", "company_name": "ASLAN TIC", "amount_try": 15990, "status": "payment_reported"},
            {"id": 2, "request_no": "REQ-002", "company_name": "Babali Servis", "amount_try": 4500, "status": "active"},
        ]
    )
    page.show()
    persistent_qapplication.processEvents()
    assert page._product_context.width() == 294
    assert page._hero.minimumHeight() == 90
    assert page._request_cards[0].geometry().x() < page._request_cards[1].geometry().x()
    assert page._request_cards[0].width() > 500
    page.close()
