# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QDialog, 
                             QFormLayout, QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, 
                             QMessageBox, QTreeWidget, QTreeWidgetItem, QSplitter, QFrame, 
                             QSpinBox, QScrollArea, QToolButton, QAbstractItemView, QMenu, 
                             QGridLayout, QInputDialog, QProgressDialog, QApplication,
                             QCheckBox, QRadioButton, QTextEdit, QButtonGroup, QSizePolicy)
from PyQt6.QtCore import Qt, QDate, QEvent, QTimer
from PyQt6.QtGui import QColor, QFont, QAction, QPainter, QPixmap
import json
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error
from src.utils.language_manager import LanguageManager
from src.ui.dialogs.base_modern_dialog import BaseModernDialog


class AddUnitDialog(BaseModernDialog):
    """Akıllı ev projesi için basit blok/daire ekleme dialogu."""
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent, title="🏠 Blok ve Daire Oluştur", width=560, height=420)
        self.db = db
        self.project_id = project_id
        self.setup_unit_ui()

    def setup_unit_ui(self):
        content = self.content_layout
        content.setSpacing(14)

        header_lbl = QLabel("🏠 Blok / Daire Yapısı Oluştur")
        header_lbl.setStyleSheet(theme_qss("font-size: 15px; font-weight: 800; color: @text;"))
        content.addWidget(header_lbl)

        form = QFormLayout()
        form.setSpacing(12)

        spin_qss = theme_qss(
            DesignTokens.get_input_qss() + """
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
                background: @surface_alt;
                border-left: 1px solid @border;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: @border;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 10px;
                height: 10px;
            }
            """
        )

        # Blok sayısı
        self.spin_block_count = QSpinBox()
        self.spin_block_count.setRange(1, 26)
        self.spin_block_count.setValue(1)
        self.spin_block_count.setFixedHeight(36)
        self.spin_block_count.setStyleSheet(spin_qss)
        form.addRow("Blok Sayısı:", self.spin_block_count)

        # Her blokta kaç daire
        self.spin_unit_count = QSpinBox()
        self.spin_unit_count.setRange(1, 200)
        self.spin_unit_count.setValue(5)
        self.spin_unit_count.setFixedHeight(36)
        self.spin_unit_count.setStyleSheet(spin_qss)
        form.addRow("Her Blokta Daire Sayısı:", self.spin_unit_count)

        # Adlandırma
        self.cmb_naming = QComboBox()
        self.cmb_naming.addItems(["Harfli (A, B, C)", "Sayılı (1, 2, 3)", "Özel"])
        self.cmb_naming.setFixedHeight(36)
        self.cmb_naming.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        form.addRow("Blok Adlandırma:", self.cmb_naming)

        # Özel adlar
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("Örn: A Blok,B Blok,C Blok")
        self.txt_custom.setFixedHeight(36)
        self.txt_custom.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.txt_custom.setVisible(False)
        form.addRow("Özel Adlar (virgülle):", self.txt_custom)

        content.addLayout(form)

        # Önizleme
        self.lbl_preview = QLabel()
        self.lbl_preview.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        self.lbl_preview.setWordWrap(True)
        content.addWidget(self.lbl_preview)

        content.addStretch()

        # Butonlar
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("ghost")))
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("✅ Oluştur")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_save.clicked.connect(self.save)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        content.addLayout(btn_row)

        # Bağlantılar
        self.cmb_naming.currentIndexChanged.connect(self._on_naming_changed)
        self.spin_block_count.valueChanged.connect(self._update_preview)
        self.spin_unit_count.valueChanged.connect(self._update_preview)
        self.cmb_naming.currentIndexChanged.connect(self._update_preview)
        self.txt_custom.textChanged.connect(self._update_preview)
        self._update_preview()

    def _on_naming_changed(self):
        self.txt_custom.setVisible(self.cmb_naming.currentText() == "Özel")
        self._update_preview()

    def _get_block_names(self):
        count = self.spin_block_count.value()
        naming = self.cmb_naming.currentText()
        if naming.startswith("Harfli"):
            return [chr(ord('A') + i) for i in range(count)]
        elif naming.startswith("Sayılı"):
            return [str(i + 1) for i in range(count)]
        else:
            custom = [n.strip() for n in self.txt_custom.text().split(",") if n.strip()]
            while len(custom) < count:
                custom.append(f"Blok{len(custom) + 1}")
            return custom[:count]

    def _update_preview(self):
        names = self._get_block_names()
        unit_count = self.spin_unit_count.value()
        sample = [f"{n}: {unit_count} daire" for n in names[:4]]
        if len(names) > 4:
            sample.append(f"...+{len(names) - 4} blok")
        total = len(names) * unit_count
        self.lbl_preview.setText("Önizleme: " + ",  ".join(sample) + f"  →  Toplam {total} daire")

    def save(self):
        block_names = self._get_block_names()
        unit_count = self.spin_unit_count.value()
        created = 0
        for block in block_names:
            for i in range(unit_count):
                unit_no = f"{block}-{i + 1}"
                data = {
                    'project_id': self.project_id,
                    'block_name': block,
                    'floor_no': '0',
                    'unit_no': unit_no,
                    'status': 'Bekliyor',
                    'price': 0,
                    'unit_type': '',
                    'area': 0,
                    'unit_price': 0,
                    'total_price': 0,
                    'description': '',
                    'parent_unit_id': None,
                    'unit_kind': 'Daire',
                }
                self.db.add_project_unit(data)
                created += 1
        show_success(self.parent(), f"{created} daire oluşturuldu.")
        self.accept()

