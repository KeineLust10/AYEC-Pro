# -*- coding: utf-8 -*-

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_colors import qc, theme_qss
from src.utils.role_utils import is_admin_role

SIDEBAR_BG = "@surface_alt"
SIDEBAR_TEXT = "@text"
SIDEBAR_HOVER = "@surface"
SIDEBAR_ACTIVE = "@selection_bg"
SIDEBAR_ACTIVE_TEXT = "@selection_text"
BORDER_COLOR = "@border"


class PremiumSettingsSidebar(QWidget):
    """Sol tarafta yer alan kategorili ayarlar menusu."""

    def __init__(self, item_callback, db=None, current_user=None, parent=None):
        super().__init__(parent)
        self.item_callback = item_callback
        self.db = db
        self.current_user = dict(current_user or {})
        self.items_map = []
        self.setFixedWidth(280)
        self.apply_theme_styles()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.header_label = QLabel("Ayarlar")
        self.header_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.header_label.setStyleSheet(theme_qss("color: @text; margin: 25px 0 10px 20px; border: none;"))
        self.layout.addWidget(self.header_label)

        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("Ayarlarda ara...")
        self.search_inp.textChanged.connect(self.filter_items)
        self.layout.addWidget(self.search_inp)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.handle_row_change)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.layout.addWidget(self.list_widget)

        self.init_menu_items()
        self.apply_theme_styles()

    def _is_classic_appearance(self):
        app = QApplication.instance()
        if app and app.property("appearanceMode") == "classic":
            return True
        try:
            return AppearanceModeManager.is_classic(self.db)
        except Exception:
            return False

    def _set_classic_transform_guard(self, classic):
        widgets = [self]
        for name in ("header_label", "search_inp", "list_widget"):
            widget = getattr(self, name, None)
            if widget is not None:
                widgets.append(widget)
        for widget in widgets:
            widget.setProperty("skipThemeTransform", False)

    def _sidebar_qss(self):
        if self._is_classic_appearance():
            return """
            QWidget {
                background-color: #F3F4F6;
                border-right: 1px solid #B8C0CC;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #AEB4BD;
                border-radius: 0px;
                padding: 5px 8px;
                font-size: 12px;
                margin: 10px 10px 4px 10px;
                color: #111827;
                min-height: 24px;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
                margin-top: 4px;
            }
            QListWidget::item {
                height: 32px;
                padding-left: 10px;
                color: #111827;
                background-color: transparent;
                border-radius: 0px;
                margin: 1px 8px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QListWidget::item:!selected:hover {
                background-color: #EEF2F7;
                color: #111827;
                border: 1px solid #CBD5E1;
            }
            QListWidget::item:selected,
            QListWidget::item:selected:active {
                background-color: #DCEBFF;
                color: #111827;
                font-weight: 700;
                border: 1px solid #8FA3BD;
            }
            QListWidget::item:disabled {
                background-color: transparent;
                color: #4B5563;
                border: none;
            }
            """
        return theme_qss(
            f"""
            QWidget {{
                background-color: {SIDEBAR_BG};
                border-right: 1px solid {BORDER_COLOR};
            }}
            QLineEdit {{
                background-color: @surface;
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 8px 30px 8px 10px;
                font-size: 13px;
                margin: 15px 15px 5px 15px;
                color: @text;
            }}
            QLineEdit:focus {{
                border-color: {SIDEBAR_ACTIVE_TEXT};
            }}
            QListWidget {{
                border: none;
                background-color: transparent;
                outline: none;
                margin-top: 5px;
            }}
            QListWidget::item {{
                height: 40px;
                padding-left: 15px;
                color: {SIDEBAR_TEXT};
                border-radius: 6px;
                margin: 2px 10px;
                font-family: 'Segoe UI';
                font-size: 14px;
            }}
            QListWidget::item:hover {{
                background-color: {SIDEBAR_HOVER};
            }}
            QListWidget::item:selected {{
                background-color: {SIDEBAR_ACTIVE};
                color: {SIDEBAR_ACTIVE_TEXT};
                font-weight: 600;
            }}
            """
        )

    def apply_theme_styles(self):
        classic = self._is_classic_appearance()
        self._set_classic_transform_guard(classic)
        self.setStyleSheet(self._sidebar_qss())
        if hasattr(self, "header_label"):
            self.header_label.setFont(QFont("Segoe UI", 12 if classic else 18, QFont.Weight.Bold))
            self.header_label.setStyleSheet(
                "color: #111827; margin: 14px 0 8px 14px; border: none; background: transparent;"
                if classic
                else theme_qss("color: @text; margin: 25px 0 10px 20px; border: none;")
            )
        if classic and hasattr(self, "list_widget"):
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if i < len(self.items_map) and self.items_map[i] is None:
                    item.setForeground(QColor("#4B5563"))
                else:
                    item.setForeground(QColor("#111827"))

    def init_menu_items(self):
        """Menu ogelerini kategorilere gore ekle."""
        structure = [
            ("GENEL", [
                ("🏢", "Firma Ayarlari", 4),
                ("🌐", "Dil, Tarih & Para Birimi", 9),
                ("%", "KDV & Kur Senkronizasyonu", 25),
                ("🎨", "Temalar & Yazi Tipi", 6),
            ]),
            ("ENTEGRASYONLAR & API", [
                ("🔌", "Entegrasyonlar & API", 21),
            ]),
            ("TICARI & LISTELER", [
                ("🚚", "Kargo Firmalari", 5),
                ("✏️", "Hizli Not Yonetimi", 14),
                ("📦", "Stok Ayarlari", 12),
            ]),
            ("GUVENLIK & SISTEM", [
                ("💾", "Yedekleme ve Veri Merkezi", 7),
                ("👥", "Kullanici Yonetimi", 19),
                ("\U0001f5a5", "Y\u00f6netim Merkezi", 24),
                ("🛡️", "Lisans Durumu", 10),
                ("🔒", "Guvenlik Ayarlari (Sifre)", 11),
                ("📜", "Sistem Islem Loglari (Audit)", 17),
            ]),
            ("UZAK BAGLANTI", [
                ("🖥️", "AYEC Pro (Uzak)", 18),
            ]),
            ("SISTEM YAPISI", [
                ("⚙️", "Sistem Kimligi & Moduler Yapi", 22),
            ]),
        ]

        self.items_map = []
        self.list_widget.clear()

        for category, items in structure:
            cat_item = QListWidgetItem(category)
            cat_item.setFlags(Qt.ItemFlag.NoItemFlags)
            cat_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            cat_item.setForeground(QColor("#4B5563") if self._is_classic_appearance() else qc("disabled_text"))
            cat_item.setSizeHint(QSize(200, 45))
            cat_item.setTextAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
            self.list_widget.addItem(cat_item)
            self.items_map.append(None)

            for icon, text, idx in items:
                if idx == 24 and not is_admin_role(self.current_user.get("role")):
                    continue
                display_text = text
                if hasattr(self, 'db') and self.db:
                    custom_text = self.db.get_setting(f"menu_label_{idx}", text)
                    display_text = str(custom_text or "").strip() or text
                item = QListWidgetItem(f"   {icon}   {display_text}")
                item.setData(Qt.ItemDataRole.UserRole, idx)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.list_widget.addItem(item)
                self.items_map.append(idx)

    def iter_items(self):
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            page_id = self.items_map[i] if i < len(self.items_map) else None
            if page_id is None:
                continue
            text = item.text().strip()
            parts = [p for p in text.split("   ") if p.strip()]
            title = parts[-1] if parts else text
            items.append({"row": i, "page_id": page_id, "title": title})
        return items

    def handle_row_change(self, row):
        if row < 0 or row >= len(self.items_map):
            return
        idx = self.items_map[row]
        if idx is not None:
            self.item_callback(idx)

    def filter_items(self, text):
        text = text.lower()
        count = self.list_widget.count()

        for i in range(count):
            item = self.list_widget.item(i)
            if not (item.flags() & Qt.ItemFlag.NoItemFlags):
                item.setHidden(bool(text) and text not in item.text().lower())

        i = 0
        while i < count:
            item = self.list_widget.item(i)
            if item.flags() & Qt.ItemFlag.NoItemFlags:
                has_visible_child = False
                j = i + 1
                while j < count:
                    child = self.list_widget.item(j)
                    if child.flags() & Qt.ItemFlag.NoItemFlags:
                        break
                    if not child.isHidden():
                        has_visible_child = True
                        break
                    j += 1
                item.setHidden(bool(text) and not has_visible_child)
            i += 1


class PlaceholderWidget(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"{title}\n(Bu modül yapım aşamasındadır)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet(theme_qss("color: @text_muted;"))
        layout.addWidget(lbl)
