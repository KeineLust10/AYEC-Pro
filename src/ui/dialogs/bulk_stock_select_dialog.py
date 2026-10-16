# -*- coding: utf-8 -*-

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QComboBox,
    QCheckBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_warning


class _QuantityStepper(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BulkQuantityStepper")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(112, 32)
        self.setStyleSheet(theme_qss(
            "QWidget#BulkQuantityStepper { background: @window; border: 1px solid @border; border-radius: 8px; }"
        ))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 2, 3, 2)
        layout.setSpacing(2)
        self.minus = QPushButton("-")
        self.plus = QPushButton("+")
        self.spin = QSpinBox()
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin.setStyleSheet(theme_qss(
            "QSpinBox { background: transparent; color: @text; border: none; padding: 0; }"
        ))
        button_qss = theme_qss(
            "QPushButton { background: transparent; color: @text_muted; border: none; "
            "border-radius: 5px; min-width: 24px; max-width: 24px; min-height: 24px; } "
            "QPushButton:hover { background: @surface_alt; color: @text; }"
        )
        for button in (self.minus, self.plus):
            button.setStyleSheet(button_qss)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(button)
        layout.insertWidget(1, self.spin, 1)
        self.minus.clicked.connect(lambda: self.spin.setValue(self.spin.value() - 1))
        self.plus.clicked.connect(lambda: self.spin.setValue(self.spin.value() + 1))

    @property
    def valueChanged(self):
        return self.spin.valueChanged

    def setRange(self, minimum, maximum):
        self.spin.setRange(minimum, maximum)

    def setValue(self, value):
        self.spin.setValue(value)

    def value(self):
        return self.spin.value()

    def minimum(self):
        return self.spin.minimum()

    def maximum(self):
        return self.spin.maximum()


