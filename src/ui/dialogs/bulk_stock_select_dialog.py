# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_warning
from src.utils.design_system import DesignTokens


class BulkStockSelectDialog(BaseModernDialog):
    SYSTEM_FILTERS = [
        ("Tümü", "all"),
        ("Bilgisayar", "computer"),
        ("Güvenlik Sistemleri", "security"),
        ("Akıllı Ev Sistemleri", "smart_home"),
    ]

    def __init__(self, parent, db, services_data=None, parts_data=None):
        self.db = db
        self.services_data = services_data or {}
        self.parts_data = parts_data or {}
        self.current_mode = "part"
        self.current_system = "all"
        super().__init__(parent=parent, title="Toplu Seçim", width=1080, height=760)
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
                    padding: 10px;
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
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Hizmet veya stok ürünlerini toplu seçin")
        title.setStyleSheet(theme_qss("font-size: 18px; font-weight: 900; color: @text;"))
        subtitle = QLabel("Üstten tür seçin, arama yapın, kalemleri işaretleyin ve adet belirleyin.")
        subtitle.setStyleSheet(theme_qss("font-size: 12px; font-weight: 600; color: @text_muted;"))
        layout.addWidget(title)
        layout.addWidget(subtitle)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        self.btn_services = QPushButton("Hizmet")
        self.btn_parts = QPushButton("Stok")
        for btn in (self.btn_services, self.btn_parts):
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
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
        layout.addLayout(mode_row)
        self._refresh_mode_styles()

        system_row = QHBoxLayout()
        system_row.setSpacing(8)
        self.system_group = QButtonGroup(self)
        self.system_group.setExclusive(True)
        for text, value in self.SYSTEM_FILTERS:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setMinimumHeight(36)
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

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Kalem adı ile ara...")
        self.search_input.textChanged.connect(self._filter_rows)
        layout.addWidget(self.search_input)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Kalem", "Durum", "Birim Fiyat", "Adet"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(False)
        self.tree.header().resizeSection(0, 500)
        self.tree.header().resizeSection(1, 160)
        self.tree.header().resizeSection(2, 160)
        self.tree.header().resizeSection(3, 100)
        layout.addWidget(self.tree, 1)

        actions = QHBoxLayout()
        self.lbl_selected = QLabel("0 kalem seçildi")
        self.lbl_selected.setStyleSheet(theme_qss("font-size: 12px; font-weight: 700; color: @text_muted;"))
        actions.addWidget(self.lbl_selected)
        actions.addStretch()

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(theme_qss("background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 10px; padding: 10px 18px; font-weight: 800;"))
        btn_ok = QPushButton("Seçilenleri Ekle")
        btn_ok.clicked.connect(self._handle_accept)
        btn_ok.setStyleSheet(theme_qss("background: @accent; color: @selection_text; border: none; border-radius: 10px; padding: 10px 18px; font-weight: 800;"))
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_ok)
        layout.addLayout(actions)

    def _refresh_mode_styles(self):
        active_qss = theme_qss(
            """
            QPushButton {
                background: @accent;
                color: @selection_text;
                border: none;
                border-radius: 12px;
                padding: 0 16px;
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
                padding: 0 16px;
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
                background: @selection_bg;
                color: @accent;
                border: 1px solid @accent;
                border-radius: 12px;
                padding: 0 14px;
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
                padding: 0 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                border-color: @accent;
                color: @text;
            }
            """
        )
        for btn, value in self.system_buttons:
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

    def _populate(self):
        self.tree.clear()
        source = self.services_data if self.current_mode == "service" else self.parts_data
        for _, info in sorted(source.items(), key=lambda item: (item[1].get("name") or "").lower()):
            item = QTreeWidgetItem(self.tree)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            name = str(info.get("name") or "")
            item.setText(0, name)
            item.setData(0, Qt.ItemDataRole.UserRole, dict(info))
            item.setData(1, Qt.ItemDataRole.UserRole, self.current_mode)
            item.setData(2, Qt.ItemDataRole.UserRole, self._detect_system_group(info, self.current_mode))

            if self.current_mode == "service":
                item.setText(1, "Hizmet")
                price_try = float(info.get("price") or 0.0)
                item.setText(2, CurrencyHelper.format_try_for_display(price_try, db=self.db, include_try_reference=False))
                qty_spin = QSpinBox()
                qty_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
                qty_spin.setRange(1, 9999)
                qty_spin.setValue(1)
            else:
                stock = int(info.get("stock") or 0)
                currency = str(info.get("currency") or "TRY").upper()
                original_price = float(info.get("original_price") or info.get("price") or 0.0)
                item.setText(1, f"Stok: {stock}")
                item.setText(2, CurrencyHelper.format_amount(original_price, db=self.db, currency_code=currency))
                qty_spin = QSpinBox()
                qty_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
                qty_spin.setRange(1, max(1, stock))
                qty_spin.setValue(1)

            qty_spin.setMinimumHeight(40)
            qty_spin.setMinimumWidth(160)
            qty_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_spin.setSingleStep(1)
            qty_spin.setAccelerated(True)
            qty_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
            DesignTokens.apply_spinbox_styles(qty_spin)
            qty_spin.valueChanged.connect(self._update_selected_count)
            self.tree.setItemWidget(item, 3, qty_spin)

        try:
            self.tree.itemChanged.disconnect(self._update_selected_count)
        except Exception:
            pass
        self.tree.itemChanged.connect(self._update_selected_count)
        self._filter_rows()
        self._update_selected_count()

    def _filter_rows(self):
        query = self.search_input.text().strip().lower()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            text = item.text(0).lower()
            system_key = item.data(2, Qt.ItemDataRole.UserRole) or "computer"
            query_match = not query or query in text
            system_match = self.current_system == "all" or system_key == self.current_system
            item.setHidden(not (query_match and system_match))

    def _update_selected_count(self):
        selected = 0
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item.checkState(0) == Qt.CheckState.Checked:
                selected += 1
        self.lbl_selected.setText(f"{selected} kalem seçildi")

    def get_selected_items(self):
        selected = []
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item.checkState(0) != Qt.CheckState.Checked:
                continue
            info = dict(item.data(0, Qt.ItemDataRole.UserRole) or {})
            item_type = item.data(1, Qt.ItemDataRole.UserRole) or self.current_mode
            qty_widget = self.tree.itemWidget(item, 3)
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
