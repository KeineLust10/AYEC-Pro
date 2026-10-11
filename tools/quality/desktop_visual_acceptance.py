# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt, QPoint, QRect, QEvent, QSettings, QTemporaryDir
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QPushButton,
    QTableView,
    QTableWidget,
    QWidget,
)
from PyQt6.QtTest import QTest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def image_has_visual_content(widget: QWidget) -> tuple[bool, int]:
    image = widget.grab().toImage()
    if image.isNull():
        return False, 0
    colors: set[int] = set()
    x_step = max(1, image.width() // 32)
    y_step = max(1, image.height() // 18)
    for y_pos in range(0, image.height(), y_step):
        for x_pos in range(0, image.width(), x_step):
            colors.add(image.pixel(x_pos, y_pos))
            if len(colors) >= 8:
                return True, len(colors)
    return len(colors) >= 2, len(colors)


def visible_table_selection_issues(widget: QWidget) -> list[str]:
    issues: list[str] = []
    for table in widget.findChildren(QAbstractItemView):
        if (
            not table.isVisible()
            or isinstance(table, QHeaderView)
            or not isinstance(table, (QTableView, QTableWidget))
        ):
            continue
        if (
            table.selectionBehavior()
            != QAbstractItemView.SelectionBehavior.SelectRows
        ):
            name = table.objectName() or table.__class__.__name__
            issues.append(name)
    return issues


def clipped_button_warnings(widget: QWidget) -> list[str]:
    warnings: list[str] = []
    for button in widget.findChildren(QPushButton):
        if not button.isVisible() or not button.text().strip():
            continue
        required = button.fontMetrics().horizontalAdvance(button.text()) + 18
        if button.width() < required and button.width() >= 44:
            name = button.objectName() or button.text()
            warnings.append(name)
    return warnings


def service_list_geometry_issues(page: QWidget) -> list[str]:
    table = getattr(page, "table", None)
    if table is None or table.rowCount() == 0:
        return []
    issues = []
    actions = table.cellWidget(0, 9)
    buttons = actions.findChildren(QPushButton) if actions is not None else []
    if len(buttons) != 8:
        issues.append("Missing original service row actions")
    cell = table.visualRect(table.model().index(0, 9))
    for button in buttons:
        rect = QRect(button.mapTo(table.viewport(), QPoint(0, 0)), button.size())
        if not cell.contains(rect) or not table.viewport().rect().contains(rect):
            issues.append("Clipped service action: " + button.toolTip())
    for column in (1, 6):
        item = table.item(0, column)
        if item is not None and QFontMetrics(item.font()).horizontalAdvance(item.text()) > table.columnWidth(column) - 16:
            issues.append("Clipped service value column: " + str(column))
    return issues


def page_factories(db):
    from src.ui.pages.new_transaction_v2_page import NewTransactionV2Page
    from src.ui.pages.accounting_page import AccountingPage
    from src.ui.pages.audit_log_page import AuditLogPage
    from src.ui.pages.contracts_page import ContractsPage
    from src.ui.pages.customers_page import CustomersPage
    from src.ui.pages.product_groups_page import ProductGroupsPage
    from src.ui.pages.report_templates_page import ReportTemplatesPage
    from src.ui.pages.brands_page import BrandsPage
    from src.ui.pages.offer_pages import OffersPage
    from src.ui.pages.stock_page import StockPage
    from src.ui.pages.settings_widgets.cargo_settings import CargoSettingsWidget
    from src.ui.pages.settings_widgets.gemini_settings_widget import GeminiSettingsWidget
    from src.ui.pages.settings_widgets.telegram_settings import TelegramSettingsWidget
    from src.ui.pages.settings_widgets.whatsapp_settings import WhatsAppSettingsWidget
    from src.ui.pages.settings_widgets.backup_settings import BackupSettingsWidget
    from src.ui.pages.settings_widgets.bank_settings import BankSettingsWidget
    from src.ui.pages.settings_widgets.integration_hub import IntegrationHubWidget
    from src.ui.pages.settings_widgets.license_settings import LicenseManagementWidget
    from src.ui.pages.settings_widgets.user_management import UserManagementWidget
    from src.ui.pages.settings_widgets.voice_assistant_settings import VoiceAssistantSettingsWidget
    from src.ui.pages.settings_widgets.voice_assistant_shortcuts import VoiceAssistantShortcutsWidget, ShortcutEditDialog
    from src.ui.dialogs.technical_service_customer_dialog import TechnicalServiceCustomerDialog
    from src.ui.dialogs.new_service_dialog import NewServiceDialog
    from src.ui.pages.settings_widgets.autonomous_agents_widget import AutonomousAgentsWidget
    from src.ui.pages.settings_widgets.system_identity_settings import SystemIdentitySettingsWidget
    from src.ui.pages.settings_sidebar import PremiumSettingsSidebar
    from src.ui.widgets.side_menu import SideMenu
    from src.ui.dialogs.technician_wizard_page2 import TechnicianWizardPage2
    from src.ui.pages.appointments_page import AppointmentsPage
    from src.ui.pages.loaner_devices_page import LoanerDevicesPage
    from src.ui.pages.personnel_page import PersonnelPage
    from src.ui.pages.finance.bank_accounts_widget import BankAccountsWidget
    from src.ui.pages.finance.check_note_page import CheckNotePage
    from src.ui.pages.service_list_page import ServiceListPage
    from src.ui.pages.service_board_page import ServiceBoardPage
    from src.ui.pages.service_status_page import ServiceStatusPage
    from src.ui.pages.job_service_tracking_page import JobServiceTrackingPage
    from src.ui.pages.external_tracking_page import ExternalTrackingPage
    from src.ui.pages.dashboard_page import DashboardPage
    from src.ui.dialogs.technician_panel import TechnicalServiceTechnicianPanel
    from src.ui.pages.pc_builder_page import PCBuilderPage
    from src.ui.pages.backup_page import BackupPage
    from src.ui.pages.stock_locations_page import StockLocationsPage
    from src.ui.pages import field_service_page as field_service_module

    def integration_reference_factory():
        from src.ui.pages.settings_widgets.gemini_reference_canvas import GeminiReferenceCanvas
        hub = IntegrationHubWidget(db)
        canvas = hub.findChild(GeminiReferenceCanvas)
        if canvas is not None:
            canvas.page.inp_api_key.setPlainText("fixture-api-key-01\nfixture-api-key-02\nfixture-api-key-03")
        return hub

    def field_service_factory():
        field_service_module.QWebEngineView = None
        return field_service_module.FieldServicePage(db)

    def settings_sidebar_factory():
        sidebar = PremiumSettingsSidebar(
            lambda *_args: None,
            db=db,
            current_user={"full_name": "Aslan Computer", "role": "Admin"},
        )
        sidebar.list_widget.setCurrentRow(1)
        return sidebar

    def transaction_reference_factory(populated=False, *, catalog_mode=0, currency='TRY'):
        directory = QTemporaryDir()
        settings = QSettings(directory.filePath('draft.ini'), QSettings.Format.IniFormat)
        page = NewTransactionV2Page(db, draft_settings=settings)
        page.catalog_tabs.setCurrentIndex(catalog_mode)
        page._visual_draft_directory = directory
        page.update_exchange_rates = lambda: page.on_currency_changed(
            page.cmb_currency.currentText()
        )
        if populated:
            page._restore_draft = lambda: None
            deferred_services = page._deferred_load_services

            def load_selected_customer():
                deferred_services()
                if page.cmb_customer.count():
                    page.cmb_customer.setCurrentIndex(0)
                    page._refresh_customer_preview()
                if currency != 'TRY':
                    for index in range(page.cmb_currency.count()):
                        if page._parse_currency_code(page.cmb_currency.itemText(index)) == currency:
                            page.cmb_currency.setCurrentIndex(index)
                            break
                    page.on_currency_changed(page.cmb_currency.currentText())
                    if page.cmb_parts.count():
                        page.cmb_parts.setCurrentIndex(0)
                    page.inp_discount.setValue(440)
                    page.update_totals()

            page._deferred_load_services = load_selected_customer
            rows = db.cursor.execute(
                'SELECT id, name, price FROM parts ORDER BY id LIMIT 4'
            ).fetchall()
            page.cart_items = [
                {
                    'id': f'visual-part-{row[0]}', 'item_id': row[0],
                    'type': 'part', 'service': row[1], 'description': '',
                    'price': float(row[2] or 0), 'qty': 1, 'date': '2026-09-30',
                }
                for row in rows
            ]
            page.refresh_cart_ui()
            page.update_totals()
        return page

    def product_group_cards_factory():
        page = ProductGroupsPage(db)
        page.view_tabs.setCurrentIndex(1)
        return page

    return {
        "transaction_basket": transaction_reference_factory,
        "transaction_basket_populated": lambda: transaction_reference_factory(True),
        "transaction_basket_service": lambda: transaction_reference_factory(catalog_mode=1),
        "transaction_basket_usd": lambda: transaction_reference_factory(True, currency='USD'),
        "accounting": lambda: AccountingPage(db, None),
        "customers": lambda: CustomersPage(db),
        "stock": lambda: StockPage(db),
        "offers": lambda: OffersPage(db),
        "product_groups": lambda: ProductGroupsPage(db),
        "product_groups_cards": product_group_cards_factory,
        "report_templates": lambda: ReportTemplatesPage(db),
        "brands": lambda: BrandsPage(db),
        "contracts": lambda: ContractsPage(db, None),
        "audit_log": lambda: AuditLogPage(db),
        "cargo_settings": lambda: CargoSettingsWidget(db),
        "gemini_settings": lambda: GeminiSettingsWidget(db),
        "autonomous_agents": lambda: AutonomousAgentsWidget(db),
        "telegram_settings": lambda: TelegramSettingsWidget(db),
        "whatsapp_settings": lambda: WhatsAppSettingsWidget(db),
        "backup_settings": lambda: BackupSettingsWidget(db),
        "bank_settings": lambda: BankSettingsWidget(db),
        "bank_accounts": lambda: BankAccountsWidget(db),
        "check_notes": lambda: CheckNotePage(db, None),
        "integration_hub": integration_reference_factory,
        "license_settings": lambda: LicenseManagementWidget(db, None),
        "user_management": lambda: UserManagementWidget(db),
        "voice_assistant_settings": lambda: VoiceAssistantSettingsWidget(db),
        "voice_assistant_shortcuts": lambda: VoiceAssistantShortcutsWidget(db),
        "voice_shortcut_editor": lambda: ShortcutEditDialog("Financial Summary", "Asistan finans \u00f6zet, kasa durumu", "Fonksiyon", "accounting_summary"),
        "new_customer": lambda: TechnicalServiceCustomerDialog(db),
        "edit_customer": lambda: TechnicalServiceCustomerDialog(db, customer_data=db.get_customers()[0]),
        "new_service": lambda: NewServiceDialog(db),
        "edit_service": lambda: NewServiceDialog(db, device_data=db.conn.execute("SELECT id, tracking_no FROM devices ORDER BY id LIMIT 1").fetchone()),
        "pattern_editor": lambda: NewServiceDialog(db)._create_pattern_lock_dialog(),
        "technician_notes": lambda: TechnicianWizardPage2(db, "DEMO-SRV-0008", {}, None),
        "appointments": lambda: AppointmentsPage(db),
        "loaner_devices": lambda: LoanerDevicesPage(db),
        "personnel": lambda: PersonnelPage(db),
        "service_list": lambda: ServiceListPage(db),
        "service_board": lambda: ServiceBoardPage(db, None),
        "service_status": lambda: ServiceStatusPage(db),
        "job_service_tracking": lambda: JobServiceTrackingPage(db),
        "external_tracking": lambda: ExternalTrackingPage(db),
        "dashboard": lambda: DashboardPage(db, None),
        "technician_panel": lambda: TechnicalServiceTechnicianPanel(db, "DEMO-SRV-0008"),
        "pc_builder": lambda: PCBuilderPage(db),
        "backup_page": lambda: BackupPage(db),
        "stock_locations": lambda: StockLocationsPage(db),
        "field_service": field_service_factory,
        "side_menu": lambda: SideMenu(
            db=db,
            current_user={"full_name": "Aslan Computer", "role": "Admin"},
        ),
        "settings_sidebar": settings_sidebar_factory,
        "system_identity": lambda: SystemIdentitySettingsWidget(db, None),
    }


def seed_visual_fixture(db, *, currency_rates=False):
    """Populate only the in-memory acceptance database with reference-like rows."""
    if currency_rates:
        for code, buying, selling in (('USD', 43.98, 44.0), ('EUR', 55.71, 55.731)):
            db.cursor.execute(
                'INSERT INTO exchange_rates '
                '(currency,buying_rate,selling_rate,effective_date,source,created_at) '
                'SELECT ?,?,?,?, ?,? WHERE NOT EXISTS '
                '(SELECT 1 FROM exchange_rates WHERE currency=?)',
                (code, buying, selling, datetime.now().strftime('%Y-%m-%d'),
                 'visual-fixture', datetime.now().isoformat(), code),
            )
        db.conn.commit()
    customer_rows = [
        ("Ahmet Yilmaz", "0555 000 0001", "ahmet@example.com", "Bireysel", ""),
        ("Aksoy Medya A.S.", "0212 444 0123", "info@aksoymedya.com", "Kurumsal", "Aksoy Medya A.S."),
        ("Baris Cevik", "0555 000 0025", "baris@cevik.net", "Kurumsal", "Bilisim Yazilim Ltd."),
        ("Cemre Ekin", "0555 000 0024", "cemre@ekin.org", "Bireysel", ""),
        ("Tolga Acar", "0555 000 0008", "tolga@acarmimarlik.com", "Kurumsal", "Acar Mimarlik Ltd."),
        ("Ayse Demir", "0555 000 0002", "ayse.demir@example.com", "Bireysel", ""),
    ]
    customer_rows.extend(
        [("Demo Musteri {:02d}".format(i), "0555 100 {:04d}".format(i), "demo{:02d}@example.com".format(i), "Kurumsal" if i % 3 == 0 else "Bireysel", "Demo Firma {:02d}".format(i) if i % 3 == 0 else "") for i in range(1, 20)]
    )
    try:
        count = db.cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO customers (name, phone, email, type, company_name) VALUES (?, ?, ?, ?, ?)",
                customer_rows,
            )
            db.conn.commit()
    except Exception:
        pass
    try:
        balance_count = db.cursor.execute("SELECT COUNT(*) FROM customer_currency_balances").fetchone()[0]
        if not balance_count:
            balance_rows = [
                (1, "TRY", 8100.0),
                (3, "TRY", -14250.0),
                (4, "TRY", 2400.0),
                (5, "TRY", 1700.0),
            ]
            db.cursor.executemany(
                "INSERT OR REPLACE INTO customer_currency_balances (customer_id, currency, balance, last_updated) VALUES (?, ?, ?, ?)",
                [(customer_id, currency, balance, "2026-09-29") for customer_id, currency, balance in balance_rows],
            )
            db.conn.commit()
    except Exception:
        pass
    appointment_rows = [
        ("Tolga Acar", "0555 000 0008", "2026-09-28", "10:00", "Bakim - Akilli Ev Kontrolu", "Planlandi", "Tolga Acar", "Saha Servis", "Normal", "#27cda0"),
        ("Ahmet Yilmaz", "0555 000 0001", "2026-09-29", "10:00", "Cihaz Teslim Alma ve Diagnostik", "Planlandi", "Eren Uysal", "Saha Servis", "Normal", "#5d8fe8"),
        ("Tolga Acar", "0555 000 0008", "2026-10-04", "10:00", "Bakim Randevusu - Akilli Ev Kontrol", "Planlandi", "Eren Uysal", "Saha Servis", "Normal", "#27cda0"),
        ("Ahmet Yilmaz", "0555 000 0001", "2026-10-04", "15:30", "Cihaz Teslim Alma ve Diagnostik", "Planlandi", "Eren Uysal", "Saha Servis", "Normal", "#5d8fe8"),
        ("Baris Cevik", "0555 000 0025", "2026-10-01", "11:30", "UPS ve Guc Testi", "Planlandi", "Murat Demir", "Atolye Servis", "Normal", "#7f879b"),
        ("Cemre Ekin", "0555 000 0024", "2026-09-30", "14:00", "Suncucu Odasi Acil Servis", "Planlandi", "Selim Celik", "Saha Servis", "Acil", "#f34f74"),
        ("Ahmet Yilmaz", "0555 000 0001", "2026-09-30", "15:30", "Cihaz Teslim Alma ve Diagnostik", "Planlandi", "Eren Uysal", "Saha Servis", "Normal", "#5d8fe8"),
        ("Ayse Demir", "0555 000 0002", "2026-09-29", "15:30", "Diagnostik Kontrol", "Planlandi", "Eren Uysal", "Saha Servis", "Normal", "#69758d"),
    ]
    try:
        appointment_count = db.cursor.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
        if not appointment_count:
            db.cursor.executemany(
                "INSERT INTO appointments (customer_name, phone, date, time, description, status, personnel_name, type, urgency, color, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [row + ("2026-09-28 08:00:00",) for row in appointment_rows],
            )
            db.conn.commit()
    except Exception:
        pass
    audit_rows = [
        (1, "currency_transactions", "UPDATE", "Cari borc duzenleme ve tahsilat islemi", "2026-09-29 14:42:19"),
        (2, "srv_repair_job", "UPDATE", "Servis durumu degistirildi", "2026-09-29 14:41:03"),
        (3, "e_invoice", "BLOCK", "Yetkisiz e-fatura kesme denemesi", "2026-09-29 14:38:52"),
        (4, "auth_service", "RESET", "Kullanici sifre sifirlama istegi", "2026-09-29 14:32:10"),
        (5, "backup_cron", "SNAPSHOT", "Yedekleme snapshot baslatildi", "2026-09-29 14:15:00"),
    ]
    try:
        audit_count = db.cursor.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
        if not audit_count:
            db.cursor.executemany(
                "INSERT INTO audit_logs (user_id, table_name, action, details, created_at) VALUES (?, ?, ?, ?, ?)",
                audit_rows,
            )
            db.conn.commit()
    except Exception:
        pass
    check_rows = [
        ("\u00c7ek", "Giri\u015f (Al\u0131nan)", "PF-0001", 1450.0, "2026-10-21", "Ahmet Yilmaz", "AYEC Pro", "Garanti BBVA", "Kadikoy", "102", "CK-8849201", "Demo portfoy cek", "Portf\u00f6yde", ""),
        ("Senet", "Giri\u015f (Al\u0131nan)", "PF-0002", 850.0, "2026-11-05", "Ayse Demir", "AYEC Pro", "Is Bankasi", "Umraniye", "412", "SNT-2026-09", "Demo senet", "Portf\u00f6yde", ""),
        ("\u00c7ek", "Giri\u015f (Al\u0131nan)", "PF-0003", 3200.0, "2026-11-20", "Mehmet Kaya", "AYEC Pro", "Akbank", "Besiktas", "778", "CK-9912048", "Takas bankasi", "Ciro Edildi", ""),
        ("Senet", "Giri\u015f (Al\u0131nan)", "PF-0004", 620.0, "2026-12-05", "Zeynep Celik", "AYEC Pro", "Yapi Kredi", "Mecidiyekoy", "778", "SNT-2026-14", "Demo senet", "Portf\u00f6yde", ""),
    ]
    try:
        check_count = db.cursor.execute("SELECT COUNT(*) FROM checks_notes").fetchone()[0]
        if not check_count:
            db.cursor.executemany(
                "INSERT INTO checks_notes (type, direction, portfolio_no, amount, due_date, issuer, recipient, bank_name, branch_name, account_no, check_no, description, status, image_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                check_rows,
            )
            db.conn.commit()
    except Exception:
        pass
    user_rows = [
        ("selim.celik", "selim@example.com", "Admin", 1, 1, "2026-01-04"),
        ("eren.uysal", "eren@example.com", "Teknisyen", 2, 1, "2026-01-05"),
        ("admin", "admin@example.com", "Master", 6, 1, "2026-01-01"),
        ("pelin.aksoy", "pelin@example.com", "Muhasebe", 4, 0, "2026-01-08"),
        ("burak.sahin", "burak@example.com", "Teknisyen", 3, 1, "2026-01-09"),
        ("murat.keskin", "murat@example.com", "Depo", 5, 1, "2026-01-10"),
    ]
    user_rows.extend(
        [("demo.user{:02d}".format(i), "demo{:02d}@example.com".format(i), ["Teknisyen", "Muhasebe", "Depo"][i % 3], 2, 1, "2026-01-{:02d}".format(11 + i)) for i in range(1, 9)]
    )
    try:
        user_count = db.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if not user_count:
            db.cursor.executemany(
                "INSERT INTO users (username, email, role, personnel_id, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                user_rows,
            )
            db.conn.commit()
    except Exception:
        pass
    part_rows = [
        ("SSD 1TB NVMe", "Depolama", 12, 2450.0, 1800.0, "TRY"),
        ("DDR5 16GB RAM", "Bellek", 24, 1850.0, 1350.0, "TRY"),
        ("USB-C Adaptoru", "Aksesuar", 31, 450.0, 300.0, "TRY"),
        ("Laptop Ekran 15.6", "Ekran", 7, 3200.0, 2400.0, "TRY"),
        ("Guc Adaptoru 65W", "Guc", 18, 980.0, 700.0, "TRY"),
        ("Klavye Mekanik", "Aksesuar", 9, 1250.0, 900.0, "TRY"),
    ]
    part_categories = ["Akilli Ev Sistemleri", "Bilgisayar Bilesenleri", "Guvenlik Sistemleri", "Ag ve Sunucu Ekipmanlari"]
    part_rows.extend(
        [("Demo Urun {:02d}".format(i), part_categories[i % len(part_categories)], 8 + (i % 48), 850.0 + (i * 175.0), (850.0 + (i * 175.0)) * 0.72, "TRY") for i in range(84)]
    )
    try:
        count = db.cursor.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO parts (name, category, stock, price, purchase_price, currency) VALUES (?, ?, ?, ?, ?, ?)",
                part_rows,
            )
            db.conn.commit()
    except Exception:
        pass
    device_rows = [
        ("DEMO-SRV-0015", "Burak Sahin", "AYEC", "Test Cihaz 15", "Teslim Edildi", "2026-09-21", 2400.0, "Normal"),
        ("DEMO-SRV-0014", "Derya Aydin", "AYEC", "Test Cihaz 14", "Teslime Hazir", "2026-09-21", 2300.0, "Normal"),
        ("DEMO-SRV-0013", "Murat Arslan", "AYEC", "Test Cihaz 13", "Test / Onay", "2026-09-21", 2200.0, "Normal"),
        ("DEMO-SRV-0012", "Elif Yilmaz", "AYEC", "Test Cihaz 12", "Tamirde", "2026-09-21", 2100.0, "Normal"),
        ("DEMO-SRV-0011", "Can Yilmaz", "AYEC", "Test Cihaz 11", "Bekliyor", "2026-09-21", 2000.0, "Normal"),
        ("DEMO-SRV-0010", "Kaan Yilmaz", "AYEC", "Test Cihaz 10", "Teslim Edildi", "2026-09-21", 1900.0, "Normal"),
        ("DEMO-SRV-0009", "Selin Yilmaz", "AYEC", "Test Cihaz 09", "Teslim Edildi", "2026-09-21", 1800.0, "Normal"),
        ("DEMO-SRV-0008", "Tolga Acar", "AYEC", "Test Cihaz 08", "Parca Bekliyor", "2026-09-21", 1700.0, "Acil"),
        ("DEMO-SRV-0007", "Mehmet Kaya", "AYEC", "Test Cihaz 07", "Teslim Edildi", "2026-09-20", 1600.0, "Normal"),
        ("DEMO-SRV-0006", "Zeynep Celik", "AYEC", "Test Cihaz 06", "Test / Onay", "2026-09-20", 1500.0, "Normal"),
        ("DEMO-SRV-0005", "Burak Sahin", "AYEC", "Test Cihaz 05", "Tamirde", "2026-09-20", 1400.0, "Normal"),
        ("DEMO-SRV-0004", "Ahmet Yilmaz", "AYEC", "Test Cihaz 04", "Bekliyor", "2026-09-20", 1300.0, "Normal"),
        ("DEMO-SRV-0003", "Murat Demir", "AYEC", "Test Cihaz 03", "Teslim Edildi", "2026-09-20", 1200.0, "Normal"),
        ("DEMO-SRV-0002", "Derya Aydin", "AYEC", "Test Cihaz 02", "Teslim Edildi", "2026-09-20", 1100.0, "Normal"),
        ("DEMO-SRV-0001", "Selin Yilmaz", "AYEC", "Test Cihaz 01", "Teslim Edildi", "2026-09-20", 1000.0, "Normal"),
    ]
    try:
        count = db.cursor.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO devices (tracking_no, customer_name, device_brand, device_model, status, entry_date, price, priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                list(reversed(device_rows)),
            )
            db.cursor.execute(
                "UPDATE devices SET delivery_type='Kargo' WHERE tracking_no='DEMO-SRV-0003'"
            )
            db.conn.commit()
    except Exception:
        pass
    loaner_rows = [
        ("Laptop", "Lenovo ThinkPad T14 Gen 3", "FPS9821", "R-14/B", "M\u00fcs\u00fcteride", 500.0),
        ("Switch", "Ubiquiti USW-24-PoE Switch", "UNT8842", "R-14/C", "Depoda", 5000.0),
        ("NVR", "Dahua 16 Kanal 4K NVR", "DH02644", "G-08/D", "Depoda", 7500.0),
        ("Yazici", "Zebra ZT411 Endustriyel Yazici", "ZB99410", "G-09/A", "M\u00fcs\u00fcteride", 400.0),
        ("Sunucu", "Dell PowerEdge T150 Kule Sunucu", "DELL-SVR-901", "B-05/C", "Depoda", 65000.0),
        ("Laptop", "HP ProBook 450 G8", "HP450G8", "R-11/A", "Depoda", 18000.0),
        ("Router", "MikroTik RB5009 Router", "MT5009", "R-11/B", "Depoda", 9500.0),
        ("Laptop", "Dell Latitude 5520", "DL5520-01", "R-12/A", "M\u00fcs\u00fcteride", 2383.2),
        ("Switch", "Cisco CBS350-24T", "CBS350-02", "R-12/B", "M\u00fcs\u00fcteride", 2383.2),
        ("Kamera", "Hikvision NVR 16CH", "HK16-03", "R-12/C", "M\u00fcs\u00fcteride", 2383.2),
        ("Router", "Fortinet Firewall 60F", "FT60F-04", "R-13/A", "M\u00fcs\u00fcteride", 2383.2),
        ("Laptop", "Lenovo ThinkPad E15", "E15-05", "R-13/B", "M\u00fcs\u00fcteride", 2383.2),
        ("Tablet", "Samsung Galaxy Tab A8", "TAB-A8-06", "G-10/A", "Depoda", 12000.0),
        ("Telefon", "Apple iPhone 14", "IPH14-07", "G-10/B", "Depoda", 32000.0),
        ("Router", "TP-Link Omada ER605", "ER605-08", "G-10/C", "Depoda", 6500.0),
        ("Switch", "Aruba Instant On 1930", "AR1930-09", "G-11/A", "Depoda", 22000.0),
        ("Laptop", "HP EliteBook 840", "HP840-10", "G-11/B", "Depoda", 38000.0),
        ("Kamera", "Dahua IP Kamera Seti", "DHSET-11", "G-11/C", "Depoda", 18500.0),
        ("Yazici", "Canon i-SENSYS LBP", "CNLBP-12", "G-12/A", "Depoda", 14500.0),
        ("NVR", "Hikvision 8 Kanal NVR", "HK8-13", "G-12/B", "Depoda", 11000.0),
        ("Laptop", "Asus ExpertBook B1", "ASB1-14", "G-12/C", "Depoda", 29000.0),
        ("Router", "Ubiquiti EdgeRouter", "UER-15", "G-13/A", "Depoda", 16000.0),
        ("Switch", "Netgear GS724", "NGS-16", "G-13/B", "Depoda", 12500.0),
        ("Tablet", "Lenovo Tab M10", "LTM10-17", "G-13/C", "Depoda", 9500.0),
        ("Telefon", "Samsung Galaxy A54", "SGA54-18", "G-14/A", "Depoda", 17500.0),
        ("Laptop", "Acer TravelMate P2", "ATP2-19", "G-14/B", "Depoda", 24000.0),
        ("Kamera", "Reolink Kamera Kit", "RLK-20", "G-14/C", "Depoda", 13500.0),
        ("Router", "MikroTik hEX S", "HEX-21", "G-15/A", "Depoda", 7000.0),
    ]
    try:
        loaner_count = db.cursor.execute("SELECT COUNT(*) FROM loaner_devices").fetchone()[0]
        if not loaner_count:
            db.cursor.executemany(
                "INSERT INTO loaner_devices (device_type, brand_model, serial_mac, shelf_no, status, daily_penalty_fee) VALUES (?, ?, ?, ?, ?, ?)",
                loaner_rows,
            )
            db.cursor.execute("SELECT id FROM loaner_devices WHERE status='M\u00fcs\u00fcteride' ORDER BY id")
            loaner_ids = [int(row[0]) for row in db.cursor.fetchall()]
            db.cursor.executemany(
                "INSERT INTO loaner_transactions (device_id, customer_name, customer_phone, tracking_no, condition_out, expected_return, status, date_given) VALUES (?, ?, ?, ?, ?, ?, 'Aktif', ?)",
                [(loaner_ids[0], "Tolga Acar", "0555 000 0008", "EMN-2026-042", "Iyi", "2026-09-28 10:00:00", "2026-09-18 10:00:00"),
                 (loaner_ids[1], "Kemal Eren", "0555 000 0019", "EMN-2026-035", "Iyi", "2026-09-27 10:00:00", "2026-09-20 10:00:00"),
                 (loaner_ids[2], "Murat Aksoy", "0555 000 0020", "EMN-2026-031", "Iyi", "2026-10-05 10:00:00", "2026-09-24 10:00:00"),
                 (loaner_ids[3], "Baris Cevik", "0555 000 0021", "EMN-2026-028", "Iyi", "2026-10-07 10:00:00", "2026-09-25 10:00:00"),
                 (loaner_ids[4], "Sinan Demir", "0555 000 0022", "EMN-2026-025", "Iyi", "2026-10-10 10:00:00", "2026-09-26 10:00:00"),
                 (loaner_ids[5], "Zeynep Celik", "0555 000 0023", "EMN-2026-021", "Iyi", "2026-10-12 10:00:00", "2026-09-27 10:00:00"),
                 (loaner_ids[6], "Mehmet Kaya", "0555 000 0024", "EMN-2026-019", "Iyi", "2026-10-14 10:00:00", "2026-09-28 10:00:00")],
            )
            db.conn.commit()
    except Exception:
        pass
    accounting_rows = [
        ("Gelir", "Tahsilat", 8977.74, 8977.74, "USD", 1.0, 8977.74, "Servis tahsilati", "2026-09-28", "Ahmet Yilmaz"),
        ("Gider", "Operasyon", 12.52, 12.52, "USD", 1.0, 12.52, "Parca ve iscilik gideri", "2026-09-28", ""),
        ("Gelir", "Tahsilat", 183.67, 183.67, "USD", 1.0, 183.67, "Cari hesap tahsilati", "2026-09-27", "Aksoy Medya A.S."),
    ]
    try:
        db.cursor.execute(
            "CREATE TABLE IF NOT EXISTS accounting ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, category TEXT, amount REAL, "
            "try_equivalent REAL, currency TEXT, exchange_rate REAL, original_amount REAL, "
            "description TEXT, date TEXT, customer_name TEXT, is_deleted INTEGER DEFAULT 0)"
        )
        accounting_cols = [row[1] for row in db.cursor.execute("PRAGMA table_info(accounting)").fetchall()]
        if "bank_account_id" not in accounting_cols:
            db.cursor.execute("ALTER TABLE accounting ADD COLUMN bank_account_id INTEGER")
        db.cursor.execute(
            "CREATE TABLE IF NOT EXISTS currency_transactions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, transaction_type TEXT, "
            "amount REAL, currency TEXT, exchange_rate REAL, try_equivalent REAL, "
            "description TEXT, tracking_no TEXT, created_at TEXT, current_balance REAL DEFAULT 0, "
            "is_invoiced INTEGER DEFAULT 0)"
        )
        count = db.cursor.execute("SELECT COUNT(*) FROM accounting").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO accounting (type, category, amount, try_equivalent, currency, exchange_rate, original_amount, description, date, customer_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                accounting_rows,
            )
            db.conn.commit()
        job_rows = [
            (1, "DEMO-SRV-0001", "Accepted Offer Service", 1800.0, "TRY", "2026-09-21", 0.0),
            (2, "DEMO-SRV-0002", "Thermal pad replacement", 2009.0, "TRY", "2026-09-21", 0.0),
            (3, "DEMO-SRV-0008", "AYEC Test Device 08 - SMD repair", 1700.0, "USD", "2026-09-21", 1700.0),
            (4, "DEMO-SRV-0003", "Industrial UPS battery service", 2207.0, "TRY", "2026-09-21", 0.0),
            (5, "DEMO-SRV-0015", "Power board revision", 4583.0, "TRY", "2026-09-21", 0.0),
            (6, "DEMO-SRV-0004", "Screen repair and diagnostics", 2175.0, "TRY", "2026-09-21", 2175.0),
        ]
        job_count = db.cursor.execute("SELECT COUNT(*) FROM currency_transactions WHERE tracking_no IS NOT NULL").fetchone()[0]
        if not job_count:
            db.cursor.executemany(
                "INSERT INTO currency_transactions (customer_id, transaction_type, amount, currency, exchange_rate, try_equivalent, description, tracking_no, created_at, current_balance) VALUES (?, 'DEBIT', ?, ?, 1.0, ?, ?, ?, ?, ?)",
                [(customer_id, amount, currency, amount, description, tracking_no, date, balance) for customer_id, tracking_no, description, amount, currency, date, balance in job_rows],
            )
            db.conn.commit()
    except Exception:
        pass
    try:
        bank_history = [
            ("Gelir", "Tahsilat", 15000.0, 15000.0, "TRY", 1.0, 15000.0, "Cari tahsilat", "2026-09-29 14:15:00", "Aksoy Medya A.S.", 1),
            ("Gider", "Tedarikci", 32400.0, 32400.0, "TRY", 1.0, 32400.0, "Parca ve donanim alimi", "2026-09-29 12:40:00", "Ozlem Yedek Parca", 2),
            ("Gelir", "Nakit Tahsilat", 1700.0, 1700.0, "TRY", 1.0, 1700.0, "Elden cihaz onarim", "2026-09-29 11:20:00", "Tolga Acar", 4),
            ("Gider", "Kasa Harcamasi", 1850.0, 1850.0, "TRY", 1.0, 1850.0, "Saha yakit ve iase", "2026-09-29 09:38:00", "Santiye", 4),
            ("Gelir", "POS Tahsilat", 58120.0, 58120.0, "TRY", 1.0, 58120.0, "Sanal POS gun sonu", "2026-09-29 08:00:00", "Garanti Pay", 5),
        ]
        history_count = db.cursor.execute("SELECT COUNT(*) FROM accounting WHERE bank_account_id IS NOT NULL").fetchone()[0]
        if not history_count:
            db.cursor.executemany(
                "INSERT INTO accounting (type, category, amount, try_equivalent, currency, exchange_rate, original_amount, description, date, customer_name, bank_account_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                bank_history,
            )
            db.conn.commit()
    except Exception:
        pass
    bank_rows = [
        ("Garanti BBVA Ticari", "Aslan Computer", "TR66 0006 2000 4810 0019 8831 01", "", "TRY", 642800.0),
        ("Vak\u0131fBank Sirket Hesabi", "Aslan Computer", "TR12 0001 5001 5800 7301 2290 44", "", "TRY", 412440.0),
        ("Is Bankasi Operasyon", "Aslan Computer", "TR89 0006 4000 0002 3900 1198 02", "", "TRY", 125000.0),
        ("Merkez Teknik Servis Kasasi", "Aslan Computer", "", "KASA-01", "TRY", 48200.0),
        ("Sanal POS Konsolidasyonu", "Aslan Computer", "", "POS-01", "TRY", 245000.20),
    ]
    try:
        db.cursor.execute(
            "CREATE TABLE IF NOT EXISTS bank_accounts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, bank_name TEXT, account_holder TEXT, iban TEXT, "
            "account_number TEXT, branch_code TEXT, currency TEXT DEFAULT 'TRY', is_active INTEGER DEFAULT 1, "
            "created_at TEXT, current_balance REAL DEFAULT 0, is_deleted INTEGER DEFAULT 0)"
        )
        count = db.cursor.execute("SELECT COUNT(*) FROM bank_accounts").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO bank_accounts (bank_name, account_holder, iban, account_number, currency, current_balance) VALUES (?, ?, ?, ?, ?, ?)",
                bank_rows,
            )
            db.conn.commit()
    except Exception:
        pass
    offer_rows = [
        ("TEKLIF-0010", "Baris Cevik", "Bilisim Ltd.", 8555.00, "accepted", "2026-09-21"),
        ("TEKLIF-0009", "Cemre Ekin", "", 8260.00, "accepted", "2026-09-21"),
        ("TEKLIF-0008", "Emre Uslu", "", 7965.00, "accepted", "2026-09-20"),
        ("TEKLIF-0007", "Pelin Aksoy", "Aksoy Medya", 7670.00, "accepted", "2026-09-20"),
        ("TEKLIF-0006", "Gokhan Polat", "Akilli Ev Sist.", 7375.00, "accepted", "2026-09-19"),
        ("TEKLIF-0005", "Ece Tas", "", 7080.00, "accepted", "2026-09-19"),
        ("TEKLIF-0004", "Ayse Demir", "Demir Teknoloji", 23936.25, "rejected", "2026-09-18"),
        ("TEKLIF-0003", "Cem Yildiz", "Yildiz Elektronik", 23936.25, "rejected", "2026-09-18"),
        ("TEKLIF-0002", "Murat Kaya", "Kaya Sistem", 23936.25, "rejected", "2026-09-17"),
        ("TEKLIF-0001", "Selin Can", "Can Otomasyon", 23936.25, "rejected", "2026-09-17"),
    ]
    try:
        db.cursor.execute(
            "CREATE TABLE IF NOT EXISTS offers ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, offer_no TEXT UNIQUE, customer_name TEXT, company_name TEXT, "
            "currency_code TEXT DEFAULT 'TRY', currency_symbol TEXT DEFAULT 'TRY', total REAL DEFAULT 0, "
            "total_try REAL DEFAULT 0, status TEXT DEFAULT 'draft', accepted_by TEXT, pdf_path TEXT, created_at TEXT)"
        )
        db.cursor.execute(
            "CREATE TABLE IF NOT EXISTS offer_items ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER NOT NULL, description TEXT, "
            "qty REAL DEFAULT 1, unit_price REAL DEFAULT 0, line_total REAL DEFAULT 0)"
        )
        count = db.cursor.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO offers (offer_no, customer_name, company_name, total, total_try, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(a, b, c, d, d, e, f) for a, b, c, d, e, f in offer_rows],
            )
            db.conn.commit()
    except Exception:
        pass
    contract_rows = [
        (2, "Aksoy Medya SLA", "Kurumsal SLA", "2026-01-01", "2026-12-31", "Aktif", 180000.0),
        (5, "Acar Mimarlik Destek", "Gold SLA", "2025-10-15", "2026-10-15", "Yenileme Bekliyor", 95000.0),
        (3, "Bilisim Yazilim Bakim", "Silver SLA", "2026-01-06", "2027-01-06", "Aktif", 64000.0),
        (1, "Eren Lojistik Depo", "Platinum SLA", "2026-03-01", "2027-03-01", "Aktif", 240000.0),
    ]
    contract_rows.extend(
        [(i + 6, "Demo SLA {:02d}".format(i), ["Gold SLA", "Silver SLA", "Platinum SLA"][i % 3], "2026-01-01", "2027-01-01", "Aktif", 40000.0 + (i * 5000.0)) for i in range(20)]
    )
    try:
        db.cursor.execute(
            "CREATE TABLE IF NOT EXISTS contracts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, title TEXT, start_date TEXT, end_date TEXT, "
            "contract_type TEXT, price REAL DEFAULT 0, status TEXT DEFAULT 'Aktif', description TEXT, created_at TEXT)"
        )
        count = db.cursor.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO contracts (customer_id, title, contract_type, start_date, end_date, status, price) VALUES (?, ?, ?, ?, ?, ?, ?)",
                contract_rows,
            )
            db.conn.commit()
    except Exception:
        pass
    tracking_rows = [
        ("GAR-2026-089", "Zeynep Celik", "ASUS ROG Strix G16", "Infocomm TR", "4598210348", "2026-09-21", "Yurtici", "Dis Serviste"),
        ("GAR-2026-084", "Ahmet Yilmaz", "Dell PowerEdge T340", "Index Bilgisayar", "9823411200", "2026-09-18", "Aras", "Onay Bekliyor"),
        ("GAR-2026-077", "Boran Teknoloji A.S.", "HP LaserJet M608", "Eren Depo", "124589211", "2026-09-14", "MNG", "Teslim Alindi"),
        ("GAR-2026-072", "Baris Cevik", "Hikvision NVR 16CH", "Hikvision TR", "", "2026-09-10", "Kurye", "Musteriye Hazir"),
    ]
    tracking_statuses = ["Dis Serviste", "Onay Bekliyor", "Teslim Alindi", "Musteriye Hazir"]
    tracking_rows.extend(
        [("GAR-2026-{:03d}".format(71 - i), "Demo Musteri {:02d}".format(i), "Demo Cihaz {:02d}".format(i), "Yetkili Servis TR", "45{:07d}".format(i), "2026-09-{:02d}".format(1 + (i % 25)), "Yurtici", tracking_statuses[i % 4]) for i in range(14)]
    )
    try:
        db.cursor.execute(
            "CREATE TABLE IF NOT EXISTS external_warranty_tracking ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, internal_tracking_no TEXT, customer_name TEXT, product_name TEXT, "
            "external_service_name TEXT, external_service_no TEXT, sent_date TEXT, outbound_cargo_no TEXT, "
            "inbound_cargo_no TEXT, status TEXT, notes TEXT, created_at TEXT)"
        )
        count = db.cursor.execute("SELECT COUNT(*) FROM external_warranty_tracking").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO external_warranty_tracking (internal_tracking_no, customer_name, product_name, external_service_name, external_service_no, sent_date, outbound_cargo_no, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                tracking_rows,
            )
            db.conn.commit()
    except Exception:
        pass
    personnel_rows = [
        ("Selim Celik", "Kidemli Teknisyen", "0555 111 0001", 48500, 14250, "TK-084", "selim@example.com", "Teknik Servis"),
        ("Eren Uysal", "Saha Muhendisi", "0555 111 0002", 44000, 11800, "SH-012", "eren@example.com", "Saha"),
        ("Burak Sahin", "Stajyer Teknisyen", "0555 111 0003", 22500, 3400, "ST-009", "burak@example.com", "Teknik Servis"),
        ("Pelin Aksoy", "Muhasebe Muduru", "0555 111 0004", 52000, 0, "FN-004", "pelin@example.com", "Finans"),
        ("Murat Keskin", "Yedek Parca Sorumlusu", "0555 111 0005", 36000, 5600, "DP-006", "murat@example.com", "Depo"),
        ("Aslan Computer", "Genel Yonetici", "0555 111 0006", 65000, 0, "ROOT", "admin@example.com", "Yonetim"),
    ]
    try:
        count = db.cursor.execute("SELECT COUNT(*) FROM personnel").fetchone()[0]
        if not count:
            db.cursor.executemany(
                "INSERT INTO personnel (name, role, phone, salary, commission, tc_no, email, department) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                personnel_rows,
            )
            db.conn.commit()
    except Exception:
        pass