class AddSubDialog(BaseModernDialog):
    """Project team and subcontractor assignment dialog."""
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent, title="Ekip \u00dcyesi / Ta\u015feron Ekle", width=840, height=1044)
        self.db = db
        self.project_id = project_id
        self.setFont(QFont("Segoe UI", 10))
        self.btn_close.setText("\u00d7")
        self.btn_close.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.logo_label.clear()
        self.logo_label.setFixedSize(54, 54)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QPixmap(54, 54)
        icon.fill(Qt.GlobalColor.transparent)
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0ea5e9"))
        painter.drawEllipse(12, 13, 11, 11)
        painter.drawEllipse(29, 16, 9, 9)
        painter.drawRoundedRect(7, 27, 21, 13, 6, 6)
        painter.drawRoundedRect(24, 28, 19, 12, 5, 5)
        painter.end()
        self.logo_label.setPixmap(icon)
        self.logo_label.setStyleSheet("background: #071426; border: 1px solid #2563eb; border-radius: 14px;")
        header_layout = self.header.layout()
        header_layout.removeWidget(self.lbl_title)
        title_block = QWidget(self.header)
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 8, 0, 0)
        title_layout.setSpacing(6)
        self.lbl_title.setFont(QFont(DesignTokens.FONT_FAMILY, 18, QFont.Weight.Bold))
        self.lbl_title.setFixedHeight(30)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(self.lbl_title)
        subtitle = QLabel("Projeye uzman ta\u015feron, usta veya saha teknikeri atan\u0131n")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setFixedHeight(22)
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none;"))
        title_layout.addWidget(subtitle)
        title_block.setFixedHeight(68)
        brand = QLabel("AYEC PRO")
        brand.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        brand.setStyleSheet(theme_qss("background: #13233d; color: #60a5fa; border: 1px solid #28436a; border-radius: 5px; padding: 10px; font-size: 10px; font-weight: 700;"))
        brand.setFixedSize(82, 42)
        header_layout.insertWidget(2, title_block)
        header_layout.insertWidget(3, brand)
        header_layout.setContentsMargins(30, 0, 14, 0)
        self.header.setFixedHeight(116)
        self.footer.setFixedHeight(90)
        self.footer_layout.insertStretch(0, 1)
        self.setup_sub_ui()
        self._apply_part9_reference_style(subtitle, brand)

    def setup_sub_ui(self):
        outer_layout = self.content_layout
        body = QWidget()
        content = QVBoxLayout(body)
        outer_layout.addWidget(body)
        content.setContentsMargins(24, 22, 24, 22)
        content.setSpacing(24)

        def _lbl(text):
            l = QLabel(text)
            l.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            l.setStyleSheet(theme_qss("color: @text_muted; font-weight: bold; font-size: 11px;"))
            return l

        def _inp(placeholder=""):
            i = QLineEdit()
            i.setFont(QFont("Segoe UI", 11))
            i.setPlaceholderText(placeholder)
            i.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            i.setFixedHeight(52)
            return i

        def _field(label, widget):
            field = QWidget()
            field_layout = QVBoxLayout(field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(8)
            field_layout.addWidget(_lbl(label))
            field_layout.addWidget(widget)
            return field

        self.txt_name = _inp("\u00d6rn. Ahmet Y\u0131lmaz veya TechEv \u00c7\u00f6z\u00fcmleri")
        content.addWidget(_field("Ad Soyad / Firma Ad\u0131 *", self.txt_name))

        self.cmb_job = QComboBox()
        self.cmb_job.setFont(QFont("Segoe UI", 11))
        self.cmb_job.setEditable(False)
        self.cmb_job.addItems([
            "\u26a1 Elektrik Tesisat\u0131",
            "\U0001f3e0 Ak\u0131ll\u0131 Ev Otomasyonu (KNX & Zigbee)",
            "\U0001f310 A\u011f & Yap\u0131sal Kablolama",
            "\U0001f4f9 Kamera & G\u00fcvenlik Sistemleri",
            "\U0001f3a8 Boya & Al\u00e7\u0131pan / \u0130nce \u0130\u015f\u00e7ilik",
            "\u2744\ufe0f \u0130klimlendirme & Havaland\u0131rma",
        ])
        self.cmb_job.setStyleSheet(theme_qss(DesignTokens.get_input_qss() + " QComboBox { background: @surface; color: @text; } QComboBox QAbstractItemView { background: @surface; color: @text; selection-background-color: @primary; }"))
        self.cmb_job.setFixedHeight(52)
        content.addWidget(_field("Uzmanl\u0131k Alan\u0131 *", self.cmb_job))

        payment_card = QFrame()
        payment_card.setObjectName("SubcontractorPaymentCard")
        payment_card.setStyleSheet(theme_qss("QFrame#SubcontractorPaymentCard { background: @surface_alt; border: 1px solid @border; border-radius: 12px; }"))
        payment_layout = QVBoxLayout(payment_card)
        payment_layout.setContentsMargins(16, 20, 16, 20)
        payment_layout.setSpacing(16)
        payment_layout.addWidget(_lbl("\u00dccretlendirme Modeli & S\u00f6zle\u015fme Tutar\u0131"))
        payment_row = QHBoxLayout()
        payment_row.setContentsMargins(0, 0, 0, 0)
        payment_row.setSpacing(4)
        payment_row.setObjectName("SubcontractorPaymentOptions")
        self.payment_group = QButtonGroup(self)
        self.payment_group.setExclusive(True)
        self.payment_radios = {}
        for label, key in (("G\u00f6t\u00fcr\u00fc / Sabit Fiyat", "fixed"), ("G\u00fcnl\u00fck Yevmiye", "daily"), ("Daire Ba\u015f\u0131", "unit")):
            option = QPushButton(label)
            option.setCheckable(True)
            option.setFont(QFont("Segoe UI", 11))
            option.setMinimumHeight(40)
            option.setStyleSheet(theme_qss("QPushButton { background: @surface; color: @text_muted; border: 0; border-radius: 5px; padding: 8px 4px; font-size: 12px; } QPushButton:checked { background: @primary; color: @selection_text; font-weight: 700; }"))
            self.payment_group.addButton(option)
            self.payment_radios[key] = option
            payment_row.addWidget(option, 1)
        self.payment_radios["fixed"].setChecked(True)
        payment_row_widget = QWidget()
        payment_row_widget.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 8px;"))
        payment_row_widget.setLayout(payment_row)
        payment_layout.addWidget(payment_row_widget)
        amount_row = QHBoxLayout()
        amount_row.setSpacing(8)
        price_box = QFrame()
        price_box.setStyleSheet("QFrame { background: #060a14; border: 1px solid #334155; border-radius: 9px; }")
        price_layout = QHBoxLayout(price_box)
        price_layout.setContentsMargins(14, 0, 12, 0)
        price_layout.setSpacing(8)
        price_label = QLabel("S\u00f6zle\u015fme Bedeli:")
        price_label.setFont(QFont("Segoe UI", 11))
        price_label.setStyleSheet("color: #718096; font-size: 12px; border: none;")
        price_layout.addWidget(price_label)
        self.txt_total = _inp("0,00")
        self.txt_total.setText("0,00")
        self.txt_total.setFixedHeight(48)
        self.txt_total.setFont(QFont("Consolas", 14, QFont.Weight.DemiBold))
        self.txt_total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.txt_total.setStyleSheet("QLineEdit { background: transparent; color: #34d399; border: 0; font: 600 14px Consolas, monospace; padding: 8px 0; }")
        price_layout.addWidget(self.txt_total, 1)
        amount_row.addWidget(price_box, 1)
        self.cmb_currency = QComboBox()
        self.cmb_currency.addItem("\u20ba TL", "TRY")
        self.cmb_currency.addItem("$ USD", "USD")
        self.cmb_currency.addItem("\u20ac EUR", "EUR")
        self.cmb_currency.setFont(QFont("Segoe UI", 11))
        self.cmb_currency.setStyleSheet(theme_qss(DesignTokens.get_input_qss() + " QComboBox { background: @surface; color: @text; } QComboBox QAbstractItemView { background: @surface; color: @text; selection-background-color: @primary; }"))
        self.cmb_currency.setFixedSize(140, 50)
        amount_row.addWidget(self.cmb_currency)
        payment_layout.addLayout(amount_row)
        content.addWidget(payment_card)

        contact_layout = QHBoxLayout()
        phone_col = QVBoxLayout()
        phone_col.setSpacing(8)
        phone_col.addWidget(_lbl("Telefon Numaras\u0131"))
        self.txt_phone = _inp("05xx xxx xx xx")
        self.txt_phone.setFixedHeight(48)
        phone_col.addWidget(self.txt_phone)
        email_col = QVBoxLayout()
        email_col.setSpacing(8)
        email_col.addWidget(_lbl("E-posta Adresi"))
        self.txt_email = _inp("ornek@mail.com")
        self.txt_email.setFixedHeight(48)
        email_col.addWidget(self.txt_email)
        contact_layout.addLayout(phone_col)
        contact_layout.addLayout(email_col)
        content.addLayout(contact_layout)

        self.unit_checks = []
        self.unit_group_buttons = []
        unit_box = QFrame()
        unit_box.setObjectName("SubcontractorUnitSelection")
        unit_box.setStyleSheet(
            "QFrame#SubcontractorUnitSelection { background: #080d19; "
            "border: 1px solid #334155; border-radius: 10px; }"
        )
        units = self.db.get_project_units(self.project_id) or []
        unit_records = []
        for unit in units:
            unit_id = unit["id"] if isinstance(unit, dict) else unit[0]
            block = unit.get("block_name", "Blok") if isinstance(unit, dict) else unit[2]
            unit_no = unit.get("unit_no", unit_id) if isinstance(unit, dict) else unit[4]
            unit_records.append((unit_id, str(block), str(unit_no)))
        unit_groups = {}
        for index, (unit_id, block, unit_no) in enumerate(unit_records):
            unit_groups.setdefault(block, []).append((index, unit_id, unit_no))
            check = QCheckBox(f"{block} {unit_no}")
            check.setFont(QFont("Segoe UI", 10))
            check.setChecked(True)
            check.setProperty("unit_id", unit_id)
            check.setStyleSheet(theme_qss("color: @text; padding: 5px;"))
            self.unit_checks.append(check)
        unit_layout = QVBoxLayout(unit_box)
        unit_layout.setContentsMargins(12, 6, 12, 6)
        unit_layout.setSpacing(8)
        unit_groups_row = QHBoxLayout()
        unit_groups_row.setContentsMargins(0, 0, 0, 0)
        unit_groups_row.setSpacing(7)
        unit_groups_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.unit_all_button = QPushButton("T\u00fcm Proje \u00d7")
        self.unit_all_button.setFont(QFont("Segoe UI", 10))
        self.unit_all_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.unit_all_button.setFixedHeight(34)
        self.unit_all_button.setCheckable(True)
        self.unit_all_button.setChecked(bool(self.unit_checks))
        self.unit_all_button.setStyleSheet(self._unit_chip_style())
        self.unit_all_button.toggled.connect(self._set_all_units)
        unit_groups_row.addWidget(self.unit_all_button)
        def add_unit_group_chip(group_key, label):
            button = QPushButton(label)
            button.setFont(QFont("Segoe UI", 10))
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button.setFixedHeight(34)
            button.setCheckable(True)
            button.setChecked(False)
            button.setProperty("unit_block", group_key)
            button.setStyleSheet(self._unit_chip_style())
            button.toggled.connect(lambda checked, key=group_key: self._set_group_units(key, checked))
            self.unit_group_buttons.append(button)
            unit_groups_row.addWidget(button)

        for block in unit_groups:
            add_unit_group_chip(block, block)
        for block, entries in unit_groups.items():
            if len(entries) > 1:
                suffix = block.split()[-1]
                numbers = [str(item[2]).removeprefix(suffix + "-").removeprefix(suffix + " ") for item in entries]
                numbers.sort(key=lambda value: (0, int(value)) if value.isdigit() else (1, value))
                add_unit_group_chip(block, f"Daire {suffix}-{numbers[0]} - {suffix}-{numbers[-1]}")
        self.btn_toggle_units = QPushButton("+ Ekle")
        self.btn_toggle_units.setFont(QFont("Segoe UI", 10))
        self.btn_toggle_units.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_toggle_units.setFixedHeight(34)
        self.btn_toggle_units.setStyleSheet("QPushButton { background: transparent; color: #aab6c8; border: 1px dashed #526783; border-radius: 6px; padding: 6px 10px; }")
        unit_groups_row.addWidget(self.btn_toggle_units)
        unit_layout.addLayout(unit_groups_row)
        self.unit_list_widget = QWidget()
        unit_list_layout = QHBoxLayout(self.unit_list_widget)
        unit_list_layout.setContentsMargins(0, 6, 0, 0)
        unit_list_layout.setSpacing(8)
        for check in self.unit_checks:
            unit_list_layout.addWidget(check)
            check.stateChanged.connect(self._sync_unit_groups)
        unit_list_layout.addStretch(1)
        self.unit_list_widget.hide()
        unit_layout.addWidget(self.unit_list_widget)
        self.btn_toggle_units.clicked.connect(self._toggle_unit_list)
        self._sync_unit_groups()
        unit_scroll = QScrollArea()
        unit_scroll.setWidgetResizable(True)
        unit_scroll.setFixedHeight(60)
        unit_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        unit_scroll.setWidget(unit_box)
        unit_field = QWidget()
        unit_field_layout = QVBoxLayout(unit_field)
        unit_field_layout.setContentsMargins(0, 0, 0, 0)
        unit_field_layout.setSpacing(8)
        unit_field_layout.addWidget(_lbl("Sorumlu Olaca\u011f\u0131 Blok / Daireler"))
        unit_field_layout.addWidget(unit_scroll)
        content.addWidget(unit_field)

        self.txt_notes = QTextEdit()
        self.txt_notes.setFont(QFont("Segoe UI", 11))
        self.txt_notes.setPlaceholderText("Ta\u015feronun i\u015f kapsam\u0131, malzeme sorumluluklar\u0131 ve i\u015f teslim tarihleri ile ilgili notlar...")
        self.txt_notes.setFixedHeight(108)
        self.txt_notes.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        content.addWidget(_field("G\u00f6rev A\u00e7\u0131klamas\u0131 & Notlar", self.txt_notes))

        self.add_button("\u0130ptal", "secondary", self.reject)
        self.add_button("\u2713  Ekip \u00dcyesini Kaydet && G\u00f6revlendir", "success", self.save)

        cancel_button = self.footer_layout.itemAt(1).widget()
        save_button = self.footer_layout.itemAt(2).widget()
        if cancel_button:
            cancel_button.setFixedHeight(44)
        if save_button:
            save_button.setFixedHeight(48)
            save_button.setMinimumWidth(330)

    def _apply_part9_reference_style(self, subtitle, brand):
        def style(widget, qss):
            widget.setProperty("skipThemeTransform", True)
            widget.setStyleSheet(qss)

        style(self, "QDialog { background: rgba(0, 0, 0, 220); }")
        style(self.card, "QFrame#ModernDialogCard { background: #0f172a; color: #e2e8f0; border: 1px solid #1e4b83; border-radius: 20px; }")
        style(self.header, "background: #101a31; border-bottom: 1px solid #1e293b; border-top-left-radius: 20px; border-top-right-radius: 20px;")
        style(self.content_container, "QFrame#ModernDialogContent { background: #0f172a; color: #e2e8f0; border: none; }")
        style(self.footer, "background: #0b1222; border-top: 1px solid #1e293b; border-bottom-left-radius: 20px; border-bottom-right-radius: 20px;")
        style(self.scroll_area, "QScrollArea { background: #0f172a; border: none; } QScrollArea::viewport { background: #0f172a; border: none; }")
        style(self.scroll_area.viewport(), "background: #0f172a; border: none;")
        if self.scroll_area.widget():
            style(self.scroll_area.widget(), "background: #0f172a; color: #e2e8f0;")
        for label in self.card.findChildren(QLabel):
            style(label, "color: #cbd5e1; background: transparent; border: none; font-family: 'Segoe UI', Arial;")
        style(self.lbl_title, "color: #f8fafc; background: transparent; border: none; font-weight: 700; font-family: 'Segoe UI', Arial;")
        style(subtitle, "color: #94a3b8; background: transparent; border: none; font-size: 12px; font-family: 'Segoe UI', Arial;")
        style(brand, "background: #13233d; color: #60a5fa; border: 1px solid #28436a; border-radius: 5px; padding: 10px; font-size: 10px; font-weight: 700; font-family: 'Segoe UI', Arial;")
        style(self.btn_close, "QPushButton { background: #172235; color: #94a3b8; border: 1px solid #26364d; border-radius: 9px; font-family: 'Segoe UI', Arial; } QPushButton:hover { background: #26364d; }")
        input_style = "QLineEdit, QTextEdit, QComboBox { background: #070c18; color: #e2e8f0; border: 1px solid #334155; border-radius: 9px; padding: 8px 12px; selection-background-color: #2563eb; } QComboBox QAbstractItemView { background: #0b1222; color: #e2e8f0; selection-background-color: #2563eb; }"
        for widget_type in (QLineEdit, QTextEdit, QComboBox):
            for control in self.card.findChildren(widget_type):
                style(control, input_style + " font-family: 'Segoe UI', Arial;")
        for button in self.payment_radios.values():
            style(button, "QPushButton { background: #070c18; color: #94a3b8; border: 0; border-radius: 5px; padding: 8px 4px; font-size: 12px; font-family: 'Segoe UI', Arial; } QPushButton:checked { background: #2563eb; color: #ffffff; font-weight: 700; }")
        for button in [self.unit_all_button, *self.unit_group_buttons]:
            style(button, "QPushButton { background: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 7px; padding: 7px 12px; font-family: 'Segoe UI', Arial; } QPushButton:checked { background: #2563eb; color: #ffffff; border-color: #2563eb; }")
        style(self.btn_toggle_units, "QPushButton { background: transparent; color: #94a3b8; border: 1px dashed #526783; border-radius: 6px; padding: 6px 10px; font-family: 'Segoe UI', Arial; }")
        for button in self.footer.findChildren(QPushButton):
            primary = "Kaydet" in button.text()
            colors = ("#34d399", "#022c22", "#34d399") if primary else ("#172235", "#e2e8f0", "#334155")
            style(button, "QPushButton { background: %s; color: %s; border: 1px solid %s; border-radius: 9px; font-weight: 700; padding: 8px 16px; font-family: 'Segoe UI', Arial; }" % colors)

    @staticmethod
    def _unit_chip_style():
        return theme_qss("QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 6px; padding: 7px 16px; font-size: 12px; } QPushButton:checked { background: @primary; color: @selection_text; border-color: @primary; }")

    def _set_all_units(self, checked):
        for item in self.unit_checks:
            item.setChecked(checked)
        self._sync_unit_groups()

    def _set_group_units(self, block, checked):
        if checked and self.unit_all_button.isChecked():
            for item in self.unit_checks:
                item.setChecked(False)
        for item in self.unit_checks:
            if str(item.text()).startswith(block + " "):
                item.setChecked(checked)
        self._sync_unit_groups()

    def _sync_unit_groups(self, *_args):
        all_checked = bool(self.unit_checks) and all(item.isChecked() for item in self.unit_checks)
        if self.unit_all_button.isChecked() != all_checked:
            self.unit_all_button.blockSignals(True)
            self.unit_all_button.setChecked(all_checked)
            self.unit_all_button.blockSignals(False)
        for button in self.unit_group_buttons:
            block = str(button.property("unit_block"))
            members = [item for item in self.unit_checks if str(item.text()).startswith(block + " ")]
            checked = not all_checked and bool(members) and all(item.isChecked() for item in members)
            if button.isChecked() != checked:
                button.blockSignals(True)
                button.setChecked(checked)
                button.blockSignals(False)

    def _toggle_unit_list(self):
        visible = not self.unit_list_widget.isVisible()
        self.unit_list_widget.setVisible(visible)
        self.btn_toggle_units.setText("Gizle" if visible else "+ Ekle")

    def save(self):
        if not self.txt_name.text().strip():
            from src.utils.toast_notification import show_error
            show_error(self.parent(), "Ad / Firma alan\u0131 zorunludur.")
            return
        payment_model = next((key for key, radio in self.payment_radios.items() if radio.isChecked()), "fixed")
        amount = self._amount(self.txt_total.text())
        data = {
            'project_id': self.project_id,
            'name': self.txt_name.text().strip(),
            'job_type': self.cmb_job.currentText().strip(),
            'total_contract_amount': amount,
            'payment_model': payment_model,
            'currency': self.cmb_currency.currentData() or self.cmb_currency.currentText(),
            'phone': self.txt_phone.text().strip(),
            'email': self.txt_email.text().strip(),
            'contact_info': " | ".join(value for value in (self.txt_phone.text().strip(), self.txt_email.text().strip()) if value),
            'assigned_units': json.dumps([check.property("unit_id") for check in self.unit_checks if check.isChecked()]),
            'notes': self.txt_notes.toPlainText().strip(),
            'daily_wage': amount if payment_model == "daily" else 0.0,
            'unit_rate': amount if payment_model == "unit" else 0.0,
        }
        self.db.add_subcontractor(data)
        self.accept()

    @staticmethod
    def _amount(value):
        try:
            return float(value.strip().replace(" ", "").replace(",", "."))
        except (AttributeError, ValueError):
            return 0.0

    def _wire_ui_signals(self):
        self.cmb_job.currentIndexChanged.connect(self._update_preview)
