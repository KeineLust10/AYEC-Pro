# -*- coding: utf-8 -*-

from datetime import datetime

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from src.ui.dialogs.partner_documents_dialog import PartnerDocumentsDialog
from src.ui.dialogs.photo_gallery_dialog import PhotoGalleryDialog
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_info, show_success


class PartnerShipmentDialog(ModernDialog):
    TABLE_NAME = "partner_shipments"

    def __init__(self, db, partner, parent=None, shipment_id=None):
        self.db = db
        self.partner = dict(partner) if hasattr(partner, "keys") else (partner or {})
        self.shipment_id = shipment_id
        self.currency_code = CurrencyHelper.get_code(self.db)
        title = "Partner Gonderi Kaydi"
        if shipment_id:
            title = "Partner Gonderi Kaydi Duzenle"
        super().__init__(title, parent, width=980, height=860)
        self.set_wheel_scroll_enabled(True)
        self._ensure_tables()
        self._build_ui()
        if shipment_id:
            self._load_shipment()

    def _ensure_tables(self):
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                partner_name TEXT NOT NULL,
                customer_name TEXT,
                product_name TEXT,
                serial_no TEXT,
                issue_summary TEXT,
                shipment_reason TEXT,
                outbound_tracking_no TEXT,
                return_tracking_no TEXT,
                external_ref_no TEXT,
                status TEXT DEFAULT 'Hazirlaniyor',
                partner_cost REAL DEFAULT 0,
                customer_price REAL DEFAULT 0,
                currency TEXT DEFAULT 'TRY',
                quote_status TEXT DEFAULT 'Beklemede',
                quote_amount REAL DEFAULT 0,
                approval_status TEXT DEFAULT 'Onay Bekliyor',
                contract_type TEXT,
                sla_level TEXT,
                accessories TEXT,
                return_qc TEXT,
                cosmetic_status TEXT,
                missing_parts TEXT,
                cost_responsibility TEXT,
                notes TEXT,
                sent_at TEXT,
                returned_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.db.cursor.execute("PRAGMA table_info(partner_shipments)")
        existing = {row[1] for row in (self.db.cursor.fetchall() or [])}
        for column_name, column_sql in (
            ("partner_id", "INTEGER DEFAULT 0"),
            ("partner_name", "TEXT DEFAULT ''"),
            ("customer_name", "TEXT"),
            ("product_name", "TEXT"),
            ("serial_no", "TEXT"),
            ("issue_summary", "TEXT"),
            ("shipment_reason", "TEXT"),
            ("outbound_tracking_no", "TEXT"),
            ("return_tracking_no", "TEXT"),
            ("external_ref_no", "TEXT"),
            ("status", "TEXT DEFAULT 'Hazirlaniyor'"),
            ("partner_cost", "REAL DEFAULT 0"),
            ("customer_price", "REAL DEFAULT 0"),
            ("quote_amount", "REAL DEFAULT 0"),
            ("quote_status", "TEXT DEFAULT 'Beklemede'"),
            ("approval_status", "TEXT DEFAULT 'Onay Bekliyor'"),
            ("currency", "TEXT DEFAULT 'TRY'"),
            ("contract_type", "TEXT"),
            ("sla_level", "TEXT"),
            ("accessories", "TEXT"),
            ("return_qc", "TEXT"),
            ("cosmetic_status", "TEXT"),
            ("missing_parts", "TEXT"),
            ("cost_responsibility", "TEXT"),
            ("notes", "TEXT"),
            ("sent_at", "TEXT"),
            ("returned_at", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ):
            if column_name not in existing:
                self.db.cursor.execute(f"ALTER TABLE partner_shipments ADD COLUMN {column_name} {column_sql}")
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_finance_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                entry_type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'TRY',
                payment_method TEXT,
                description TEXT,
                entry_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                event_type TEXT NOT NULL,
                detail TEXT,
                event_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        timeline_cols = {
            row[1]
            for row in self.db.cursor.execute(
                "PRAGMA table_info(partner_timeline)"
            ).fetchall()
        }
        for column_name, column_sql in (
            ("partner_id", "INTEGER DEFAULT 0"),
            ("shipment_id", "INTEGER"),
            ("event_type", "TEXT DEFAULT 'GENEL'"),
            ("detail", "TEXT"),
            ("event_date", "TEXT DEFAULT ''"),
            ("created_at", "TEXT DEFAULT ''"),
        ):
            if column_name not in timeline_cols:
                self.db.cursor.execute(
                    f"ALTER TABLE partner_timeline ADD COLUMN {column_name} {column_sql}"
                )
        if "title" in timeline_cols:
            self.db.cursor.execute(
                """
                UPDATE partner_timeline
                SET event_type = COALESCE(NULLIF(event_type, ''), NULLIF(title, ''), 'GENEL')
                WHERE COALESCE(event_type, '') = ''
                """
            )
        else:
            self.db.cursor.execute(
                """
                UPDATE partner_timeline
                SET event_type = COALESCE(NULLIF(event_type, ''), 'GENEL')
                WHERE COALESCE(event_type, '') = ''
                """
            )
        self.db.cursor.execute(
            """
            UPDATE partner_timeline
            SET event_date = COALESCE(NULLIF(event_date, ''), NULLIF(created_at, ''), datetime('now'))
            WHERE COALESCE(event_date, '') = ''
            """
        )
        self.db.cursor.execute(
            """
            UPDATE partner_timeline
            SET created_at = COALESCE(NULLIF(created_at, ''), NULLIF(event_date, ''), datetime('now'))
            WHERE COALESCE(created_at, '') = ''
            """
        )
        self.db.conn.commit()

    def _build_ui(self):
        card = QFrame()
        card.setStyleSheet(theme_qss(DesignTokens.get_card_qss()))
        grid = QGridLayout(card)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(12)

        def add_field(label_text, widget, row, col, colspan=1):
            label = QLabel(label_text)
            label.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700;"))
            box = QVBoxLayout()
            box.setSpacing(6)
            box.addWidget(label)
            box.addWidget(widget)
            grid.addLayout(box, row, col, 1, colspan)

        self.inp_partner = QLineEdit(str(self.partner.get("name") or ""))
        self.inp_partner.setReadOnly(True)
        self.inp_partner.setFixedHeight(42)
        self.inp_partner.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_customer = QLineEdit()
        self.inp_customer.setPlaceholderText("Musteri adi")
        self.inp_customer.setFixedHeight(42)
        self.inp_customer.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_product = QLineEdit()
        self.inp_product.setPlaceholderText("Cihaz / Urun / Model")
        self.inp_product.setFixedHeight(42)
        self.inp_product.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_serial = QLineEdit()
        self.inp_serial.setPlaceholderText("Seri no / Barkod")
        self.inp_serial.setFixedHeight(42)
        self.inp_serial.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_issue = QTextEdit()
        self.inp_issue.setPlaceholderText("Ariza veya gonderim konusu")
        self.inp_issue.setMinimumHeight(90)
        self.inp_issue.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_reason = QTextEdit()
        self.inp_reason.setPlaceholderText("Partnere neden gonderiliyor?")
        self.inp_reason.setMinimumHeight(90)
        self.inp_reason.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_external_ref = QLineEdit()
        self.inp_external_ref.setPlaceholderText("Partner kayit / servis no")
        self.inp_external_ref.setFixedHeight(42)
        self.inp_external_ref.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_outbound = QLineEdit()
        self.inp_outbound.setPlaceholderText("Gidis kargo no")
        self.inp_outbound.setFixedHeight(42)
        self.inp_outbound.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_return = QLineEdit()
        self.inp_return.setPlaceholderText("Donus kargo no")
        self.inp_return.setFixedHeight(42)
        self.inp_return.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_status = QLineEdit("Hazirlaniyor")
        self.inp_status.setFixedHeight(42)
        self.inp_status.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_quote_status = QLineEdit("Beklemede")
        self.inp_quote_status.setFixedHeight(42)
        self.inp_quote_status.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.spin_quote_amount = QDoubleSpinBox()
        self.spin_quote_amount.setRange(0, 10_000_000)
        self.spin_quote_amount.setDecimals(2)
        self.spin_quote_amount.setSuffix(f" {CurrencyHelper.get_symbol(currency_code=self.currency_code)}")
        self.spin_quote_amount.setFixedHeight(42)
        self.spin_quote_amount.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_approval = QLineEdit("Onay Bekliyor")
        self.inp_approval.setFixedHeight(42)
        self.inp_approval.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.spin_partner_cost = QDoubleSpinBox()
        self.spin_partner_cost.setRange(0, 10_000_000)
        self.spin_partner_cost.setDecimals(2)
        self.spin_partner_cost.setSuffix(f" {CurrencyHelper.get_symbol(currency_code=self.currency_code)}")
        self.spin_partner_cost.setFixedHeight(42)
        self.spin_partner_cost.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.spin_customer_price = QDoubleSpinBox()
        self.spin_customer_price.setRange(0, 10_000_000)
        self.spin_customer_price.setDecimals(2)
        self.spin_customer_price.setSuffix(f" {CurrencyHelper.get_symbol(currency_code=self.currency_code)}")
        self.spin_customer_price.setFixedHeight(42)
        self.spin_customer_price.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_contract = QLineEdit(str(self.partner.get("contract_type") or "Standart Anlasma"))
        self.inp_contract.setReadOnly(True)
        self.inp_contract.setFixedHeight(42)
        self.inp_contract.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_sla = QLineEdit(str(self.partner.get("sla_level") or "24 Saat Donus"))
        self.inp_sla.setReadOnly(True)
        self.inp_sla.setFixedHeight(42)
        self.inp_sla.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_accessories = QTextEdit()
        self.inp_accessories.setPlaceholderText("Gonderilen aksesuarlar / paket icerigi")
        self.inp_accessories.setMinimumHeight(72)
        self.inp_accessories.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_return_qc = QLineEdit("Beklemede")
        self.inp_return_qc.setFixedHeight(42)
        self.inp_return_qc.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_cosmetic = QLineEdit("Kontrol Edilmedi")
        self.inp_cosmetic.setFixedHeight(42)
        self.inp_cosmetic.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_missing_parts = QLineEdit("Yok")
        self.inp_missing_parts.setFixedHeight(42)
        self.inp_missing_parts.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_cost_responsibility = QLineEdit("Partner")
        self.inp_cost_responsibility.setFixedHeight(42)
        self.inp_cost_responsibility.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.date_sent = QDateEdit(QDate.currentDate())
        self.date_sent.setCalendarPopup(True)
        self.date_sent.setDisplayFormat("dd.MM.yyyy")
        self.date_sent.setFixedHeight(42)
        self.date_sent.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.date_returned = QDateEdit(QDate.currentDate())
        self.date_returned.setCalendarPopup(True)
        self.date_returned.setDisplayFormat("dd.MM.yyyy")
        self.date_returned.setFixedHeight(42)
        self.date_returned.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_notes = QTextEdit()
        self.inp_notes.setPlaceholderText("Ic notlar, teslim detaylari, paket icerigi")
        self.inp_notes.setMinimumHeight(90)
        self.inp_notes.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        add_field("Calisma Ortagi", self.inp_partner, 0, 0)
        add_field("Musteri", self.inp_customer, 0, 1)
        add_field("Urun", self.inp_product, 1, 0)
        add_field("Seri No", self.inp_serial, 1, 1)
        add_field("Ariza / Konu", self.inp_issue, 2, 0)
        add_field("Gonderim Nedeni", self.inp_reason, 2, 1)
        add_field("Partner Ref / Servis No", self.inp_external_ref, 3, 0)
        add_field("Durum", self.inp_status, 3, 1)
        add_field("Gidis Kargo", self.inp_outbound, 4, 0)
        add_field("Donus Kargo", self.inp_return, 4, 1)
        add_field("Partner Maliyeti", self.spin_partner_cost, 5, 0)
        add_field("Musteriye Yansitilan", self.spin_customer_price, 5, 1)
        add_field("Teklif Durumu", self.inp_quote_status, 6, 0)
        add_field("Teklif Tutari", self.spin_quote_amount, 6, 1)
        add_field("Onay Durumu", self.inp_approval, 7, 0)
        add_field("Gonderim Tarihi", self.date_sent, 7, 1)
        add_field("Sozlesme", self.inp_contract, 8, 0)
        add_field("SLA", self.inp_sla, 8, 1)
        add_field("Aksesuarlar / Paket", self.inp_accessories, 9, 0)
        add_field("Maliyet Sorumlulugu", self.inp_cost_responsibility, 9, 1)
        add_field("Donus Kalite Kontrol", self.inp_return_qc, 10, 0)
        add_field("Kozmetik Durum", self.inp_cosmetic, 10, 1)
        add_field("Eksik Parca", self.inp_missing_parts, 11, 0)
        add_field("Donus Tarihi", self.date_returned, 11, 1)
        add_field("Notlar", self.inp_notes, 12, 0, 2)

        self.add_widget(card)
        self.add_cancel_button("Vazgec")
        self.add_button("Belgeler", "secondary", self.open_documents)
        self.add_button("Fotograf Galerisi", "secondary", self.open_photo_gallery)
        self.add_button("Kaydet ve Kapat", "primary", self.save)

    def _photo_tracking_key(self):
        base = self.inp_serial.text().strip() or self.inp_product.text().strip() or "shipment"
        partner_id = self.partner.get("id") or "0"
        shipment_id = self.shipment_id or "new"
        return f"partner-{partner_id}-{shipment_id}-{base}"

    def open_photo_gallery(self):
        dlg = PhotoGalleryDialog(
            self.db,
            self._photo_tracking_key(),
            self,
            read_only=False,
            stage="Partner",
        )
        dlg.exec()

    def open_documents(self):
        dlg = PartnerDocumentsDialog(self.db, self.partner, self, shipment_id=self.shipment_id)
        dlg.exec()

    def _load_shipment(self):
        self.db.cursor.execute(
            """
            SELECT customer_name, product_name, serial_no, issue_summary, shipment_reason,
                   outbound_tracking_no, return_tracking_no, external_ref_no, status,
                   partner_cost, customer_price, currency, quote_status, quote_amount, approval_status, contract_type, sla_level,
                   accessories, return_qc, cosmetic_status, missing_parts, cost_responsibility,
                   notes, sent_at, returned_at
            FROM partner_shipments
            WHERE id = ?
            """,
            (self.shipment_id,),
        )
        row = self.db.cursor.fetchone()
        if not row:
            return
        (
            customer_name,
            product_name,
            serial_no,
            issue_summary,
            shipment_reason,
            outbound_tracking_no,
            return_tracking_no,
            external_ref_no,
            status,
            partner_cost,
            customer_price,
            currency,
            quote_status,
            quote_amount,
            approval_status,
            contract_type,
            sla_level,
            accessories,
            return_qc,
            cosmetic_status,
            missing_parts,
            cost_responsibility,
            notes,
            sent_at,
            returned_at,
        ) = row
        self.inp_customer.setText(customer_name or "")
        self.inp_product.setText(product_name or "")
        self.inp_serial.setText(serial_no or "")
        self.inp_issue.setPlainText(issue_summary or "")
        self.inp_reason.setPlainText(shipment_reason or "")
        self.inp_outbound.setText(outbound_tracking_no or "")
        self.inp_return.setText(return_tracking_no or "")
        self.inp_external_ref.setText(external_ref_no or "")
        self.inp_status.setText(status or "")
        self.spin_partner_cost.setValue(float(partner_cost or 0))
        self.spin_customer_price.setValue(float(customer_price or 0))
        self.currency_code = str(currency or self.currency_code or "TRY").upper()
        symbol = CurrencyHelper.get_symbol(currency_code=self.currency_code)
        self.spin_partner_cost.setSuffix(f" {symbol}")
        self.spin_customer_price.setSuffix(f" {symbol}")
        self.spin_quote_amount.setSuffix(f" {symbol}")
        self.inp_quote_status.setText(quote_status or "")
        self.spin_quote_amount.setValue(float(quote_amount or 0))
        self.inp_approval.setText(approval_status or "")
        self.inp_contract.setText(contract_type or "")
        self.inp_sla.setText(sla_level or "")
        self.inp_accessories.setPlainText(accessories or "")
        self.inp_return_qc.setText(return_qc or "")
        self.inp_cosmetic.setText(cosmetic_status or "")
        self.inp_missing_parts.setText(missing_parts or "")
        self.inp_cost_responsibility.setText(cost_responsibility or "")
        self.inp_notes.setPlainText(notes or "")
        if sent_at:
            self.date_sent.setDate(QDate.fromString(sent_at, "yyyy-MM-dd"))
        if returned_at:
            self.date_returned.setDate(QDate.fromString(returned_at, "yyyy-MM-dd"))

    def save(self):
        partner_id = self.partner.get("id")
        if not partner_id:
            show_error(self, "Partner secimi bulunamadi.")
            return
        customer_name = self.inp_customer.text().strip()
        product_name = self.inp_product.text().strip()
        if not customer_name or not product_name:
            show_error(self, "Musteri ve urun alanlari zorunludur.")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = (
            int(partner_id),
            str(self.partner.get("name") or "").strip(),
            customer_name,
            product_name,
            self.inp_serial.text().strip(),
            self.inp_issue.toPlainText().strip(),
            self.inp_reason.toPlainText().strip(),
            self.inp_outbound.text().strip(),
            self.inp_return.text().strip(),
            self.inp_external_ref.text().strip(),
            self.inp_status.text().strip() or "Hazirlaniyor",
            float(self.spin_partner_cost.value() or 0),
            float(self.spin_customer_price.value() or 0),
            self.currency_code,
            self.inp_quote_status.text().strip() or "Beklemede",
            float(self.spin_quote_amount.value() or 0),
            self.inp_approval.text().strip() or "Onay Bekliyor",
            self.inp_contract.text().strip(),
            self.inp_sla.text().strip(),
            self.inp_accessories.toPlainText().strip(),
            self.inp_return_qc.text().strip() or "Beklemede",
            self.inp_cosmetic.text().strip() or "Kontrol Edilmedi",
            self.inp_missing_parts.text().strip() or "Yok",
            self.inp_cost_responsibility.text().strip() or "Partner",
            self.inp_notes.toPlainText().strip(),
            self.date_sent.date().toString("yyyy-MM-dd"),
            self.date_returned.date().toString("yyyy-MM-dd"),
            now,
        )

        try:
            if self.shipment_id:
                self.db.cursor.execute(
                    """
                    UPDATE partner_shipments
                    SET partner_id = ?, partner_name = ?, customer_name = ?, product_name = ?, serial_no = ?,
                        issue_summary = ?, shipment_reason = ?, outbound_tracking_no = ?, return_tracking_no = ?,
                        external_ref_no = ?, status = ?, partner_cost = ?, customer_price = ?, currency = ?, quote_status = ?,
                        quote_amount = ?, approval_status = ?, contract_type = ?, sla_level = ?, accessories = ?,
                        return_qc = ?, cosmetic_status = ?, missing_parts = ?, cost_responsibility = ?, notes = ?,
                        sent_at = ?, returned_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    payload + (self.shipment_id,),
                )
            else:
                self.db.cursor.execute(
                    """
                    INSERT INTO partner_shipments (
                        partner_id, partner_name, customer_name, product_name, serial_no,
                        issue_summary, shipment_reason, outbound_tracking_no, return_tracking_no,
                        external_ref_no, status, partner_cost, customer_price, currency, quote_status,
                        quote_amount, approval_status, contract_type, sla_level, accessories, return_qc,
                        cosmetic_status, missing_parts, cost_responsibility, notes, sent_at,
                        returned_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload + (now,),
                )
                self.shipment_id = self.db.cursor.lastrowid
            self._append_timeline_event(
                "shipment_saved",
                "{product} | durum={status} | teklif={quote_status} | onay={approval}".format(
                    product=product_name,
                    status=self.inp_status.text().strip() or "Hazirlaniyor",
                    quote_status=self.inp_quote_status.text().strip() or "Beklemede",
                    approval=self.inp_approval.text().strip() or "Onay Bekliyor",
                ),
            )
            self.db.conn.commit()
            show_success(self, "Partner gonderi kaydi kaydedildi.")
            self.accept()
        except Exception as exc:
            show_error(self, f"Partner gonderi kaydi kaydedilemedi: {exc}")

    def _append_timeline_event(self, event_type, detail):
        if not self.shipment_id:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.cursor.execute(
            """
            INSERT INTO partner_timeline (partner_id, shipment_id, event_type, detail, event_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(self.partner.get("id") or 0),
                int(self.shipment_id),
                event_type,
                detail,
                self.date_sent.date().toString("yyyy-MM-dd"),
                now,
            ),
        )