def reference_inventory() -> list[str]:
    reference_root = Path("C:\\Users\\yedek\\Desktop\\Figma tasar\u0131m")
    if not reference_root.exists():
        return []
    return sorted(str(path) for path in reference_root.rglob("*.png"))


REFERENCE_CANVAS_SIZES = {
    "transaction_basket": (1320, 1226),
    "transaction_basket_populated": (1320, 1226),
    "transaction_basket_service": (1320, 1226),
    "transaction_basket_usd": (1320, 1226),
    "side_menu": (272, 1024),
    "settings_sidebar": (280, 1280),
    "service_board": (1268, 1220),
    "job_service_tracking": (1268, 1220),
    "contracts": (1080, 992),
    "service_status": (1112, 1013),
    "external_tracking": (1268, 1220),
    "field_service": (1280, 1220),
    "technician_panel": (1280, 837),
    "bank_accounts": (1088, 988),
    "check_notes": (1280, 1024),
    "accounting": (1088, 988),
    "service_list": (1088, 988),
    "offers": (1088, 988),
    "audit_log": (1088, 988),
    "user_management": (1088, 1176),
    "voice_assistant_shortcuts": (1088, 642),
    "voice_assistant_settings": (1088, 685),
    "autonomous_agents": (1088, 810),
    "system_identity": (1088, 810),
    "integration_hub": (1088, 742),
    "new_customer": (864, 820),
    "edit_customer": (864, 820),
    "new_service": (1256, 960),
    "edit_service": (1256, 960),
    "pattern_editor": (380, 450),
    "voice_shortcut_editor": (620, 420),
    "personnel": (1100, 988),
    "customers": (1280, 960),
    "stock": (1280, 1024),
}
REFERENCE_RENDER_WAIT_MS = {
    "customers": 1000,
    "field_service": 1000,
}


