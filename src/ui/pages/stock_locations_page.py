# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QAbstractSpinBox,
    QFrame,
    QSplitter,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtGui import QColor, QDoubleValidator, QFont
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss, tc


def _item(value, user_data=None, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
    item = QTableWidgetItem(str(value if value is not None else "-"))
    item.setTextAlignment(alignment)
    if user_data is not None:
        item.setData(Qt.ItemDataRole.UserRole, user_data)
    return item


def _badge_item(value, bg_color="#E0E7FF", fg_color="#3730A3", alignment=Qt.AlignmentFlag.AlignCenter):
    item = QTableWidgetItem(str(value if value is not None else "-"))
    item.setTextAlignment(alignment)
    item.setBackground(QColor(bg_color))
    item.setForeground(QColor(fg_color))
    return item


class CountValueEdit(QLineEdit):
    """Reliable numeric editor for count-table cells."""

    def __init__(self, value, decimals, parent=None):
        super().__init__(parent)
        self._decimals = decimals
        self.setValidator(QDoubleValidator(0.0, 999999999.0, decimals, self))
        self.setFixedSize(62, 28)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_value(value)
        self.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @surface_alt;
                color: @text;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 800;
                padding: 0px 4px;
                selection-background-color: @accent;
                selection-color: @selection_text;
            }
            QLineEdit:focus { background: @surface; }
        """))

    def value(self):
        try:
            return max(0.0, float(self.text().strip().replace(",", ".")))
        except ValueError:
            return 0.0

    def set_value(self, value):
        number = max(0.0, float(value))
        if self._decimals:
            text = f"{number:.{self._decimals}f}".rstrip("0").rstrip(".")
        else:
            text = f"{number:.0f}"
        self.setText(text)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()


class CountStepper(QWidget):
    """Compact inline control used for physical stock counts."""

    def __init__(self, value, decimals, parent=None):
        super().__init__(parent)
        self.spn_counted = CountValueEdit(value, decimals)

        self.decrease = self._button("-")
        self.increase = self._button("+")
        self.decrease.clicked.connect(lambda: self._adjust(-1))
        self.increase.clicked.connect(lambda: self._adjust(1))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.decrease)
        layout.addWidget(self.spn_counted)
        layout.addWidget(self.increase)

    def _adjust(self, amount):
        self.spn_counted.set_value(self.spn_counted.value() + amount)

    @staticmethod
    def _button(label):
        button = QToolButton()
        button.setText(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(24, 24)
        button.setStyleSheet(theme_qss("""
            QToolButton {
                background: @surface_alt;
                color: @text_muted;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 800;
            }
            QToolButton:hover {
                background: @accent;
                color: @selection_text;
            }
            QToolButton:pressed { background: @accent_hover; }
        """))
        return button


class StockLocationDialog(ModernDialog):
    """Yeni Depo veya Arac konumu ekleme dialogu."""

    def __init__(self, parent=None):
        super().__init__("Yeni Depo / Arac Ekle", parent, width=520, height=380)
        self.setup_ui()

    def setup_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(14)

        input_style = theme_qss("""
            QLineEdit, QComboBox {
                background: @surface;
                border: 2px solid @border;
                border-radius: 8px;
                padding: 10px 14px;
                color: @text;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: @accent;
            }
        """)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ornek: Merkez Depo veya Servis Araci 1")
        self.name_edit.setStyleSheet(input_style)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Depo", "warehouse")
        self.type_combo.addItem("Servis Araci", "vehicle")
        self.type_combo.addItem("Personel Stogu", "personnel")
        self.type_combo.addItem("Proje Stogu", "project")
        self.type_combo.setStyleSheet(input_style)

        self.plate_edit = QLineEdit()
        self.plate_edit.setPlaceholderText("Ornek: 34 ABC 123 (Servis araci ise)")
        self.plate_edit.setStyleSheet(input_style)

        lbl_style = theme_qss("font-weight: 700; color: @text; font-size: 13px;")

        lbl1 = QLabel("Konum Adi *"); lbl1.setStyleSheet(lbl_style)
        lbl2 = QLabel("Konum Turu"); lbl2.setStyleSheet(lbl_style)
        lbl3 = QLabel("Arac Plakasi"); lbl3.setStyleSheet(lbl_style)

        form.addRow(lbl1, self.name_edit)
        form.addRow(lbl2, self.type_combo)
        form.addRow(lbl3, self.plate_edit)

        layout.addLayout(form)
        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.btn_cancel = QPushButton("Iptal")
        self.btn_cancel.setFixedHeight(42)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                color: @text;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: @surface_alt;
            }
        """))
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("✓ Konumu Kaydet")
        self.btn_save.setFixedHeight(42)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss("""
            QPushButton {
                background: @accent;
                border: none;
                border-radius: 8px;
                color: @selection_text;
                font-weight: 700;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: @accent_hover;
            }
        """))
        self.btn_save.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)

        layout.addLayout(btn_box)

    def values(self):
        return (
            self.name_edit.text().strip(),
            self.type_combo.currentData(),
            self.plate_edit.text().strip(),
        )


