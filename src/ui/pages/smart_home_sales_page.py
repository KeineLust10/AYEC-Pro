# -*- coding: utf-8 -*-

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.utils.design_system import DesignTokens
from src.utils.tax_settings import TaxSettings
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success, show_warning
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import InlineNumberStepper


class SmartHomeProductPoolDialog(ModernDialog):
    def __init__(self, parent_page):
        super().__init__(title="Akilli Ev Urun Havuzu", parent=parent_page, width=980, height=620)
        self.parent_page = parent_page
        self.setModal(True)
        self.set_footer_visible(False)
        self._build_ui()
        self.refresh_table()

    @staticmethod
    def _value(row, key, default=None):
        if row is None:
            return default
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[key]
        except Exception:
            return default

    def _build_ui(self):
        self.setStyleSheet(
            theme_qss(
                """
                QDialog { background: @bg; }
                QLabel { color: @text; background: transparent; border: none; }
                """
            )
        )
        root = self.content_layout
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("Akıllı Ev Ürün Havuzu")
        title.setStyleSheet(theme_qss("font-size: 22px; font-weight: 900; color: @text;"))
        subtitle = QLabel("Stoktaki akıllı ev ürünlerini arayın, adet ve birim fiyat belirleyip teklife ekleyin.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(theme_qss("font-size: 12px; font-weight: 600; color: @text_muted;"))
        root.addWidget(title)
        root.addWidget(subtitle)

        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Ürün adı, kod, kategori veya barkod ile ara...")
        self.inp_search.setMinimumHeight(42)
        self.inp_search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_search.textChanged.connect(self.refresh_table)
        controls.addWidget(self.inp_search, 1)

        qty_lbl = QLabel("Adet")
        qty_lbl.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text_muted;"))
        controls.addWidget(qty_lbl)
        self.spn_qty = InlineNumberStepper(value=1, decimals=0)
        self.spn_qty.setRange(1, 9999)
        self.spn_qty.setMinimumHeight(42)
        controls.addWidget(self.spn_qty)

        price_lbl = QLabel("Birim Fiyat")
        price_lbl.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text_muted;"))
        controls.addWidget(price_lbl)
        self.inp_unit_price = InlineNumberStepper(value=0.0, decimals=2)
        self.inp_unit_price.setRange(0, 999999999)
        self.inp_unit_price.setMinimumHeight(42)
        controls.addWidget(self.inp_unit_price)
        root.addLayout(controls)

        self.tbl_products = QTableWidget(0, 9)
        self.tbl_products.setHorizontalHeaderLabels(["", "ID", "Kod", "Ürün", "Kategori", "Stok", "Fiyat", "PB", "Adet"])
        self.tbl_products.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_products.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl_products.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_products.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        self.tbl_products.setColumnHidden(1, True)
        self.tbl_products.verticalHeader().setDefaultSectionSize(38)
        self.tbl_products.itemSelectionChanged.connect(self._sync_selected_product_price)
        head = self.tbl_products.horizontalHeader()
        head.setSectionsMovable(False)
        head.setStretchLastSection(False)
        for column in (0, 2, 4, 5, 6, 7, 8):
            head.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        head.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        head.resizeSection(0, 36)
        head.resizeSection(2, 105)
        head.resizeSection(4, 140)
        head.resizeSection(5, 70)
        head.resizeSection(6, 85)
        head.resizeSection(7, 55)
        head.resizeSection(8, 132)
        root.addWidget(self.tbl_products, 1)

        footer = QHBoxLayout()
        self.lbl_result = QLabel("0 ürün")
        self.lbl_result.setStyleSheet(theme_qss("font-size: 12px; font-weight: 700; color: @text_muted;"))
        footer.addWidget(self.lbl_result)
        footer.addStretch()

        btn_close = QPushButton("Kapat")
        btn_close.setMinimumHeight(42)
        btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="lg")))
        btn_close.clicked.connect(self.reject)
        footer.addWidget(btn_close)

        btn_add = QPushButton("Seçili Ürünü Teklife Ekle")
        btn_add.setMinimumHeight(42)
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="lg")))
        btn_add.clicked.connect(self._add_selected_product)
        footer.addWidget(btn_add)
        root.addLayout(footer)

    def _clear_product_rows(self):
        for row_index in range(self.tbl_products.rowCount()):
            for column_index in (0, 8):
                widget = self.tbl_products.cellWidget(row_index, column_index)
                if widget is not None:
                    widget.setUpdatesEnabled(False)
                    widget.hide()
                    self.tbl_products.removeCellWidget(row_index, column_index)
                    widget.deleteLater()
        self.tbl_products.clearContents()
        self.tbl_products.setRowCount(0)

    @staticmethod
    def _centered_cell_widget(widget):
        holder = QWidget()
        holder.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        holder_layout = QHBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(0)
        holder_layout.addStretch(1)
        holder_layout.addWidget(widget)
        holder_layout.addStretch(1)
        return holder

    def _row_checkbox(self, row_index):
        holder = self.tbl_products.cellWidget(row_index, 0)
        return holder.findChild(QCheckBox) if holder is not None else None

    def _row_quantity_spin(self, row_index):
        holder = self.tbl_products.cellWidget(row_index, 8)
        return holder.findChild(InlineNumberStepper, "productPoolRowQty") if holder is not None else None

    def refresh_table(self):
        self.parent_page._refresh_product_table(self.inp_search.text().strip().lower())
        self.lbl_result.setText(f"{len(self.parent_page.filtered_products)} ürün")
        self.tbl_products.setUpdatesEnabled(False)
        try:
            self._clear_product_rows()
            self.tbl_products.setRowCount(len(self.parent_page.filtered_products))
            for r, row in enumerate(self.parent_page.filtered_products):
                currency = str(self._value(row, "currency", "TRY") or "TRY").upper()
                row_checkbox = QCheckBox()
                row_checkbox.setObjectName("productPoolRowCheck")
                row_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                self.tbl_products.setCellWidget(r, 0, self._centered_cell_widget(row_checkbox))
                values = [
                    str(self._value(row, "id", "") or ""),
                    str(self._value(row, "code", "") or ""),
                    str(self._value(row, "name", "") or ""),
                    str(self._value(row, "category", "") or ""),
                    str(int(float(self._value(row, "stock", 0) or 0))),
                    f"{float(self._value(row, 'price', 0) or 0):.2f}",
                    currency,
                ]
                for c, value in enumerate(values, start=1):
                    item = QTableWidgetItem(value)
                    if c == 2:
                        item.setToolTip(value)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    elif c in (5, 6, 7):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tbl_products.setItem(r, c, item)
                qty_spin = InlineNumberStepper(value=int(self.spn_qty.value() or 1), decimals=0)
                qty_spin.setObjectName("productPoolRowQty")
                qty_spin.setRange(1, 9999)
                qty_spin.setMinimumHeight(32)
                qty_spin.setFixedWidth(118)
                self.tbl_products.setCellWidget(r, 8, self._centered_cell_widget(qty_spin))
            self.tbl_products.doItemsLayout()
        finally:
            self.tbl_products.setUpdatesEnabled(True)
            self.tbl_products.viewport().update()

    def _selected_product_row(self):
        row_index = self.tbl_products.currentRow()
        if row_index < 0 or row_index >= len(self.parent_page.filtered_products):
            return None
        return self.parent_page.filtered_products[row_index]

    def _sync_selected_product_price(self):
        row = self._selected_product_row()
        if row:
            self.inp_unit_price.setValue(float(self._value(row, "price", 0.0) or 0.0))

    def _add_selected_product(self):
        selected_rows = []
        for row_index in range(self.tbl_products.rowCount()):
            checkbox = self._row_checkbox(row_index)
            if checkbox is not None and checkbox.isChecked():
                selected_rows.append((row_index, self.parent_page.filtered_products[row_index]))

        if not selected_rows:
            row = self._selected_product_row()
            if row:
                selected_rows = [(self.tbl_products.currentRow(), row)]

        if not selected_rows:
            show_warning(self, "Lütfen en az bir ürün seçin.")
            return

        for row_index, row in selected_rows:
            qty_widget = self._row_quantity_spin(row_index)
            qty = int(qty_widget.value()) if qty_widget is not None else int(self.spn_qty.value() or 1)
            self.parent_page._append_product_to_offer(
                row=row,
                qty=qty,
                unit_price=float(self._value(row, "price", self.inp_unit_price.value()) or self.inp_unit_price.value() or 0.0),
            )
        self.parent_page._refresh_selected_table()
        self.parent_page._update_offer_badge()
        show_success(self, f"{len(selected_rows)} ürün teklif sepetine eklendi.")