def run(output_root: Path) -> dict[str, object]:
    from src.database import Database
    from src.utils.reference_typography import apply_reference_font
    from src.utils.theme_manager import ThemeManager

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    font_families = apply_reference_font(app)
    font_family = "Inter" if "Inter" in font_families else "Segoe UI"
    app.setFont(QFont(font_family, 9))
    app.setStyleSheet(ThemeManager.get_stylesheet("Koyu Mavi"))
    fd, db_path = tempfile.mkstemp(prefix="ayec_visual_", suffix=".db")
    os.close(fd)
    os.unlink(db_path)
    db = Database(db_path)
    seed_visual_fixture(db, currency_rates=True)
    previous_visual_mode = os.environ.get("AYEC_VISUAL_ACCEPTANCE")
    os.environ["AYEC_VISUAL_ACCEPTANCE"] = "1"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root.resolve() / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    results: list[dict[str, object]] = []

    try:
        requested_pages = {
            name.strip() for name in os.environ.get("AYEC_VISUAL_PAGES", "").split(",")
            if name.strip()
        }
        for theme_name in ("AYEC", "Koyu Mavi"):
            for page_name, factory in page_factories(db).items():
                if requested_pages and page_name not in requested_pages:
                    continue
                page = factory()
                page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
                canvas_width, canvas_height = REFERENCE_CANVAS_SIZES.get(
                    page_name, (1280, 1024)
                )
                page.resize(canvas_width, canvas_height)
                ThemeManager.apply_theme(
                    app,
                    theme_name,
                    window=page,
                    animate=False,
                )
                ThemeManager.refresh_widget_tree(page)
                page.show()
                app.processEvents()
                page.setMaximumSize(canvas_width, canvas_height)
                page.resize(canvas_width, canvas_height)
                app.processEvents()
                QTest.qWait(REFERENCE_RENDER_WAIT_MS.get(page_name, 250))
                app.processEvents()
                screenshot = output_dir / (
                    f"{theme_name.lower().replace(' ', '_')}_{page_name}.png"
                )
                saved = bool(page.grab().save(str(screenshot), "PNG"))
                has_content, sampled_colors = image_has_visual_content(page)
                selection_issues = visible_table_selection_issues(page)
                button_warnings = clipped_button_warnings(page)
                geometry_issues = service_list_geometry_issues(page) if page_name == "service_list" else []
                passed = saved and has_content and not selection_issues and not geometry_issues
                results.append(
                    {
                        "theme": theme_name,
                        "page": page_name,
                        "screenshot": str(screenshot),
                        "saved": saved,
                        "has_visual_content": has_content,
                        "sampled_colors": sampled_colors,
                        "table_selection_issues": selection_issues,
                        "clipped_button_warnings": button_warnings,
                        "geometry_issues": geometry_issues,
                        "status": "passed" if passed else "failed",
                    }
                )
                page.close()
                page.deleteLater()
                app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                app.processEvents()
    finally:
        if previous_visual_mode is None:
            os.environ.pop("AYEC_VISUAL_ACCEPTANCE", None)
        else:
            os.environ["AYEC_VISUAL_ACCEPTANCE"] = previous_visual_mode
        if hasattr(db, "close"):
            db.close()
        try:
            Path(db_path).unlink(missing_ok=True)
        except OSError:
            pass

    passed = all(item["status"] == "passed" for item in results)
    references = reference_inventory()
    report = {
        "status": "passed" if passed else "failed",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "resolution": {
            "default": [1280, 1024],
            "overrides": {
                name: list(size) for name, size in REFERENCE_CANVAS_SIZES.items()
            },
        },
        "reference_count": len(references),
        "references": references,
        "results": results,
    }
    report_path = output_dir / "desktop_visual_acceptance.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    report["report"] = str(report_path)
    if not passed:
        raise RuntimeError(f"Desktop visual acceptance failed: {report_path}")
    return report


def main() -> int:
    report = run(ROOT / "artifacts" / "desktop_visual_acceptance")
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": report["report"],
                "screenshots": len(report["results"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