class UsePartOnCustomerDialog(ModernDialog):
    """Urunu Servis Cihazina / Musteriye Takma (Stoktan Dusme) Dialogu."""

    def __init__(self, db, part_data, parent=None):
        super().__init__("Musteriye / Servis Cihazina Tak", parent, width=540, height=440)
        self.db = db
        self.part_data = part_data
        self.setup_ui()

    def setup_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)

        info_card = QFrame()
        info_card.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 14px;
            }
        """))
        info_lay = QVBoxLayout(info_card)
        info_lay.setSpacing(4)

        name_lbl = QLabel(f"<b>Urun:</b> {self.part_data.get('name', '-')}")
        name_lbl.setStyleSheet(theme_qss("font-size: 15px; color: @text;"))
        avail_qty = float(self.part_data.get('quantity', 0) or 0)
        unit = str(self.part_data.get('unit', 'Adet') or 'Adet')
        qty_lbl = QLabel(f"<b>Kullanilabilir Stok:</b> {avail_qty:g} {unit}")
        qty_lbl.setStyleSheet(theme_qss("color: @accent; font-size: 13px; font-weight: bold;"))

        info_lay.addWidget(name_lbl)
        info_lay.addWidget(qty_lbl)
        layout.addWidget(info_card)

        form = QFormLayout()
        form.setSpacing(14)

        input_style = theme_qss("""
            QComboBox, QDoubleSpinBox, QLineEdit {
                background: @surface;
                border: 2px solid @border;
                border-radius: 8px;
                padding: 8px 12px;
                color: @text;
                font-size: 13px;
            }
            QComboBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
                border-color: @accent;
            }
        """)

        self.cmb_device = QComboBox()
        self.cmb_device.setStyleSheet(input_style)
        self._load_active_devices()

        self.spn_qty = QDoubleSpinBox()
        self.spn_qty.setStyleSheet(input_style)
        self.spn_qty.setDecimals(3 if unit in ("Metre", "Kg", "Lt") else 0)
        self.spn_qty.setRange(0.001, max(avail_qty, 0.001))
        self.spn_qty.setValue(1.0 if avail_qty >= 1 else avail_qty)

        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("Ornek: Ekran degisimi yapildi")
        self.txt_note.setStyleSheet(input_style)

        lbl_style = theme_qss("font-weight: 700; color: @text; font-size: 13px;")
        lbl_dev = QLabel("Servis Cihazi / Musteri *"); lbl_dev.setStyleSheet(lbl_style)
        lbl_qty = QLabel("Takilacak Miktar *"); lbl_qty.setStyleSheet(lbl_style)
        lbl_not = QLabel("Islem Notu"); lbl_not.setStyleSheet(lbl_style)

        form.addRow(lbl_dev, self.cmb_device)
        form.addRow(lbl_qty, self.spn_qty)
        form.addRow(lbl_not, self.txt_note)

        layout.addLayout(form)
        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        btn_cancel = QPushButton("Iptal")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                color: @text;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover { background: @surface_alt; }
        """))
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("✓ Musteriye Tak (Stoktan Dus)")
        btn_save.setFixedHeight(42)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(theme_qss("""
            QPushButton {
                background: @accent;
                border: none;
                border-radius: 8px;
                color: @selection_text;
                font-weight: 700;
                padding: 0 24px;
            }
            QPushButton:hover { background: @accent_hover; }
        """))
        btn_save.clicked.connect(self._do_use_part)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _load_active_devices(self):
        try:
            self.cmb_device.clear()
            cur = self.db.conn.cursor()
            cur.execute("""
                SELECT tracking_no, customer_name, device_brand, device_model, status
                FROM devices
                WHERE COALESCE(is_archived, 0) = 0 AND COALESCE(is_deleted, 0) = 0
                ORDER BY id DESC LIMIT 100
            """)
            rows = cur.fetchall() or []
            if not rows:
                self.cmb_device.addItem("Aktif servis kaydi bulunamadi", None)
                return

            for r in rows:
                if hasattr(r, "keys"):
                    t_no = r["tracking_no"]
                    c_name = r["customer_name"] or "Musteri"
                    d_model = r["device_model"] or r["device_brand"] or "Cihaz"
                    st = r["status"] or ""
                else:
                    t_no = r[0]
                    c_name = r[1] or "Musteri"
                    d_model = r[3] or r[2] or "Cihaz"
                    st = r[4] or ""

                display = f"[{t_no}] {c_name} - {d_model} ({st})"
                self.cmb_device.addItem(display, t_no)
        except Exception:
            self.cmb_device.addItem("Cihazlar yuklenemedi", None)

    def _do_use_part(self):
        tracking_no = self.cmb_device.currentData()
        if not tracking_no:
            QMessageBox.warning(self, "Uyari", "Lutfen urunun takilacagi bir servis cihazini secin.")
            return

        part_id = self.part_data.get("part_id")
        quantity = self.spn_qty.value()

        try:
            ok = self.db.use_part(
                part_id=part_id,
                quantity=quantity,
                tracking_no=tracking_no,
                commit=True
            )
            if ok:
                QMessageBox.information(
                    self,
                    "Basarili",
                    f"Urun [{tracking_no}] nolu servis cihazina/musteriye takildi ve stoktan dusuldu."
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Hata", "Urun stoktan dusulemedi. Stok miktarini kontrol edin.")
        except Exception as exc:
            QMessageBox.critical(self, "Hata", f"Islem sirasinda hata olustu: {exc}")


class StockLocationsPage(QWidget):
    """Modernized Pro Warehouse & Vehicle Inventory Management Page."""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.transfer_lines = []
        self.kit_lines = []
        self.inventory_page = 0
        self.inventory_page_size = 5
        self._build_ui()
        self.refresh_data()

    def _button(self, text, primary=False):
        button = QPushButton(text)
        button.setMinimumHeight(32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            button.setStyleSheet(theme_qss("""
                QPushButton {
                    background: @accent;
                    color: @selection_text;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-weight: 700;
                    font-size: 13px;
                }
                QPushButton:hover { background: @accent_hover; }
            """))
        else:
            button.setStyleSheet(theme_qss("""
                QPushButton {
                    background: @surface_alt;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 4px;
                    padding: 4px 12px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover { background: @surface_alt; border-color: @accent; }
            """))
        return button

    def _count_spinbox(self):
        """Create a compact integer editor for stock counts."""
        spinbox = QSpinBox()
        spinbox.setRange(1, 999999999)
        spinbox.setValue(1)
        spinbox.setFixedHeight(38)
        spinbox.setMinimumWidth(150)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinbox.setGroupSeparatorShown(False)
        spinbox.setStyleSheet(theme_qss("QSpinBox { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 4px 8px; color: @text; font-size: 13px; font-weight: bold; } QSpinBox:focus { border-color: @accent; }"))
        return spinbox

    def _card(self, title_text, value_text, click_handler=None, accent_token="@accent", detail_text=""):
        card = QFrame()
        card.setFixedHeight(128)
        if click_handler:
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda event: click_handler(card)
        card.setStyleSheet(theme_qss(f"""
            QFrame {{
                background: @surface;
                border: 1px solid @surface;
                border-radius: 8px;
                padding: 0;
            }}
            QLabel {{ background: transparent; border: none; }}
            QFrame:hover {{
                border-color: @accent;
            }}
        """))
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        lbl_t = QLabel(title_text)
        lbl_t.setStyleSheet(theme_qss(f"color: {accent_token}; font-family: Inter; font-size: 11px; font-weight: 600;"))
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.addWidget(lbl_t, 1)
        icon = QLabel("\u25a3")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(theme_qss(f"background: @surface_alt; color: {accent_token}; border: 1px solid @border; border-radius: 5px; font-size: 18px; font-weight: 700;"))
        title_row.addWidget(icon)
        lay.addLayout(title_row)

        lbl_v = QLabel(str(value_text))
        lbl_v.setStyleSheet(theme_qss(f"color: {accent_token}; font-family: 'JetBrains Mono'; font-size: 23px; font-weight: 700;"))

        lay.addWidget(lbl_v)
        card.lbl_value = lbl_v
        if detail_text:
            lbl_d = QLabel(detail_text)
            lbl_d.setWordWrap(True)
            lbl_d.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 700;"))
            lay.addWidget(lbl_d)
            card.lbl_detail = lbl_d
        else:
            card.lbl_detail = None
        return card

    def _build_ui(self):
        self.setObjectName("StockLocationsPage")
        self.setStyleSheet(theme_qss(
            "QWidget#StockLocationsPage { background: @window; font-family: Inter; }"
        ))
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # 1. Compact Header Bar: Title + Stat Cards + Action Button (Single Compact Row)
        header = QHBoxLayout()
        header.setSpacing(10)

        heading = QVBoxLayout()
        heading.setSpacing(2)
        title = QLabel("Depo ve Ara\u00e7 Stoklar\u0131 & Transfer Y\u00f6netimi")
        title.setWordWrap(True)
        title.setStyleSheet(theme_qss("font-family: Inter; font-size: 24px; font-weight: 700; color: @text;"))
        subtitle = QLabel(
            "Merkez depo, \u015fantiye konsinye alanlar\u0131 ve servis ara\u00e7lar\u0131ndaki mobil envanter hareketleri."
        )
        subtitle.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)

        system_badge = QLabel("LOKASYON BAZLI ERP")
        system_badge.setStyleSheet(theme_qss(
            "background: @surface_alt; color: @success; border: 1px solid @border; "
            "border-radius: 4px; padding: 3px 7px; font-size: 10px; "
            "font-weight: 800; letter-spacing: 1px;"
        ))
        header.addWidget(system_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        # Compact Stat Pills
        self.card_depo = self._card("MERKEZ DEPO (EREN DEPO)", "0 Kalem", self._show_depot_filter, "@success", "0 Aktif Lokasyon / Raf Kat\u0131")
        self.card_arac = self._card("SERV\u0130S ARA\u00c7LARI (MOB\u0130L)", "0 Kalem", self._show_vehicle_filter, "@finance_action_collection", "0 Donan\u0131ml\u0131 Mobil Saha Arac\u0131")
        self.card_urun = self._card("AKT\u0130F TRANSFER / YOLDA", "0 Sevkiyat", self._show_transfer_filter, "@accent", "Karekodlu Teslimat Bekleniyor")
        self.card_hareket = self._card("KONS\u0130NYE / \u015eANT\u0130YE", "0 Kalem Cihaz", self._show_inventory_filter, "@danger", "0 Farkl\u0131 M\u00fc\u015fteri Sahas\u0131nda")

        header.addStretch()

        add_location = self._button("+ Yeni Depo / Ara\u00e7 Ekle")
        add_location.setFixedHeight(36)
        add_location.clicked.connect(self.add_location)
        header.addWidget(add_location)

        start_transfer = self._button("+ Stok Transferi Ba\u015flat", True)
        start_transfer.setFixedHeight(36)
        start_transfer.setStyleSheet(theme_qss(
            "QPushButton { background: @finance_secondary; color: @finance_action_income_text; "
            "border: none; border-radius: 4px; padding: 4px 12px; font-weight: 600; } "
            "QPushButton:hover { background: @finance_action_income; }"
        ))
        start_transfer.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        header.addWidget(start_transfer)

        root.addLayout(header)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        for card in (self.card_depo, self.card_arac, self.card_urun, self.card_hareket):
            stats.addWidget(card, 1)
        root.addLayout(stats)

        # 2. Compact 1-Line Info Strip
        info_card = QFrame()
        info_card.setFixedHeight(32)
        info_card.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface;
                border-left: 3px solid @accent;
                border-radius: 6px;
                padding: 0px 10px;
            }
            QLabel { color: @text; font-size: 12px; }
        """))
        info_lay = QHBoxLayout(info_card)
        info_lay.setContentsMargins(10, 0, 10, 0)
        info_txt = QLabel(
            "💡 <b>Çift Tık:</b> Kartı Düzenle &nbsp;&nbsp;|&nbsp;&nbsp; "
            "<b>Sağ Tık:</b> Müşteriye/Servise Tak (Stoktan Düş) &nbsp;&nbsp;|&nbsp;&nbsp; "
            "<b>Transfer Sekmesi:</b> Depolar Arası Sevk"
        )
        info_lay.addWidget(info_txt)

        # 3. Main Segmented Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(theme_qss("""
            QTabWidget::pane {
                border: 1px solid @border;
                border-radius: 6px;
                background: @surface;
                padding: 0px;
            }
            QTabBar::tab {
                background: @surface;
                color: @text_muted;
                padding: 10px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: 600;
                font-size: 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: @finance_surface_lowest;
                color: @finance_action_collection;
                border-bottom: 2px solid @accent;
            }
            QTabBar::tab:hover:!selected {
                background: @surface;
                color: @text;
            }
        """))

        self.tabs.addTab(self._build_inventory_tab(), "📍 Konum Stokları")
        self.tabs.addTab(self._build_transfer_tab(), "🔄 Transfer & İade")
        self.tabs.addTab(self._build_count_tab(), "📋 Araç Sayımı")
        self.tabs.addTab(self._build_kit_tab(), "🧰 Hazır Kitler")
        self.tabs.addTab(self._build_history_tab(), "📜 Hareket Geçmişi")
        root.addWidget(self.tabs, 1)
        root.addWidget(info_card)
        root.addWidget(self._build_reference_footer())

    def _build_reference_footer(self):
        footer = QWidget()
        footer.setObjectName("StockReferenceFooter")
        grid = QHBoxLayout(footer)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        cards = (
            ("Mobil Stok Guvence Protokolu", "Arac bagaj kapak sensoru ve RFID donanim kasasi aktif. Cihazlar mobil teknisyen terminaliyle eslenir.", "@success"),
            ("Ikmal Talebi: TR-2024-884", "Eren Depo -> 34 AY 001 icin 2 adet NVR hazirlik asamasinda. Beklenen varis: 16:30.", "@accent"),
            ("El Terminali ve Kamera Tarama", "Barkod okuyucu hazir. Klavye kisayolu: F2 ile aninda seri numarasi okutun.", "@finance_secondary"),
        )
        for title_text, body_text, accent in cards:
            card = QFrame()
            card.setMinimumHeight(78)
            card.setStyleSheet(theme_qss(
                "QFrame { background: @surface; border: 1px solid @surface; "
                "border-radius: 8px; } QLabel { background: transparent; border: none; }"
            ))
            box = QVBoxLayout(card)
            box.setContentsMargins(12, 8, 12, 8)
            box.setSpacing(3)
            title_label = QLabel(title_text)
            title_label.setStyleSheet(theme_qss(f"color: {accent}; font-weight: 600; font-size: 12px;"))
            body_label = QLabel(body_text)
            body_label.setWordWrap(True)
            body_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
            box.addWidget(title_label)
            box.addWidget(body_label)
            grid.addWidget(card, 1)
        return footer

    def _configure_table(self, table):
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.setShowGrid(False)
        table.horizontalHeader().setFixedHeight(32)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @finance_surface_lowest;
                alternate-background-color: @window;
                color: @text;
                gridline-color: @border;
                border: none;
                border-radius: 4px;
                font-family: Inter;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid @surface;
            }
            QTableWidget::item:hover {
                background-color: @surface_alt;
                color: @accent;
            }
            QTableWidget::item:selected {
                background-color: @finance_active_bg;
                color: @text;
            }
            QHeaderView::section {
                background-color: @surface_high;
                color: @text_muted;
                padding: 4px 8px;
                font-weight: 700;
                font-size: 10px;
                border: none;
                text-transform: uppercase;
            }
        """))

    def _build_inventory_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)

        tools = QHBoxLayout()
        self.inventory_location = QComboBox()
        self.inventory_location.setStyleSheet(theme_qss("""
            QComboBox {
                background: @surface_alt; border: 1px solid @border;
                border-radius: 4px; padding: 5px 10px; color: @text;
                font-size: 12px;
            }
            QComboBox:focus { border-color: @accent; }
        """))
        self.inventory_location.currentIndexChanged.connect(self._inventory_query_changed)
        self.inventory_location.currentIndexChanged.connect(self._update_inventory_context)

        self.inventory_search = QLineEdit()
        self.inventory_search.setPlaceholderText("🔍 Ürün adı, stok kodu veya barkod ile arayın...")
        self.inventory_search.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @finance_surface_lowest; border: 1px solid @border;
                border-radius: 4px; padding: 5px 10px; color: @text;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: @accent; }
        """))
        self.inventory_search.textChanged.connect(self._inventory_query_changed)

        lbl_loc = QLabel("Konum Filtresi:")
        lbl_loc.setStyleSheet(theme_qss("font-weight: 700; color: @text; font-size: 13px;"))

        tools.addWidget(lbl_loc)
        tools.addWidget(self.inventory_location, 1)
        tools.addWidget(self.inventory_search, 2)
        layout.addLayout(tools)

        location_context = QHBoxLayout()
        self.inventory_location_meta = QLabel("Konum se\u00e7ilmedi")
        self.inventory_location_meta.setStyleSheet(theme_qss("color: @finance_action_collection; font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 600;"))
        location_context.addWidget(self.inventory_location_meta, 1)
        self.inventory_filter_button = self._button("\u2637")
        self.inventory_filter_button.setFixedSize(34, 32)
        self.inventory_filter_button.setToolTip("Konum filtresini a\u00e7")
        self.inventory_filter_button.clicked.connect(self.inventory_location.showPopup)
        self.inventory_refresh_button = self._button("\u21bb")
        self.inventory_refresh_button.setFixedSize(34, 32)
        self.inventory_refresh_button.setToolTip("Envanteri yenile")
        self.inventory_refresh_button.clicked.connect(self.load_inventory)
        location_context.addWidget(self.inventory_filter_button)
        location_context.addWidget(self.inventory_refresh_button)
        layout.addLayout(location_context)

        self.inventory_table = QTableWidget(0, 9)
        self.inventory_table.setHorizontalHeaderLabels(
            ["\u00dcr\u00fcn Tan\u0131m\u0131", "Stok Kodu", "Barkod", "Birim", "Mevcut Miktar", "Rezerve", "Kullan\u0131labilir", "Min. E\u015fik", "H\u0131zl\u0131 \u0130\u015flemler"]
        )
        self._configure_table(self.inventory_table)
        self.inventory_table.verticalHeader().setDefaultSectionSize(50)
        self.inventory_table.setWordWrap(True)
        for column in (1, 2, 3, 4, 5, 6, 7):
            self.inventory_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.inventory_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.inventory_table.setColumnWidth(8, 164)

        self.inventory_table.itemDoubleClicked.connect(self._on_inventory_double_clicked)
        self.inventory_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.inventory_table.customContextMenuRequested.connect(self._show_inventory_context_menu)

        layout.addWidget(self.inventory_table, 1)

        self.inventory_summary = QLabel()
        self.inventory_summary.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700; font-size: 13px;"))
        inventory_footer = QHBoxLayout()
        inventory_footer.addWidget(self.inventory_summary, 1)
        self.inventory_previous = QPushButton("<")
        self.inventory_page_label = QLabel("1 / 1")
        self.inventory_page_label.setMinimumWidth(54)
        self.inventory_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inventory_next = QPushButton(">")
        for button in (self.inventory_previous, self.inventory_next):
            button.setFixedSize(34, 30)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.inventory_previous.clicked.connect(lambda: self._change_inventory_page(-1))
        self.inventory_next.clicked.connect(lambda: self._change_inventory_page(1))
        inventory_footer.addWidget(self.inventory_previous)
        inventory_footer.addWidget(self.inventory_page_label)
        inventory_footer.addWidget(self.inventory_next)
        layout.addLayout(inventory_footer)
        return page

    def _inventory_query_changed(self, *_args):
        self.inventory_page = 0
        self._update_inventory_context()
        self.load_inventory()

    def _update_inventory_context(self, *_args):
        index = self.inventory_location.currentIndex()
        location = self._locations[index] if 0 <= index < len(getattr(self, "_locations", [])) else None
        if not location:
            self.inventory_location_meta.setText("Konum se\u00e7ilmedi")
            return
        location_type = location.get("type") or location.get("location_type") or "location"
        self.inventory_location_meta.setText(f"Aktif Konum: {location.get('name') or '-'}  |  Tip: {location_type}")

    def _change_inventory_page(self, delta):
        self.inventory_page += delta
        self.load_inventory()

    def _on_inventory_double_clicked(self, item):
        row = item.row()
        item_0 = self.inventory_table.item(row, 0)
        if not item_0:
            return
        part_id = item_0.data(Qt.ItemDataRole.UserRole)
        if part_id:
            try:
                from src.ui.dialogs.add_stock_dialog import AddStockDialog
                dialog = AddStockDialog(self.db, self, item_id=part_id)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.refresh_data()
            except Exception as exc:
                QMessageBox.warning(self, "Stok Kartı Açılamadı", str(exc))

    def _show_inventory_context_menu(self, pos):
        row = self.inventory_table.rowAt(pos.y())
        if row < 0:
            return

        item_0 = self.inventory_table.item(row, 0)
        if not item_0:
            return

        part_id = item_0.data(Qt.ItemDataRole.UserRole)
        part_name = item_0.text()

        row_data = {
            "part_id": part_id,
            "name": part_name,
            "code": self.inventory_table.item(row, 1).text() if self.inventory_table.item(row, 1) else "",
            "unit": self.inventory_table.item(row, 3).text() if self.inventory_table.item(row, 3) else "Adet",
            "quantity": float(self.inventory_table.item(row, 6).text() or 0) if self.inventory_table.item(row, 6) else 0,
        }

        menu = QMenu(self)
        menu.setStyleSheet(theme_qss("""
            QMenu {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 10px 22px;
                border-radius: 6px;
                font-weight: 600;
            }
            QMenu::item:selected {
                background: @accent;
                color: @selection_text;
            }
        """))

        act_edit = menu.addAction("✏️ Stok Kartını Düzenle (Çift Tık)")
        act_use = menu.addAction("🛠️ Müşteriye / Servis Cihazına Tak (Stoktan Düş)")
        act_transfer = menu.addAction("🔄 Başka Depoya / Araca Transfer Et")

        action = menu.exec(self.inventory_table.viewport().mapToGlobal(pos))
        if action == act_edit:
            self._on_inventory_double_clicked(item_0)
        elif action == act_use:
            dialog = UsePartOnCustomerDialog(self.db, row_data, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_data()
        elif action == act_transfer:
            self.tabs.setCurrentIndex(1)

    def _build_transfer_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        card = QFrame()
        card.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 14px;
            }
        """))
        card_lay = QVBoxLayout(card)
        card_lay.setSpacing(12)

        locations = QHBoxLayout()
        self.source_combo = QComboBox()
        self.target_combo = QComboBox()
        self.source_combo.setStyleSheet(theme_qss("QComboBox { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 8px 12px; color: @text; font-size: 13px; font-weight: bold; }"))
        self.target_combo.setStyleSheet(theme_qss("QComboBox { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 8px 12px; color: @text; font-size: 13px; font-weight: bold; }"))
        self.source_combo.currentIndexChanged.connect(self.load_transfer_products)
        swap = self._button("⇄ Kaynak / Hedef Değiştir")
        swap.clicked.connect(self.swap_locations)

        lbl_s = QLabel("Kaynak Konum:"); lbl_s.setStyleSheet(theme_qss("font-weight: 700; color: @text;"))
        lbl_t = QLabel("Hedef Konum:"); lbl_t.setStyleSheet(theme_qss("font-weight: 700; color: @text;"))

        locations.addWidget(lbl_s)
        locations.addWidget(self.source_combo, 1)
        locations.addWidget(lbl_t)
        locations.addWidget(self.target_combo, 1)
        locations.addWidget(swap)
        card_lay.addLayout(locations)

        kit_row = QHBoxLayout()
        self.transfer_kit = QComboBox()
        self.transfer_kit.setStyleSheet(theme_qss("QComboBox { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 8px 12px; color: @text; font-size: 13px; }"))
        add_kit = self._button("📦 Hazır Kiti Sepete Ekle")
        add_kit.clicked.connect(self.add_transfer_kit)

        lbl_k = QLabel("Hazır Kit:"); lbl_k.setStyleSheet(theme_qss("font-weight: 700; color: @text;"))
        kit_row.addWidget(lbl_k)
        kit_row.addWidget(self.transfer_kit, 1)
        kit_row.addWidget(add_kit)
        card_lay.addLayout(kit_row)

        layout.addWidget(card)

        add_line = QHBoxLayout()
        self.transfer_product = QComboBox()
        self.transfer_product.setMinimumWidth(350)
        self.transfer_product.setStyleSheet(theme_qss("QComboBox { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 8px 12px; color: @text; font-size: 13px; }"))

        self.transfer_quantity = self._count_spinbox()

        add = self._button("+ Listeye Ekle", True)
        add.clicked.connect(self.add_transfer_line)

        lbl_p = QLabel("Transfer Ürünü:"); lbl_p.setStyleSheet(theme_qss("font-weight: 700; color: @text;"))
        lbl_q = QLabel("Miktar:"); lbl_q.setStyleSheet(theme_qss("font-weight: 700; color: @text;"))

        add_line.addWidget(lbl_p)
        add_line.addWidget(self.transfer_product, 1)
        add_line.addWidget(lbl_q)
        add_line.addWidget(self.transfer_quantity)
        add_line.addWidget(add)
        layout.addLayout(add_line)

        self.transfer_table = QTableWidget(0, 4)
        self.transfer_table.setHorizontalHeaderLabels(["Ürün Adı", "Birim", "Miktar", "İşlem"])
        self._configure_table(self.transfer_table)
        layout.addWidget(self.transfer_table, 1)

        footer = QHBoxLayout()
        self.transfer_note = QLineEdit()
        self.transfer_note.setPlaceholderText("Transfer / İade açıklama notu ekleyin...")
        self.transfer_note.setStyleSheet(theme_qss("QLineEdit { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 10px 14px; color: @text; font-size: 13px; }"))

        save = self._button("✓ Transferi Tamamla", True)
        save.setFixedHeight(44)
        save.clicked.connect(self.save_transfer)
        footer.addWidget(self.transfer_note, 1)
        footer.addWidget(save)
        layout.addLayout(footer)
        return page

    def _build_kit_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        header = QHBoxLayout()
        self.kit_name = QLineEdit()
        self.kit_name.setPlaceholderText("Örnek: 8 Kameralı Saha Kurulum Kiti")
        self.kit_name.setStyleSheet(theme_qss("QLineEdit { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 10px 14px; color: @text; font-size: 13px; }"))
        lbl_kn = QLabel("Kit Adı:"); lbl_kn.setStyleSheet(theme_qss("font-weight: 700; color: @text; font-size: 13px;"))
        header.addWidget(lbl_kn)
        header.addWidget(self.kit_name, 1)
        layout.addLayout(header)

        add_row = QHBoxLayout()
        self.kit_product = QComboBox()
        self.kit_product.setStyleSheet(theme_qss("QComboBox { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 8px 12px; color: @text; font-size: 13px; }"))
        self.kit_quantity = self._count_spinbox()

        add = self._button("+ Kit Satırına Ekle", True)
        add.clicked.connect(self.add_kit_line)

        add_row.addWidget(self.kit_product, 1)
        add_row.addWidget(self.kit_quantity)
        add_row.addWidget(add)
        layout.addLayout(add_row)

        self.kit_table = QTableWidget(0, 3)
        self.kit_table.setHorizontalHeaderLabels(["Ürün Adı", "Miktar", "İşlem"])
        self._configure_table(self.kit_table)
        layout.addWidget(self.kit_table, 1)

        save = self._button("✓ Kiti Kaydet", True)
        save.setFixedHeight(44)
        save.clicked.connect(self.save_kit)
        layout.addWidget(save)
        return page

    def _build_count_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        tools = QHBoxLayout()
        self.count_location = QComboBox()
        self.count_location.setStyleSheet(theme_qss("QComboBox { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 8px 14px; color: @text; font-size: 13px; font-weight: bold; }"))
        self.count_location.currentIndexChanged.connect(self.load_count)
        reload_button = self._button("🔄 Sayım Listesini Yenile")
        reload_button.clicked.connect(self.load_count)

        lbl_cl = QLabel("Sayılacak Konum:"); lbl_cl.setStyleSheet(theme_qss("font-weight: 700; color: @text; font-size: 13px;"))
        tools.addWidget(lbl_cl)
        tools.addWidget(self.count_location, 1)
        tools.addWidget(reload_button)
        layout.addLayout(tools)

        self.count_table = QTableWidget(0, 4)
        self.count_table.setHorizontalHeaderLabels(["Ürün Adı", "Sistem Miktarı", "Sayılan Miktar", "Fark"])
        self._configure_table(self.count_table)
        layout.addWidget(self.count_table, 1)

        footer = QHBoxLayout()
        self.count_note = QLineEdit()
        self.count_note.setPlaceholderText("Sayım açıklaması veya not ekleyin...")
        self.count_note.setStyleSheet(theme_qss("QLineEdit { background: @surface; border: 2px solid @border; border-radius: 8px; padding: 10px 14px; color: @text; font-size: 13px; }"))

        save = self._button("✓ Sayımı Kaydet & Stok Güncelle", True)
        save.setFixedHeight(44)
        save.clicked.connect(self.save_count)
        footer.addWidget(self.count_note, 1)
        footer.addWidget(save)
        layout.addLayout(footer)
        return page

    def _build_history_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        refresh = self._button("🔄 Geçmişi Yenile")
        refresh.clicked.connect(self.load_history)
        layout.addWidget(refresh, 0, Qt.AlignmentFlag.AlignRight)

        self.history_table = QTableWidget(0, 8)
        self.history_table.setHorizontalHeaderLabels(
            ["Referans No", "Kaynak Konum", "Hedef Konum", "Ürünler", "Kalem Sayısı", "Toplam Miktar", "Açıklama", "Tarih"]
        )
        self._configure_table(self.history_table)
        layout.addWidget(self.history_table, 1)
        return page

    def _actor_name(self):
        user = getattr(self.main_window, "current_user", None)
        if isinstance(user, dict):
            return str(user.get("username") or user.get("name") or "")
        return str(getattr(user, "username", "") or "")

    def _show_location_filter(self, location_type, anchor):
        locations = [
            loc for loc in getattr(self, "_locations", [])
            if str(loc.get("location_type") or loc.get("type") or "") in (
                location_type if isinstance(location_type, tuple) else (location_type,)
            )
        ]
        if not locations:
            return
        if len(locations) == 1:
            self.inventory_location.setCurrentIndex(
                self.inventory_location.findData(locations[0]["id"])
            )
            self.tabs.setCurrentIndex(0)
            return
        menu = QMenu(self)
        for location in locations:
            label = str(location.get("name") or "-")
            if location.get("vehicle_plate"):
                label += " ({})".format(location["vehicle_plate"])
            action = menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, location_id=location["id"]: self._select_inventory_location(location_id)
            )
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _select_inventory_location(self, location_id):
        index = self.inventory_location.findData(location_id)
        if index >= 0:
            self.inventory_location.setCurrentIndex(index)
        self.tabs.setCurrentIndex(0)

    def _show_depot_filter(self, anchor):
        self._show_location_filter(("main", "warehouse"), anchor)

    def _show_vehicle_filter(self, anchor):
        self._show_location_filter("vehicle", anchor)

    def _show_inventory_filter(self, _anchor):
        self.tabs.setCurrentIndex(0)
        self.inventory_search.clear()
        self.inventory_location.setFocus()

    def _show_transfer_filter(self, _anchor):
        self.tabs.setCurrentIndex(4)

    def refresh_data(self):
        self.db.ensure_stock_location_schema()
        locations = self.db.get_stock_locations()
        self._locations = locations

        # Update KPI Cards
        location_type = lambda loc: loc.get("type") or loc.get("location_type")
        inventory_totals = {}
        for location in locations:
            location_id = int(location["id"])
            rows = self.db.get_location_inventory(location_id)
            inventory_totals[location_id] = sum(float(row.get("quantity") or 0) for row in rows)
        depot_locations = [loc for loc in locations if location_type(loc) in ("main", "warehouse")]
        vehicle_locations = [loc for loc in locations if location_type(loc) == "vehicle"]
        site_locations = [loc for loc in locations if location_type(loc) in ("consignment", "site", "project")]
        depot_total = sum(inventory_totals[int(loc["id"])] for loc in depot_locations)
        vehicle_total = sum(inventory_totals[int(loc["id"])] for loc in vehicle_locations)
        site_total = sum(inventory_totals[int(loc["id"])] for loc in site_locations)
        transfer_total = len(self.db.get_stock_transfer_history(limit=250))
        self.card_depo.lbl_value.setText(f"{depot_total:,.0f} Kalem")
        self.card_depo.lbl_detail.setText(f"{len(depot_locations)} Aktif Lokasyon / Raf Kat\u0131")
        self.card_arac.lbl_value.setText(f"{vehicle_total:,.0f} Kalem")
        self.card_arac.lbl_detail.setText(f"{len(vehicle_locations)} Donan\u0131ml\u0131 Mobil Saha Arac\u0131")
        self.card_urun.lbl_value.setText(f"{transfer_total} Sevkiyat")
        self.card_hareket.lbl_value.setText(f"{site_total} Kalem Cihaz")
        self.card_hareket.lbl_detail.setText(f"{len(site_locations)} Farkl\u0131 M\u00fc\u015fteri Sahas\u0131nda")
        
        combos = [
            self.inventory_location,
            self.source_combo,
            self.target_combo,
            self.count_location,
        ]
        selected = [combo.currentData() for combo in combos]
        for index, combo in enumerate(combos):
            combo.blockSignals(True)
            combo.clear()
            for location in locations:
                label = location["name"]
                if location.get("vehicle_plate"):
                    label += f" ({location['vehicle_plate']})"
                combo.addItem(label, location["id"])
            wanted = combo.findData(selected[index])
            combo.setCurrentIndex(wanted if wanted >= 0 else min(index, combo.count() - 1))
            combo.blockSignals(False)

        if self.target_combo.count() > 1 and self.target_combo.currentData() == self.source_combo.currentData():
            self.target_combo.setCurrentIndex(1)

        self.transfer_kit.clear()
        self.transfer_kit.addItem("Kit seçin...", None)
        for kit in self.db.get_stock_kits():
            self.transfer_kit.addItem(kit["name"], kit["id"])

        self.kit_product.clear()
        source_location_id = self.source_combo.currentData()
        if source_location_id:
            for row in self.db.get_location_inventory(source_location_id):
                self.kit_product.addItem(row["name"], row)

        self._update_inventory_context()
        self.load_inventory()
        self.load_transfer_products()
        self.load_count()
        self.load_history()

    def add_location(self):
        dialog = StockLocationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, location_type, plate = dialog.values()
        if not name:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen konum adını girin.")
            return
        try:
            self.db.create_stock_location(name, location_type, plate or None)
            self.refresh_data()
        except Exception as exc:
            QMessageBox.warning(self, "Konum Kaydedilemedi", str(exc))

    def load_inventory(self):
        location_id = self.inventory_location.currentData()
        if not location_id:
            return
        rows = self.db.get_location_inventory(location_id, self.inventory_search.text())
        visible = [row for row in rows if abs(float(row["quantity"])) > 0.000001]
        total_pages = max(1, (len(visible) + self.inventory_page_size - 1) // self.inventory_page_size)
        self.inventory_page = max(0, min(self.inventory_page, total_pages - 1))
        start = self.inventory_page * self.inventory_page_size
        page_rows = visible[start:start + self.inventory_page_size]
        self.inventory_table.setRowCount(len(page_rows))

        for row_index, row in enumerate(page_rows):
            available = float(row["quantity"]) - float(row["reserved_quantity"])
            unit = row.get("unit") or "Adet"
            values = [
            f"{row['name']}\n{row.get('category') or 'Genel'}", row.get("code") or "-", row.get("barcode") or "-",
                unit, f"{float(row['quantity']):g}",
                f"{float(row['reserved_quantity']):g}", f"{available:g}",
                f"{float(row.get('min_quantity') or 0):g}",
            ]
            for column, value in enumerate(values):
                if column == 3: # Unit Badge
                    self.inventory_table.setItem(row_index, column, _badge_item(value, tc("surface_alt"), tc("text")))
                elif column == 4: # Total Qty
                    self.inventory_table.setItem(row_index, column, _item(value, row["part_id"], Qt.AlignmentFlag.AlignCenter))
                elif column == 6: # Available Qty
                    bg = tc("finance_success_bg") if available > 0 else tc("finance_warning_bg")
                    fg = tc("success") if available > 0 else tc("danger")
                    self.inventory_table.setItem(row_index, column, _badge_item(value, bg, fg))
                elif column == 7:
                    minimum = float(row.get("min_quantity") or 0)
                    quantity = float(row.get("quantity") or 0)
                    if minimum > 0 and quantity <= minimum:
                        self.inventory_table.setItem(row_index, column, _badge_item(value, tc("finance_warning_bg"), tc("danger")))
                    else:
                        self.inventory_table.setItem(row_index, column, _item(value, row["part_id"], Qt.AlignmentFlag.AlignCenter))
                else:
                    self.inventory_table.setItem(row_index, column, _item(value, row["part_id"]))

            row_data = {
                "part_id": row["part_id"],
                "name": row["name"],
                "code": row.get("code") or "",
                "unit": unit,
                "quantity": available,
            }
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(3, 2, 3, 2)
            actions_layout.setSpacing(4)
            transfer = QPushButton("\u21c4")
            use_part = QPushButton("\u2295")
            edit = QPushButton("\u270e")
            transfer.setToolTip("Stok transferi baslat")
            use_part.setToolTip("Musteri veya servis kaydina stok dus")
            edit.setToolTip("Stok kartini duzenle")
            for button in (transfer, use_part, edit):
                button.setFixedHeight(26)
                button.setStyleSheet(theme_qss(
                    DesignTokens.get_button_qss("secondary", size="sm")
                    + " QPushButton { padding: 0 2px; font-size: 10px; }"
                ))
                actions_layout.addWidget(button)
            transfer.setFixedWidth(42)
            use_part.setFixedWidth(34)
            edit.setFixedWidth(34)
            transfer.clicked.connect(lambda _checked=False: self.tabs.setCurrentIndex(1))
            use_part.clicked.connect(
                lambda _checked=False, data=row_data: self._use_inventory_part(data)
            )
            edit.clicked.connect(
                lambda _checked=False, item=self.inventory_table.item(row_index, 0): self._on_inventory_double_clicked(item)
            )
            self.inventory_table.setCellWidget(row_index, 8, actions)

        self.inventory_summary.setText(
            f"📊 Bu konumda toplam {len(visible)} farklı kalem ürün kayıtlı."
        )
        self.inventory_page_label.setText(f"{self.inventory_page + 1} / {total_pages}")
        self.inventory_previous.setEnabled(self.inventory_page > 0)
        self.inventory_next.setEnabled(self.inventory_page + 1 < total_pages)

    def _use_inventory_part(self, row_data):
        dialog = UsePartOnCustomerDialog(self.db, row_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()

    def load_transfer_products(self):
        location_id = self.source_combo.currentData()
        self.transfer_product.clear()
        if not location_id:
            return
        for row in self.db.get_location_inventory(location_id):
            if float(row["quantity"]) <= 0.000001:
                continue
            unit = row.get('unit') or 'Adet'
            self.transfer_product.addItem(
                f"{row['name']} | {float(row['quantity']):g} {unit}", row
            )

    def swap_locations(self):
        source = self.source_combo.currentData()
        target = self.target_combo.currentData()
        self.source_combo.setCurrentIndex(self.source_combo.findData(target))
        self.target_combo.setCurrentIndex(self.target_combo.findData(source))

    def add_transfer_line(self):
        product = self.transfer_product.currentData()
        if not product:
            return
        quantity = int(self.transfer_quantity.value())
        existing = next(
            (line for line in self.transfer_lines if line["part_id"] == product["part_id"]),
            None,
        )
        if existing:
            existing["quantity"] += quantity
        else:
            self.transfer_lines.append(
                {
                    "part_id": product["part_id"],
                    "name": product["name"],
                    "unit": product.get("unit") or "Adet",
                    "quantity": quantity,
                }
            )
        self.render_transfer_lines()

    def add_transfer_kit(self):
        kit_id = self.transfer_kit.currentData()
        if not kit_id:
            return
        for kit_line in self.db.get_stock_kit_lines(kit_id):
            existing = next(
                (
                    line
                    for line in self.transfer_lines
                    if line["part_id"] == kit_line["part_id"]
                ),
                None,
            )
            if existing:
                existing["quantity"] += float(kit_line["quantity"])
            else:
                self.transfer_lines.append(
                    {
                        "part_id": kit_line["part_id"],
                        "name": kit_line["name"],
                        "unit": kit_line.get("unit") or "Adet",
                        "quantity": float(kit_line["quantity"]),
                    }
                )
        self.render_transfer_lines()

    def add_kit_line(self):
        product = self.kit_product.currentData()
        if not product:
            return
        quantity = int(self.kit_quantity.value())
        existing = next(
            (line for line in self.kit_lines if line["part_id"] == product["part_id"]),
            None,
        )
        if existing:
            existing["quantity"] += quantity
        else:
            self.kit_lines.append(
                {
                    "part_id": product["part_id"],
                    "name": product["name"],
                    "quantity": quantity,
                }
            )
        self.render_kit_lines()

    def render_kit_lines(self):
        self.kit_table.setRowCount(len(self.kit_lines))
        self.kit_table.verticalHeader().setDefaultSectionSize(46)
        for row, line in enumerate(self.kit_lines):
            self.kit_table.setItem(row, 0, _item(line["name"]))
            self.kit_table.setItem(row, 1, _item(f"{line['quantity']:g}", alignment=Qt.AlignmentFlag.AlignCenter))
            
            btn_remove = QPushButton("Sil")
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove.setFixedSize(70, 28)
            btn_remove.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #EF4444;
                }
            """)
            btn_remove.clicked.connect(lambda _checked=False, index=row: self.remove_kit_line(index))

            btn_container = QWidget()
            btn_lay = QHBoxLayout(btn_container)
            btn_lay.setContentsMargins(0, 0, 0, 0)
            btn_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_lay.addWidget(btn_remove)

            self.kit_table.setCellWidget(row, 2, btn_container)

    def remove_kit_line(self, index):
        if 0 <= index < len(self.kit_lines):
            self.kit_lines.pop(index)
            self.render_kit_lines()

    def save_kit(self):
        if not self.kit_name.text().strip():
            QMessageBox.warning(self, "Hazır Kit", "Lütfen kit adını girin.")
            return
        try:
            self.db.save_stock_kit(self.kit_name.text(), self.kit_lines)
            self.kit_name.clear()
            self.kit_lines.clear()
            self.kit_table.setRowCount(0)
            self.refresh_data()
            QMessageBox.information(self, "Hazır Kit", "Kit başarıyla kaydedildi.")
        except Exception as exc:
            QMessageBox.warning(self, "Hazır Kit", str(exc))

    def render_transfer_lines(self):
        self.transfer_table.setRowCount(len(self.transfer_lines))
        self.transfer_table.verticalHeader().setDefaultSectionSize(46)
        for row, line in enumerate(self.transfer_lines):
            self.transfer_table.setItem(row, 0, _item(line["name"]))
            self.transfer_table.setItem(row, 1, _badge_item(line["unit"], "#E0E7FF", "#3730A3"))
            self.transfer_table.setItem(row, 2, _item(f"{line['quantity']:g}", alignment=Qt.AlignmentFlag.AlignCenter))
            
            btn_remove = QPushButton("Kaldır")
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove.setFixedSize(75, 28)
            btn_remove.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #EF4444;
                }
            """)
            btn_remove.clicked.connect(lambda _checked=False, index=row: self.remove_transfer_line(index))

            btn_container = QWidget()
            btn_lay = QHBoxLayout(btn_container)
            btn_lay.setContentsMargins(0, 0, 0, 0)
            btn_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_lay.addWidget(btn_remove)

            self.transfer_table.setCellWidget(row, 3, btn_container)

    def remove_transfer_line(self, index):
        if 0 <= index < len(self.transfer_lines):
            self.transfer_lines.pop(index)
            self.render_transfer_lines()

    def save_transfer(self):
        if not self.transfer_lines:
            QMessageBox.warning(self, "Transfer", "Lütfen transfer edilecek en az bir ürün ekleyin.")
            return
        try:
            _transfer_id, reference = self.db.transfer_stock(
                self.source_combo.currentData(),
                self.target_combo.currentData(),
                self.transfer_lines,
                self.transfer_note.text(),
                self._actor_name(),
            )
            QMessageBox.information(
                self, "Transfer Tamamlandı", f"Transfer başarıyla yapıldı.\nReferans No: {reference}"
            )
            self.transfer_lines.clear()
            self.transfer_note.clear()
            self.render_transfer_lines()
            self.refresh_data()
        except Exception as exc:
            QMessageBox.warning(self, "Transfer Yapılamadı", str(exc))

    def _get_count_editor_from_cell(self, row, col=2):
        widget = self.count_table.cellWidget(row, col)
        if not widget:
            return None
        if isinstance(widget, (QDoubleSpinBox, QLineEdit)):
            return widget
        if hasattr(widget, "spn_counted"):
            return widget.spn_counted
        return widget.findChild(QLineEdit) or widget.findChild(QDoubleSpinBox)

    def load_count(self):
        location_id = self.count_location.currentData()
        if not location_id:
            return
        rows = self.db.get_location_inventory(location_id)
        visible = [row for row in rows if abs(float(row["quantity"])) > 0.000001]
        self.count_table.setRowCount(len(visible))
        self.count_table.verticalHeader().setDefaultSectionSize(42)
        for row_index, row in enumerate(visible):
            expected = float(row["quantity"])
            unit = row.get("unit") or "Adet"
            self.count_table.setItem(row_index, 0, _item(row["name"], row["part_id"]))
            self.count_table.setItem(row_index, 1, _item(f"{expected:g}", alignment=Qt.AlignmentFlag.AlignCenter))

            stepper = CountStepper(expected, 3 if unit in ("Metre", "Kg", "Lt") else 0)
            stepper.spn_counted.textChanged.connect(
                lambda _value, current_row=row_index: self.update_count_difference(current_row)
            )
            self.count_table.setCellWidget(row_index, 2, stepper)
            self.count_table.setItem(row_index, 3, _badge_item("0", "#DCFCE7", "#166534"))

    def update_count_difference(self, row):
        expected_item = self.count_table.item(row, 1)
        counted = self._get_count_editor_from_cell(row, 2)
        if expected_item and counted:
            difference = float(counted.value()) - float(expected_item.text())
            if difference == 0:
                self.count_table.setItem(row, 3, _badge_item("0", "#DCFCE7", "#166534"))
            elif difference < 0:
                self.count_table.setItem(row, 3, _badge_item(f"{difference:g}", "#FEE2E2", "#991B1B"))
            else:
                self.count_table.setItem(row, 3, _badge_item(f"+{difference:g}", "#DBEAFE", "#1E40AF"))

    def save_count(self):
        lines = []
        for row in range(self.count_table.rowCount()):
            product = self.count_table.item(row, 0)
            counted = self._get_count_editor_from_cell(row, 2)
            if product and counted:
                lines.append(
                    {
                        "part_id": product.data(Qt.ItemDataRole.UserRole),
                        "counted_quantity": counted.value(),
                    }
                )
        if not lines:
            QMessageBox.warning(self, "Sayım", "Sayılacak stok bulunamadı.")
            return
        answer = QMessageBox.question(
            self,
            "Sayımı Onayla",
            "Sayım farkları konum ve toplam stok bakiyesine işlenecek. Devam edilsin mi?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.save_stock_count(
                self.count_location.currentData(), lines, self.count_note.text(), self._actor_name()
            )
            QMessageBox.information(self, "Sayım", "Sayım kaydedildi.")
            self.count_note.clear()
            self.refresh_data()
        except Exception as exc:
            QMessageBox.warning(self, "Sayım Kaydedilemedi", str(exc))

    def load_history(self):
        rows = self.db.get_stock_transfer_history()
        self.history_table.setRowCount(len(rows))

        if hasattr(self, "card_hareket"):
            lbl = self.card_hareket.findChildren(QLabel)[-1]
            lbl.setText(str(len(rows)))

        for row_index, row in enumerate(rows):
            note = str(row.get("note") or "-")
            note = note.replace("Appointment load", "Randevu araca yukleme")
            note = note.replace("Appointment return", "Randevu iade")
            values = [
                row["reference_no"], row["source_name"], row["target_name"],
                row.get("product_names") or "-", row["line_count"],
                f"{float(row['total_quantity']):g}", note,
                row["created_at"],
            ]
            for column, value in enumerate(values):
                if column == 0:
                    self.history_table.setItem(row_index, column, _badge_item(value, "#E0E7FF", "#3730A3"))
                elif column == 5:
                    self.history_table.setItem(row_index, column, _item(value, alignment=Qt.AlignmentFlag.AlignCenter))
                else:
                    self.history_table.setItem(row_index, column, _item(value))