class SmartHomeSalesPage(QWidget):
    SMART_HOME_KEYWORDS = [
        "akıllı", "akilli", "smart", "hub", "priz", "röle", "role", "zil",
        "aydınlatma", "aydinlatma", "şarj", "sarj", "klima kontrol", "enerji",
        "kilit", "wii", "wiipro", "wiicom", "wiicap", "wiimmd", "termostat",
        "otomasyon", "interkom", "zigbee", "dimmer", "gateway", "sensor",
        "sensör", "perde", "siren",
    ]

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.products = []
        self.filtered_products = []
        self.selected_items = []
        self.product_pool_dialog = None
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        self.setObjectName("SmartHomeSalesPage")
        self.setStyleSheet(
            theme_qss(
                """
                QWidget#SmartHomeSalesPage { background: transparent; }
                QLabel { color: @text; background: transparent; border: none; }
                """
            )
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 8, 20, 20)
        root.setSpacing(14)

        hero = QFrame()
        hero.setStyleSheet(
            theme_qss(
                """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f4c81, stop:1 #1f7a8c);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 24px;
                """
            )
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(18)

        title_box = QVBoxLayout()
        title = QLabel("Akıllı Ev Proforma")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: 900;")
        subtitle = QLabel("Popup \u00fcr\u00fcn havuzu, sade sat\u0131\u015f ak\u0131\u015f\u0131 ve AYEC Pro proforma mant\u0131\u011f\u0131yla PDF \u00fcretimi")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.82); font-size: 12px; font-weight: 600;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hero_layout.addLayout(title_box, 1)

        self.lbl_offer_badge = QLabel()
        self.lbl_offer_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_offer_badge.setMinimumSize(220, 64)
        self.lbl_offer_badge.setStyleSheet(
            "background: rgba(255,255,255,0.14); color: white; border-radius: 18px; font-size: 15px; font-weight: 800; padding: 8px 14px;"
        )
        hero_layout.addWidget(self.lbl_offer_badge)
        root.addWidget(hero)

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_left_column(), 11)
        body.addWidget(self._build_right_column(), 13)
        root.addLayout(body, 1)

    def _panel(self, title, subtitle=None):
        frame = QFrame()
        frame.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 22px;"))
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        ttl = QLabel(title)
        ttl.setStyleSheet(theme_qss("font-size: 17px; font-weight: 900; color: @text;"))
        layout.addWidget(ttl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setWordWrap(True)
            sub.setStyleSheet(theme_qss("font-size: 11px; font-weight: 600; color: @text_muted;"))
            layout.addWidget(sub)
        return frame, layout

    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(theme_qss("font-size: 11px; color: @text_muted; font-weight: 800;"))
        return lbl

    def _styled_line(self):
        w = QLineEdit()
        w.setMinimumHeight(42)
        w.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        return w

    def _styled_combo(self):
        w = QComboBox()
        w.setEditable(True)
        w.setMinimumHeight(42)
        w.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        return w

    def _build_left_column(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        info_card, info_layout = self._panel(
            "Proje ve Müşteri Bilgileri",
            "Teklif üst sayfasındaki proje özeti bu alanlardan oluşur."
        )
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.cmb_customer = self._styled_combo()
        self.cmb_customer.currentIndexChanged.connect(self._fill_customer_fields)

        self.inp_offer_no = self._styled_line()
        self.inp_offer_no.setReadOnly(True)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setMinimumHeight(42)
        self.date_edit.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.date_edit.dateChanged.connect(self._update_offer_badge)

        self.inp_company = self._styled_line()
        self.inp_contact = self._styled_line()
        self.inp_phone = self._styled_line()
        self.inp_email = self._styled_line()
        self.inp_project = self._styled_line()

        self.spn_block = InlineNumberStepper(value=1, decimals=0)
        self.spn_block.setRange(1, 9999)
        self.spn_block.setMinimumHeight(42)

        self.spn_flat = InlineNumberStepper(value=1, decimals=0)
        self.spn_flat.setRange(1, 9999)
        self.spn_flat.setMinimumHeight(42)

        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Teklife eklenecek özel not, kapsam özeti veya proje açıklaması...")
        self.txt_notes.setMinimumHeight(120)
        self.txt_notes.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        entries = [
            ("Müşteri", self.cmb_customer, "Teklif No", self.inp_offer_no),
            ("Firma / Kurum", self.inp_company, "Tarih", self.date_edit),
            ("Yetkili Kişi", self.inp_contact, "Telefon", self.inp_phone),
            ("E-Posta", self.inp_email, "Proje Adı", self.inp_project),
            ("Blok Sayısı", self.spn_block, "Daire Sayısı", self.spn_flat),
        ]
        row = 0
        for left_label, left_widget, right_label, right_widget in entries:
            form.addWidget(self._field_label(left_label), row, 0)
            form.addWidget(self._field_label(right_label), row, 1)
            form.addWidget(left_widget, row + 1, 0)
            form.addWidget(right_widget, row + 1, 1)
            row += 2

        form.addWidget(self._field_label("Teklif Notu"), row, 0, 1, 2)
        form.addWidget(self.txt_notes, row + 1, 0, 1, 2)
        info_layout.addLayout(form)

        actions = QHBoxLayout()
        actions.setSpacing(10)

        btn_pool = QPushButton("Akıllı Ev Ürün Havuzunu Aç")
        btn_pool.setMinimumHeight(44)
        btn_pool.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="lg")))
        btn_pool.clicked.connect(self._open_product_pool)
        actions.addWidget(btn_pool, 1)

        self.lbl_pool_hint = QLabel("Ürün havuzu ayrı pencerede açılır. Sayfa sadece teklif özetine odaklanır.")
        self.lbl_pool_hint.setWordWrap(True)
        self.lbl_pool_hint.setStyleSheet(
            theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 14px; padding: 10px 14px; font-size: 12px; font-weight: 700; color: @text_muted;")
        )
        actions.addWidget(self.lbl_pool_hint, 1)
        info_layout.addLayout(actions)
        layout.addWidget(info_card)
        layout.addStretch()
        return container

    def _build_right_column(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        summary_card, summary_layout = self._panel(
            "Teklif Sepeti",
            "Ürünler popup havuzdan eklenir. Bu alan teklifin son halini gösterir."
        )
        self.tbl_selected = QTableWidget(0, 7)
        self.tbl_selected.setHorizontalHeaderLabels(["Ürün", "Kod", "Kategori", "Açıklama", "Adet", "Birim", "Toplam"])
        self.tbl_selected.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_selected.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_selected.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_selected.setMinimumHeight(430)
        self.tbl_selected.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        head = self.tbl_selected.horizontalHeader()
        head.resizeSection(0, 170)
        head.resizeSection(1, 85)
        head.resizeSection(2, 110)
        head.resizeSection(3, 215)
        head.resizeSection(4, 55)
        head.resizeSection(5, 85)
        head.resizeSection(6, 95)
        summary_layout.addWidget(self.tbl_selected)

        stats = QHBoxLayout()
        self.lbl_total_items = QLabel("0 Kalem")
        self.lbl_total_items.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text_muted;"))
        self.lbl_total = QLabel("0.00 USD")
        self.lbl_total.setStyleSheet(theme_qss("font-size: 24px; font-weight: 900; color: @success;"))
        stats.addWidget(self.lbl_total_items)
        stats.addStretch()
        stats.addWidget(self.lbl_total)
        summary_layout.addLayout(stats)

        button_row = QHBoxLayout()
        btn_remove = QPushButton("Seçileni Çıkar")
        btn_remove.setMinimumHeight(42)
        btn_remove.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="lg")))
        btn_remove.clicked.connect(self._remove_selected_item)
        btn_clear = QPushButton("Listeyi Temizle")
        btn_clear.setMinimumHeight(42)
        btn_clear.setStyleSheet(theme_qss(DesignTokens.get_button_qss("warning", size="lg")))
        btn_clear.clicked.connect(self._clear_items)
        button_row.addWidget(btn_remove)
        button_row.addWidget(btn_clear)
        summary_layout.addLayout(button_row)
        layout.addWidget(summary_card, 1)

        pdf_card, pdf_layout = self._panel(
            "Teklif Çıktısı",
            "Ak\u0131ll\u0131 ev teklifi, AYEC Pro proforma mant\u0131\u011f\u0131na benzer kurumsal PDF olarak olu\u015fturulur."
        )
        self.preview_hint = QLabel(
            "Akış: Müşteri ve proje bilgilerini girin, ürünleri havuzdan ekleyin ve doğrudan PDF proforma oluşturun."
        )
        self.preview_hint.setWordWrap(True)
        self.preview_hint.setStyleSheet(
            theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 16px; padding: 14px; font-size: 12px; font-weight: 600; color: @text;")
        )
        pdf_layout.addWidget(self.preview_hint)

        btn_generate = QPushButton("Akıllı Ev Proforma PDF Oluştur")
        btn_generate.setMinimumHeight(48)
        btn_generate.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="lg")))
        btn_generate.clicked.connect(self._create_offer_letter)
        pdf_layout.addWidget(btn_generate)
        layout.addWidget(pdf_card)
        return container

    def _peek_offer_no(self):
        prefix = str(self.db.get_setting("reference_number_prefix", "REF") or "REF").strip() or "REF"
        next_raw = str(self.db.get_setting("reference_number_next", "1") or "1").strip()
        next_number = int(next_raw) if next_raw.isdigit() else 1
        return f"{prefix}{next_number}"

    def _consume_offer_no(self):
        if hasattr(self.db, "get_next_reference_number"):
            return self.db.get_next_reference_number()
        return self._peek_offer_no()

    def _iter_customers(self):
        for row in self.db.get_customers() or []:
            yield dict(row) if not isinstance(row, dict) else row

    @staticmethod
    def _row_value(row, key, default=None):
        if row is None:
            return default
        if isinstance(row, dict):
            return row.get(key, default)
        try:
            return row[key]
        except Exception:
            return default

    def _load_customers(self):
        self.cmb_customer.blockSignals(True)
        self.cmb_customer.clear()
        for row in self._iter_customers():
            label = str(self._row_value(row, "name", "") or "")
            company_name = str(self._row_value(row, "company_name", "") or "").strip()
            if company_name and company_name.lower() != label.lower():
                label = f"{label} / {company_name}"
            self.cmb_customer.addItem(label, row)
        self.cmb_customer.setCurrentIndex(-1)
        self.cmb_customer.blockSignals(False)

    def _fill_customer_fields(self):
        row = self.cmb_customer.currentData()
        if not isinstance(row, dict):
            return
        customer_name = str(self._row_value(row, "name", "") or "").strip()
        company_name = str(self._row_value(row, "company_name", "") or "").strip() or customer_name
        self.inp_company.setText(company_name)
        self.inp_contact.setText(customer_name)
        self.inp_phone.setText(str(self._row_value(row, "phone", "") or "").strip())
        self.inp_email.setText(str(self._row_value(row, "email", "") or "").strip())
        if not self.inp_project.text().strip():
            self.inp_project.setText(company_name)
        self._update_offer_badge()

    def _is_smart_home_product(self, row):
        text = " ".join(str(self._row_value(row, key, "") or "") for key in ("name", "description", "category", "code", "barcode")).lower()
        return any(keyword in text for keyword in self.SMART_HOME_KEYWORDS)

    def _load_products(self):
        rows, _total = self.db.get_parts_paginated(limit=5000, offset=0, category="Tümü")
        all_products = []
        smart_products = []
        for row in rows or []:
            item = dict(row) if not isinstance(row, dict) else row
            all_products.append(item)
            if self._is_smart_home_product(item):
                smart_products.append(item)
        self.products = smart_products or all_products
        self._refresh_product_table("")

    def _refresh_product_table(self, query=""):
        self.filtered_products = []
        for row in self.products:
            text = " ".join(str(self._row_value(row, key, "") or "").lower() for key in ("name", "code", "category", "barcode", "description"))
            if query and query not in text:
                continue
            self.filtered_products.append(row)

    def _append_product_to_offer(self, row, qty, unit_price):
        currency = str(self._row_value(row, "currency", "USD") or "USD").upper()
        self.selected_items.append(
            {
                "part_id": self._row_value(row, "id"),
                "name": str(self._row_value(row, "name", "") or ""),
                "brand": str(self._row_value(row, "brand", "") or ""),
                "code": str(self._row_value(row, "code", "") or ""),
                "category": str(self._row_value(row, "category", "") or ""),
                "description": str(self._row_value(row, "description", self._row_value(row, "category", "")) or ""),
                "qty": qty,
                "unit_price": unit_price,
                "currency": currency,
            }
        )

    def _open_product_pool(self):
        if self.product_pool_dialog is None:
            self.product_pool_dialog = SmartHomeProductPoolDialog(self)
        self.product_pool_dialog.refresh_table()
        self.product_pool_dialog.exec()

    def _refresh_selected_table(self):
        self.tbl_selected.setRowCount(len(self.selected_items))
        currency_totals = {}
        for r, item in enumerate(self.selected_items):
            line_total = float(item["unit_price"]) * int(item["qty"])
            currency = str(item.get("currency") or "USD").upper()
            currency_totals[currency] = currency_totals.get(currency, 0.0) + line_total
            values = [
                item["name"],
                item["code"],
                item["category"],
                item["description"],
                str(item["qty"]),
                f"{item['unit_price']:.2f} {item['currency']}",
                f"{line_total:.2f} {item['currency']}",
            ]
            for c, value in enumerate(values):
                self.tbl_selected.setItem(r, c, QTableWidgetItem(value))
        self.lbl_total_items.setText(f"{len(self.selected_items)} Kalem")
        if not currency_totals:
            self.lbl_total.setText("0.00 USD")
        elif len(currency_totals) == 1:
            currency, total = next(iter(currency_totals.items()))
            self.lbl_total.setText(f"{total:.2f} {currency}")
        else:
            parts = [f"{total:.2f} {currency}" for currency, total in currency_totals.items()]
            self.lbl_total.setText(" | ".join(parts))
        self._update_offer_badge()

    def _remove_selected_item(self):
        row = self.tbl_selected.currentRow()
        if row < 0:
            show_warning(self, "Lütfen listeden bir kalem seçin.")
            return
        del self.selected_items[row]
        self._refresh_selected_table()

    def _clear_items(self):
        self.selected_items = []
        self._refresh_selected_table()

    def _offer_data(self):
        return {
            "offer_no": self.inp_offer_no.text().strip() or self._peek_offer_no(),
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "company_name": self.inp_company.text().strip(),
            "customer_name": self.inp_contact.text().strip(),
            "phone": self.inp_phone.text().strip(),
            "email": self.inp_email.text().strip(),
            "project_name": self.inp_project.text().strip(),
            "block_count": int(self.spn_block.value() or 1),
            "flat_count": int(self.spn_flat.value() or 1),
            "notes": self.txt_notes.toPlainText().strip(),
        }

    def _update_offer_badge(self):
        data = self._offer_data()
        self.lbl_offer_badge.setText(
            f"{data['offer_no']}\n{data['date']}  |  {len(self.selected_items)} kalem"
        )

    def _create_offer_letter(self):
        if not self.selected_items:
            show_warning(self, "PDF oluşturmadan önce en az bir ürün ekleyin.")
            return
        data = self._offer_data()
        if not data["company_name"]:
            show_warning(self, "Firma / kurum alanı boş bırakılamaz.")
            return
        if not data["project_name"]:
            show_warning(self, "Proje adı boş bırakılamaz.")
            return
        try:
            from src.ui.pages.transaction.dialogs.proforma_dialog import ProformaDialog
            from src.utils.exchange_rate_manager import ExchangeRateManager

            subtotal_try = 0.0
            proforma_items = []
            for item in self.selected_items:
                src_currency = str(item.get("currency") or "TRY").upper()
                unit_price = float(item.get("unit_price") or 0.0)
                rate = 1.0
                if src_currency != "TRY":
                    rate = ExchangeRateManager.get_current_rate(self.db, src_currency) or 1.0
                price_try = unit_price if src_currency == "TRY" else unit_price * rate
                qty = int(item.get("qty") or 1)
                subtotal_try += price_try * qty
                proforma_items.append(
                    {
                        "service": item.get("name") or "Akıllı Ev Ürünü",
                        "name": item.get("name") or "",
                        "code": item.get("code") or "",
                        "brand": item.get("brand") or "",
                        "model": item.get("name") or item.get("code") or "",
                        "description": item.get("description") or item.get("category") or "",
                        "qty": qty,
                        "price": price_try,
                    }
                )
            vat_rate = TaxSettings.get_ratio(self.db)
            vat_amount = subtotal_try * vat_rate
            total_try = subtotal_try + vat_amount
            preferred_currency = str(self.selected_items[0].get("currency") or "TRY").upper()
            currency_mode = "USD" if preferred_currency == "USD" else "EUR" if preferred_currency == "EUR" else "TL"
            dialog = ProformaDialog(
                self,
                self.db,
                proforma_items,
                (subtotal_try, 0.0, vat_rate, vat_amount, total_try),
                data["customer_name"] or data["company_name"],
                currency_mode=currency_mode,
                customer_id=self._row_value(self.cmb_customer.currentData(), "id"),
                customer_company=data["company_name"],
                initial_company=data["company_name"],
                initial_project=data["project_name"],
                preferred_template="bulut_deri",
                source="smart_home",
            )
            dialog.exec()
        except Exception as e:
            show_error(self, f"Teklif oluşturma hatası:\n{e}")

    def refresh_data(self):
        self._load_customers()
        self._load_products()
        self.inp_offer_no.setText(self._peek_offer_no())
        self._update_offer_badge()
