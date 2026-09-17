from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QFrame, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger


class GlobalSearchDialog(ModernDialog):
    """
    Spotlight / Command Palette stili global arama.
    Kisayol: CTRL + K
    """

    def __init__(self, parent, db, navigation_callback):
        super().__init__(title="Global Arama", parent=parent, width=600, height=400)
        self.db = db
        self.nav_callback = navigation_callback
        self.set_footer_visible(False)
        self.init_ui()

    def init_ui(self):
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setStyleSheet(
            """
            QFrame {
                background-color: #1e293b;
                border: 1px solid #34495e;
                border-radius: 15px;
            }
            """
        )
        self.content_layout.addWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Gitmek istediginiz yer, musteri veya islem... (Menu, Musteri, Stok)")
        self.search_box.setFont(QFont("Segoe UI", 14))
        self.search_box.setStyleSheet(
            """
            QLineEdit {
                background-color: #34495e;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                selection-background-color: #F59E0B;
            }
            """
        )
        self.search_box.textChanged.connect(self.on_search)
        layout.addWidget(self.search_box)

        self.result_list = QListWidget()
        self.result_list.setStyleSheet(
            """
            QListWidget {
                background-color: transparent;
                border: none;
                color: #ecf0f1;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #F59E0B;
                color: white;
            }
            """
        )
        self.result_list.itemActivated.connect(self.on_item_activated)
        layout.addWidget(self.result_list)

        footer = QLabel("Secmek icin [ENTER], kapatmak icin [ESC]")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #95a5a6; font-size: 10px;")
        layout.addWidget(footer)

        self.menu_items = [
            ("Ana Sayfa", 40, "page"),
            ("Servis Takip", 41, "page"),
            ("Musteri Listesi", 21, "page"),
            ("Stok Listesi", 999, "page"),
            ("Gelir / Gider", 101, "page"),
            ("Ayarlar", 130, "page"),
            ("Duyurular", 120, "page"),
            ("Saha Servisi", 141, "page"),
        ]

    def on_search(self, text):
        self.result_list.clear()
        if not text or len(text) < 2:
            return

        text = text.lower()

        for label, idx, type_ in self.menu_items:
            if text in label.lower():
                self.add_result(label, "Sayfaya Git", idx, type_)

        try:
            customers = self.db.search_customer(text)
            if not hasattr(self.db, "search_customer"):
                all_customers = self.db.get_customers()
                customers = [customer for customer in all_customers if text in str(customer[1]).lower()]
            for customer in customers[:5]:
                self.add_result(customer[1], f"Musteri Detayina Git ({customer[2]})", customer[0], "customer")
        except Exception as exc:
            logger.debug(f"Global search customer lookup failed: {exc}")

        try:
            stocks = self.db.get_stock_items()
            filtered_stocks = [stock for stock in stocks if text in stock["name"].lower()]
            for stock in filtered_stocks[:5]:
                self.add_result(
                    stock["name"],
                    f"Stok: {stock['quantity']} Adet | "
                    f"{CurrencyHelper.format_try_for_display(stock['price_sell'], db=self.db, include_try_reference=False)}",
                    999,
                    "stock",
                )
        except Exception as exc:
            logger.debug(f"Global search stock lookup failed: {exc}")

        if self.result_list.count() > 0:
            self.result_list.setCurrentRow(0)

    def add_result(self, title, subtitle, data, type_):
        item = QListWidgetItem()
        base_role = int(Qt.ItemDataRole.UserRole)
        item.setData(base_role, data)
        item.setData(base_role + 1, type_)

        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(5, 5, 5, 5)
        vbox.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: white;")

        lbl_sub = QLabel(subtitle)
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet("color: #bdc3c7;")

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_sub)

        item.setSizeHint(QSize(0, 55))
        self.result_list.addItem(item)
        self.result_list.setItemWidget(item, widget)

    def on_item_activated(self, item):
        base_role = int(Qt.ItemDataRole.UserRole)
        data = item.data(base_role)
        type_ = item.data(base_role + 1)

        self.close()

        if type_ in {"page", "stock"}:
            self.nav_callback(data)
        elif type_ == "customer":
            self.nav_callback(21)