class BulkStockSelectDialog(BaseModernDialog):
    SYSTEM_FILTERS = [
        ("Tümü", "all"),
        ("Bilgisayar Bile\u015fenleri", "computer"),
        ("Güvenlik Sistemleri", "security"),
        ("Akıllı Ev Sistemleri", "smart_home"),
    ]

    def __init__(self, parent, db, services_data=None, parts_data=None):
        self.db = db
        self.services_data = services_data or {}
        self.parts_data = parts_data or {}
        self.current_mode = "part"
        self.current_system = "all"
        super().__init__(parent=parent, title="Toplu \u00dcr\u00fcn & Hizmet Se\u00e7im Havuzu", width=864, height=840)
        self.logo_label.setPixmap(QPixmap())
        self.logo_label.setFixedSize(30, 30)
        mark = QPixmap(30, 30)
        mark.fill(Qt.GlobalColor.transparent)
        painter = QPainter(mark)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#22d3ee"), 1.4))
        for x, y in ((9, 9), (16, 9), (9, 16), (16, 16)):
            painter.drawRoundedRect(x, y, 4, 4, 1, 1)
        painter.end()
        self.logo_label.setPixmap(mark)
        self.logo_label.setStyleSheet(theme_qss(
            "QLabel { color: @accent; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 8px; font-size: 16px; font-weight: 700; }"
        ))
        self.lbl_title.setStyleSheet(theme_qss(
            "color: @text; background: transparent; border: none; font-size: 14px; font-weight: 700;"
        ))
        self.btn_close.setText("\u00d7")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; border: 1px solid @border; color: @text_muted; "
            "font-size: 16px; font-weight: 500; border-radius: 6px; padding: 0px; } "
            "QPushButton:hover { border-color: @danger; color: @danger; }"
        ))
        self.content_container.setStyleSheet(
            theme_qss(
                """
                QWidget {
                    background: @surface;
                    color: @text;
                }
                QLineEdit {
                    background: @surface_alt;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 10px;
                    padding: 8px 10px;
                }
                QTreeWidget {
                    background: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 12px;
                }
                QHeaderView::section {
                    background: @surface_alt;
                    color: @text;
                    border: none;
                    padding: 5px;
                    font-weight: 800;
                }
                """
            )
        )
        self.system_buttons = []
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(0, 16, 18, 18)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        intro_row = QHBoxLayout()
        intro_row.setSpacing(8)
        intro = QLabel("Hizmet veya stok \u00fcr\u00fcnlerini filtreleyin, adet belirleyin ve tek t\u0131kla sepete ekleyin.")
        intro.setFixedHeight(22)
        intro.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; background: transparent; border: none;"))
        version = QLabel("v2.4 Enterprise")
        version.setStyleSheet(theme_qss(
            "QLabel { color: @accent; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 8px; padding: 2px 6px; font-size: 9px; font-weight: 700; }"
        ))
        version.setFixedSize(92, 22)
        header_layout = self.header.layout()
        header_layout.setSpacing(0)
        header_layout.removeWidget(self.lbl_title)
        title_stack = QWidget(self.header)
        title_stack_layout = QVBoxLayout(title_stack)
        title_stack_layout.setContentsMargins(0, 0, 0, 0)
        title_stack_layout.setSpacing(1)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title_row.addWidget(self.lbl_title)
        title_row.addWidget(version)
        title_stack_layout.addLayout(title_row)
        title_stack_layout.addWidget(intro)
        header_layout.insertWidget(2, title_stack)

        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(18, 0, 0, 0)
        mode_row.setSpacing(10)
        self.btn_services = QPushButton("Hizmetler (Servis & \u0130\u015f\u00e7ilik)")
        self.btn_parts = QPushButton("Stok & Par\u00e7a (Envanter)")
        for btn in (self.btn_services, self.btn_parts):
            btn.setCheckable(True)
            btn.setMinimumHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.btn_services)
        self.mode_group.addButton(self.btn_parts)
        self.btn_parts.setChecked(True)
        self.btn_services.clicked.connect(lambda: self._switch_mode("service"))
        self.btn_parts.clicked.connect(lambda: self._switch_mode("part"))
        mode_row.addWidget(self.btn_services)
        mode_row.addWidget(self.btn_parts)
        mode_row.addStretch()
        self.inventory_badge = QLabel("\u25cf Canl\u0131 Envanter Aktif")
        self.inventory_badge.setFixedHeight(30)
        self.inventory_badge.setStyleSheet(theme_qss(
            "QLabel { background: @surface_alt; color: @success; border: 1px solid @border; "
            "border-radius: 6px; padding: 5px 9px; font-size: 10px; font-weight: 700; }"
        ))
        self.depot_badge = QLabel("Depo: Merkez Depo (A Blok)")
        self.depot_badge.setFixedHeight(30)
        self.depot_badge.setStyleSheet(theme_qss(
            "QLabel { background: @surface_alt; color: @text_muted; border: 1px solid @border; "
            "border-radius: 6px; padding: 5px 9px; font-size: 10px; font-weight: 600; }"
        ))
        mode_row.addWidget(self.inventory_badge)
        mode_row.addWidget(self.depot_badge)
        layout.addLayout(mode_row)
        self._refresh_mode_styles()

        system_row = QHBoxLayout()
        system_row.setContentsMargins(18, 0, 0, 0)
        system_row.setSpacing(8)
        self.system_group = QButtonGroup(self)
        self.system_group.setExclusive(True)
        for text, value in self.SYSTEM_FILTERS:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if value == "all":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, v=value: self._switch_system(v))
            self.system_group.addButton(btn)
            self.system_buttons.append((btn, value))
            system_row.addWidget(btn)
        system_row.addStretch()
        layout.addLayout(system_row)
        self._refresh_system_styles()

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(18, 0, 0, 0)
        filter_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("\u00dcr\u00fcn ad\u0131, barkod veya stok kodu ile ara... (Ctrl + F)")
        self.search_input.setFixedHeight(32)
        self.search_input.setTextMargins(18, 0, 38, 0)
        search_icon = QPixmap(16, 16)
        search_icon.fill(Qt.GlobalColor.transparent)
        icon_painter = QPainter(search_icon)
        icon_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon_painter.setPen(QPen(QColor("#94a3b8"), 1.4))
        icon_painter.drawEllipse(2, 2, 8, 8)
        icon_painter.drawLine(9, 9, 14, 14)
        icon_painter.end()
        self.search_icon = QLabel(self.search_input)
        self.search_icon.setFixedSize(16, 16)
        self.search_icon.setPixmap(search_icon)
        self.find_badge = QLabel("Ctrl+F", self.search_input)
        self.find_badge.setFixedSize(28, 18)
        self.find_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.find_badge.setStyleSheet(theme_qss(
            "QLabel { color: @text_muted; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 3px; font-size: 8px; }"
        ))
        self.search_input.textChanged.connect(self._filter_rows)
        self.find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.find_shortcut.activated.connect(self.search_input.setFocus)
        self.accept_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        self.accept_shortcut.activated.connect(self._handle_accept)
        filter_row.addWidget(self.search_input, 4)
        self.status_filter = QComboBox()
        self.status_filter.addItem("Durum: Yaln\u0131zca Stokta Olanlar", "available")
        self.status_filter.addItem("Durum: T\u00fcm\u00fcn\u00fc G\u00f6ster (Kritik Dahil)", "all")
        self.status_filter.addItem("Durum: Yaln\u0131zca Kritik Stok (<10)", "critical")
        self.status_filter.currentIndexChanged.connect(self._filter_rows)
        self.status_filter.setMinimumWidth(0)
        self.status_filter.setMaximumWidth(200)
        filter_row.addWidget(self.status_filter, 2)
        self.sort_filter = QComboBox()
        self.sort_filter.addItem("S\u0131ralama: Fiyata G\u00f6re Artan", "price_asc")
        self.sort_filter.addItem("S\u0131ralama: Fiyata G\u00f6re Azalan", "price_desc")
        self.sort_filter.addItem("S\u0131ralama: En \u00c7ok Satanlar", "best_selling")
        self.sort_filter.addItem("S\u0131ralama: Stok Miktar\u0131na G\u00f6re", "stock")
        self.sort_filter.currentIndexChanged.connect(self._populate)
        self.sort_filter.setMinimumWidth(0)
        self.sort_filter.setMaximumWidth(200)
        filter_row.addWidget(self.sort_filter, 2)
        for combo in (self.status_filter, self.sort_filter):
            combo.setMinimumHeight(32)
            combo.setStyleSheet(theme_qss(
                'QComboBox { background: @surface_alt; color: @text; '
                'border: 1px solid @border; border-radius: 8px; padding: 0 5px; font-size: 9px; } '
                'QComboBox QAbstractItemView { background: @surface; color: @text; '
                'selection-background-color: @selection_bg; }'
            ))
        layout.addLayout(filter_row)
        layout.addSpacing(7)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(7)
        self.tree.setHeaderLabels(["", "KALEM / \u00dcR\u00dcN TANIMI & KOD", "KATEGOR\u0130", "STOK DURUMU", "B\u0130R\u0130M F\u0130YAT", "ADET BEL\u0130RLE", "SE\u00c7\u0130M"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(False)
        self.tree.setUniformRowHeights(False)
        self.tree.setMinimumHeight(280)
        self.tree.setMaximumHeight(420)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.tree.header().setFixedHeight(35)
        for section, width in enumerate((34, 300, 120, 122, 90, 98, 50)):
            self.tree.header().resizeSection(section, width)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setStretchLastSection(False)
        self.select_visible = QCheckBox(self.tree.header())
        self.select_visible.setTristate(True)
        self.select_visible.setFixedSize(18, 18)
        self.select_visible.setStyleSheet(theme_qss(
            'QCheckBox { spacing: 0; } QCheckBox::indicator { width: 15px; height: 15px; '
            'background: @surface_alt; border: 1px solid @border; border-radius: 4px; } '
            'QCheckBox::indicator:checked, QCheckBox::indicator:indeterminate { '
            'background: @accent; border-color: @accent; }'
        ))
        self.select_visible.stateChanged.connect(self._toggle_visible_rows)
        self.tree.header().installEventFilter(self)
        self._position_header_checkbox()
        layout.addWidget(self.tree, 1)

        self.lbl_selected = QLabel("0 kalem seçildi")
        self.lbl_selected.setStyleSheet(theme_qss("font-size: 12px; font-weight: 700; color: @text_muted;"))
        self.lbl_subtotal = QLabel("Ara Toplam: 0.00 \u20ba")
        self.lbl_subtotal.setStyleSheet(theme_qss("font-size: 13px; font-weight: 800; color: @accent;"))
        self.footer_layout.addWidget(self.lbl_selected)
        self.footer_layout.addWidget(self.lbl_subtotal, 1)
        self.add_button("Vazge\u00e7", variant="secondary", callback=self.reject)
        self.add_button("Se\u00e7ilenleri Ekle", variant="primary", callback=self._handle_accept)

    def _refresh_mode_styles(self):
        active_qss = theme_qss(
            """
            QPushButton {
                background: @accent;
                color: @selection_text;
                border: none;
                border-radius: 12px;
                padding: 0 10px;
                font-size: 10px;
                font-weight: 800;
            }
            """
        )
        passive_qss = theme_qss(
            """
            QPushButton {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 0 10px;
                font-size: 10px;
                font-weight: 800;
            }
            QPushButton:hover {
                border-color: @accent;
            }
            """
        )
        self.btn_services.setStyleSheet(active_qss if self.current_mode == "service" else passive_qss)
        self.btn_parts.setStyleSheet(active_qss if self.current_mode == "part" else passive_qss)

    def _refresh_system_styles(self):
        active_qss = theme_qss(
            """
            QPushButton {
                background: @accent;
                color: @text;
                border: 1px solid @accent;
                border-radius: 12px;
                padding: 0 8px;
                font-size: 9px;
                font-weight: 800;
            }
            """
        )
        passive_qss = theme_qss(
            """
            QPushButton {
                background: @surface_alt;
                color: @text_muted;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 0 8px;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton:hover {
                border-color: @accent;
                color: @text;
            }
            """
        )
        source = self.parts_data
        counts = {"all": len(source), "computer": 0, "security": 0, "smart_home": 0}
        for info in source.values():
            counts[self._detect_system_group(info, "part")] += 1
        for btn, value in self.system_buttons:
            label = next((text for text, key in self.SYSTEM_FILTERS if key == value), value)
            btn.setText(f"{label} ({counts.get(value, 0)})")
            btn.setStyleSheet(active_qss if self.current_system == value else passive_qss)

    def _switch_mode(self, mode):
        self.current_mode = mode
        self.search_input.clear()
        self._refresh_mode_styles()
        self._populate()

    def _switch_system(self, system_key):
        self.current_system = system_key
        self._refresh_system_styles()
        self._filter_rows()

    def _detect_system_group(self, info, item_type):
        category = str(info.get("category") or "").lower()
        text = " ".join(
            str(info.get(key) or "")
            for key in ("name", "description", "category")
        ).lower()

        security_keywords = [
            "kamera", "alarm", "sensör", "sensor", "geçiş", "guvenlik", "güvenlik",
            "yangın", "interkom", "nvr", "dvr", "kayıt", "siren", "dedektör", "dedektor",
            "ups", "güç", "guc", "pir", "ip kamera",
        ]
        smart_home_keywords = [
            "akıllı", "akilli", "smart", "hub", "priz", "röle", "role", "zil",
            "aydınlatma", "aydinlatma", "ev şarj", "ev sarj", "şarj", "sarj",
            "ses asistan", "klima kontrol", "enerji yönet", "kilit", "homepod", "echo",
        ]
        computer_keywords = [
            "anakart", "işlemci", "islemci", "ram", "ssd", "hdd", "ekran kartı", "gpu",
            "psu", "güç kaynağı", "guc kaynagi", "kasa", "monitör", "monitor", "klavye",
            "mouse", "yazılım", "yazilim", "cpu", "thermal", "kablo", "printer", "modem",
            "sunucu", "pc", "bilgisayar",
        ]

        if category:
            if any(keyword in category for keyword in security_keywords):
                return "security"
            if any(keyword in category for keyword in smart_home_keywords):
                return "smart_home"
            if any(keyword in category for keyword in computer_keywords):
                return "computer"

        if any(keyword in text for keyword in security_keywords):
            return "security"
        if any(keyword in text for keyword in smart_home_keywords):
            return "smart_home"
        if any(keyword in text for keyword in computer_keywords):
            return "computer"

        return "computer"

    def _row_is_selected(self, item):
        return bool(item.data(0, Qt.ItemDataRole.UserRole))

    def _set_row_selected(self, item, selected):
        item.setData(0, Qt.ItemDataRole.UserRole, bool(selected))
        checkbox_cell = self.tree.itemWidget(item, 0)
        row_checkbox = checkbox_cell.findChild(QPushButton) if checkbox_cell else None
        if row_checkbox is not None and row_checkbox.isChecked() != bool(selected):
            row_checkbox.blockSignals(True)
            row_checkbox.setChecked(bool(selected))
            row_checkbox.blockSignals(False)

    def _populate(self):
        selected_state = {}
        if hasattr(self, "tree"):
            for index in range(self.tree.topLevelItemCount()):
                old_item = self.tree.topLevelItem(index)
                old_info = old_item.data(1, Qt.ItemDataRole.UserRole) or {}
                old_id = str(old_info.get("id") or old_info.get("name") or "")
                old_qty = self.tree.itemWidget(old_item, 5)
                selected_state[old_id] = (
                    self._row_is_selected(old_item),
                    old_qty.value() if old_qty else 1,
                )
        self.tree.clear()
        source = self.services_data if self.current_mode == "service" else self.parts_data
        entries = list(source.items())
        sort_mode = self.sort_filter.currentData() if hasattr(self, "sort_filter") else "price_asc"
        def sort_key(entry):
            info = entry[1]
            price = float(info.get("original_price") or info.get("price") or 0)
            stock = int(info.get("stock") or 0)
            if sort_mode == "price_desc":
                return (-price, (info.get("name") or "").lower())
            if sort_mode == "stock":
                return (-stock, (info.get("name") or "").lower())
            if sort_mode == "best_selling":
                return (-float(info.get("sold_count") or info.get("sales_count") or 0), (info.get("name") or "").lower())
            return (price, (info.get("name") or "").lower())
        entries.sort(key=sort_key)
        for _, info in entries:
            item = QTreeWidgetItem(self.tree)
            item.setData(0, Qt.ItemDataRole.UserRole, False)
            name = str(info.get("name") or "")
            item.setText(1, name)
            item.setData(1, Qt.ItemDataRole.UserRole, dict(info))
            item.setData(1, Qt.ItemDataRole.UserRole + 1, self.current_mode)
            item.setData(1, Qt.ItemDataRole.UserRole + 2, self._detect_system_group(info, self.current_mode))
            for column in range(self.tree.columnCount()):
                item.setSizeHint(column, QSize(0, 48))
            row_checkbox = QPushButton("\u2713")
            row_checkbox.setCheckable(True)
            row_checkbox.setFixedSize(16, 16)
            row_checkbox.setStyleSheet(theme_qss(
                'QPushButton { color: transparent; background: @surface_alt; border: 1px solid @border; '
                'border-radius: 4px; padding: 0; font-size: 10px; font-weight: 800; } '
                'QPushButton:checked { color: @selection_text; background: @accent; border-color: @accent; }'
            ))
            checkbox_cell = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_cell)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.addWidget(row_checkbox, 0, Qt.AlignmentFlag.AlignCenter)
            self.tree.setItemWidget(item, 0, checkbox_cell)

            title_cell = QWidget()
            title_cell.setMinimumHeight(48)
            title_layout = QHBoxLayout(title_cell)
            title_layout.setContentsMargins(2, 3, 2, 3)
            title_layout.setSpacing(10)
            icon_label = QLabel("\u26a1")
            icon_label.setFixedSize(26, 28)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet(theme_qss(
                "QLabel { background: @surface_alt; color: @accent; border: 1px solid @border; "
                "border-radius: 6px; font-size: 13px; }"
            ))
            title_stack = QWidget()
            title_stack_layout = QVBoxLayout(title_stack)
            title_stack_layout.setContentsMargins(0, 0, 0, 0)
            title_stack_layout.setSpacing(2)
            title_label = QLabel(name)
            title_label.setStyleSheet(theme_qss("background: transparent; border: none; color: @text; font-weight: 600;"))
            sku = str(info.get("code") or info.get("sku") or "-")
            barcode = str(info.get("barcode") or "-")
            code_label = QLabel(f"SKU: {sku} \u2022 Barkod: {barcode}")
            code_label.setStyleSheet(theme_qss('background: transparent; border: none; color: @text_muted; font: 9px "JetBrains Mono";'))
            title_stack_layout.addWidget(title_label)
            title_stack_layout.addWidget(code_label)
            title_layout.addWidget(icon_label)
            title_layout.addWidget(title_stack, 1)
            self.tree.setItemWidget(item, 1, title_cell)

            category = str(info.get("category") or ("Hizmet" if self.current_mode == "service" else "Genel"))
            item.setText(2, category)
            category_label = QLabel(category)
            category_label.setFixedHeight(23)
            category_label.setStyleSheet(theme_qss(
                "QLabel { background: @surface_alt; color: @text_muted; border: 1px solid @border; "
                "border-radius: 5px; padding: 3px 6px; font-size: 9px; }"
            ))
            category_label.setToolTip(category)
            category_cell = QWidget()
            category_layout = QHBoxLayout(category_cell)
            category_layout.setContentsMargins(0, 0, 0, 0)
            category_layout.addWidget(category_label, 0, Qt.AlignmentFlag.AlignCenter)
            self.tree.setItemWidget(item, 2, category_cell)

            if self.current_mode == "service":
                item.setText(3, "Hizmet")
                price_try = float(info.get("price") or 0.0)
                primary_price = CurrencyHelper.format_amount(price_try, db=self.db, currency_code="TRY")
                reference_price = ""
                qty_spin = _QuantityStepper()
                qty_spin.setRange(1, 9999)
                qty_spin.setValue(1)
            else:
                stock = int(info.get("stock") or 0)
                currency = str(info.get("currency") or "TRY").upper()
                original_price = float(info.get("original_price") or info.get("price") or 0.0)
                status = "Stok Yok" if stock <= 0 else (f"Kritik: {stock}" if stock < 10 else f"Stok: {stock} Adet")
                item.setText(3, status)
                status_label = QLabel(("\u25cf " if stock >= 10 else "! ") + status)
                status_label.setStyleSheet(theme_qss(
                    "QLabel { background: @success_bg; color: @success; border: 1px solid @success; "
                    "border-radius: 10px; padding: 3px 7px; font-size: 9px; font-weight: 700; }"
                    if stock >= 10 else
                    "QLabel { background: @warning_bg; color: @warning; border: 1px solid @warning; "
                    "border-radius: 10px; padding: 3px 7px; font-size: 9px; font-weight: 700; }"
                ))
                status_label.setFixedHeight(23)
                status_label.setToolTip(status)
                status_cell = QWidget()
                status_layout = QHBoxLayout(status_cell)
                status_layout.setContentsMargins(0, 0, 0, 0)
                status_layout.addWidget(status_label, 0, Qt.AlignmentFlag.AlignCenter)
                self.tree.setItemWidget(item, 3, status_cell)
                item.setText(4, CurrencyHelper.format_amount(original_price, db=self.db, currency_code=currency))
                primary_price = CurrencyHelper.format_amount(original_price, db=self.db, currency_code=currency)
                reference_price = ""
                if currency != "TRY":
                    converted = CurrencyHelper.convert_amount(self.db, original_price, currency, "TRY")
                    reference_price = CurrencyHelper.format_amount(converted, db=self.db, currency_code="TRY")
                else:
                    converted = CurrencyHelper.convert_amount(self.db, original_price, "TRY", "USD")
                    reference_price = CurrencyHelper.format_amount(converted, db=self.db, currency_code="USD")
                qty_spin = _QuantityStepper()
                qty_spin.setRange(1, max(1, stock))
                qty_spin.setValue(1)

            price_cell = QWidget()
            price_layout = QVBoxLayout(price_cell)
            price_layout.setContentsMargins(0, 1, 0, 1)
            price_layout.setSpacing(1)
            primary_label = QLabel(primary_price)
            primary_label.setStyleSheet(theme_qss(
                "QLabel { color: @text; background: transparent; border: none; font-weight: 700; }"
            ))
            price_layout.addWidget(primary_label)
            if reference_price:
                reference_label = QLabel(f"\u2248 {reference_price}")
                reference_label.setStyleSheet(theme_qss(
                    "QLabel { color: @text_muted; background: transparent; border: none; font-size: 9px; }"
                ))
                price_layout.addWidget(reference_label)
            self.tree.setItemWidget(item, 4, price_cell)

            qty_spin.setMinimumHeight(32)
            qty_spin.setMaximumHeight(34)
            qty_spin.setMinimumWidth(84)
            qty_spin.setMaximumWidth(84)
            qty_spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            qty_spin.valueChanged.connect(self._update_selected_count)
            self.tree.setItemWidget(item, 5, qty_spin)
            row_id = str(info.get("id") or info.get("name") or "")
            checked, old_qty = selected_state.get(row_id, (False, 1))
            qty_spin.setValue(min(max(qty_spin.minimum(), old_qty), qty_spin.maximum()))
            self._set_row_selected(item, checked)
            row_checkbox.toggled.connect(
                lambda selected, row=item: self._set_row_selected(row, selected)
            )
            select_button = QPushButton()
            select_button.setFixedSize(30, 30)
            select_button.setCursor(Qt.CursorShape.PointingHandCursor)
            select_button.clicked.connect(
                lambda _checked=False, row=item: self._set_row_selected(
                    row, not self._row_is_selected(row)
                )
            )
            self.tree.setItemWidget(item, 6, select_button)

        try:
            self.tree.itemChanged.disconnect(self._update_selected_count)
        except Exception:
            pass
        self.tree.itemChanged.connect(self._update_selected_count)
        self._filter_rows()
        self._update_selected_count()

    def _filter_rows(self):
        query = self.search_input.text().strip().lower()
        status_filter = self.status_filter.currentData()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            info = item.data(1, Qt.ItemDataRole.UserRole) or {}
            item_type = item.data(1, Qt.ItemDataRole.UserRole + 1) or self.current_mode
            system_key = item.data(1, Qt.ItemDataRole.UserRole + 2) or "computer"
            searchable = " ".join(str(info.get(key) or "") for key in ("name", "code", "sku", "barcode", "description", "category")).lower()
            query_match = not query or query in searchable
            system_match = self.current_system == "all" or system_key == self.current_system
            stock = int(info.get("stock") or 0)
            status_match = (
                item_type == "service"
                or status_filter == "all"
                or (status_filter == "available" and stock > 0)
                or (status_filter == "critical" and 0 < stock < 10)
            )
            item.setHidden(not (query_match and system_match and status_match))
        self._update_selected_count()

    def _position_header_checkbox(self):
        if not hasattr(self, "select_visible"):
            return
        header = self.tree.header()
        x = header.sectionViewportPosition(0) + (header.sectionSize(0) - self.select_visible.width()) // 2
        y = (header.height() - self.select_visible.height()) // 2
        self.select_visible.move(x, y)
        self.select_visible.raise_()

    def _toggle_visible_rows(self, state):
        checked = state != Qt.CheckState.Unchecked.value
        self.tree.blockSignals(True)
        try:
            for index in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(index)
                if not item.isHidden():
                    self._set_row_selected(item, checked)
        finally:
            self.tree.blockSignals(False)
        self._update_selected_count()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_header_checkbox()
        if hasattr(self, "find_badge"):
            self.find_badge.move(
                self.search_input.width() - self.find_badge.width() - 9,
                (self.search_input.height() - self.find_badge.height()) // 2,
            )
            self.search_icon.move(
                10,
                (self.search_input.height() - self.search_icon.height()) // 2,
            )

    def _update_selected_count(self):
        selected = 0
        visible = 0
        selected_visible = 0
        subtotal_try = 0.0
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            active = self._row_is_selected(item)
            if active:
                selected += 1
                info = item.data(1, Qt.ItemDataRole.UserRole) or {}
                qty_widget = self.tree.itemWidget(item, 5)
                subtotal_try += float(info.get("price") or 0.0) * (qty_widget.value() if qty_widget else 1)
            if not item.isHidden():
                visible += 1
                if active:
                    selected_visible += 1
            button = self.tree.itemWidget(item, 6)
            if button is not None:
                button.setText("\u2713" if active else "+")
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @accent; color: @selection_text; border: none; border-radius: 7px; font-weight: 800; }"
                    if active else
                    "QPushButton { background: @surface_alt; color: @text_muted; border: 1px solid @border; border-radius: 7px; }"
                ))
        self.lbl_selected.setText(f"{selected} kalem seçildi")
        self.lbl_subtotal.setText(
            f"Ara Toplam: {CurrencyHelper.format_try_for_display(subtotal_try, db=self.db, include_try_reference=False)}"
        )
        state = (
            Qt.CheckState.Unchecked if selected_visible == 0
            else Qt.CheckState.Checked if selected_visible == visible
            else Qt.CheckState.PartiallyChecked
        )
        self.select_visible.blockSignals(True)
        self.select_visible.setCheckState(state)
        self.select_visible.blockSignals(False)

    def get_selected_items(self):
        selected = []
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if not self._row_is_selected(item):
                continue
            info = dict(item.data(1, Qt.ItemDataRole.UserRole) or {})
            item_type = item.data(1, Qt.ItemDataRole.UserRole + 1) or self.current_mode
            qty_widget = self.tree.itemWidget(item, 5)
            qty = qty_widget.value() if qty_widget else 1
            info["qty"] = int(qty)
            info["type"] = "service" if item_type == "service" else "part"
            selected.append(info)
        return selected

    def _handle_accept(self):
        if not self.get_selected_items():
            show_warning(self, "Lütfen en az bir hizmet veya stok ürünü seçin.")
            return
        self.accept()
