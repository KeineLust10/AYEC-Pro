# -*- coding: utf-8 -*-

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout, QWidget, QFrame, QPushButton, QStyledItemDelegate, QStyleOptionViewItem, QStyle

from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_colors import qc, theme_qss
from src.utils.role_utils import is_admin_role
from src.ui.widgets.navigation_glyph import navigation_icon
from src.utils.design_system import DesignTokens
from src.utils.reference_typography import load_reference_fonts

SETTINGS_GLYPHS = {
    4: 'building', 9: 'globe', 25: 'percent', 6: 'palette', 21: 'plug', 20: 'plug', 16: 'plug',
    5: 'truck', 14: 'pencil', 12: 'box', 7: 'save', 19: 'people',
    24: 'monitor', 10: 'shield', 11: 'lock', 17: 'document',
    18: 'monitor', 22: 'settings',
}


class _SettingsNavigationDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        is_category = index.data(Qt.ItemDataRole.UserRole) == 'category'
        if not is_category:
            opt.rect.adjust(14, 0, 0, 0)
        super().paint(painter, opt, index)
        if not is_category and option.state & QStyle.StateFlag.State_Selected:
            painter.save()
            painter.setPen(qc('accent'))
            painter.drawLine(opt.rect.left(), opt.rect.top() + 4,
                             opt.rect.left(), opt.rect.bottom() - 4)
            painter.restore()

SIDEBAR_BG = "@window"
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
        self._category_rows = {}
        self._category_expanded = {}
        self._active_page_id = None
        self.setFixedWidth(274)
        self.apply_theme_styles()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.header_label = QLabel("Ayarlar")
        self.header_label.setFont(QFont(self._ui_font_family(), 18, QFont.Weight.Bold))
        self.header_label.setStyleSheet(theme_qss("color: @text; margin: 25px 0 10px 20px; border: none;"))
        self.header_label.hide()

        self.profile_card = QFrame()
        self.profile_card.setObjectName("SettingsProfileCard")
        self.profile_card.setFixedHeight(76)
        self.profile_card.setStyleSheet(theme_qss(
            "QFrame#SettingsProfileCard { background: @finance_surface; "
            "border: 1px solid @finance_outline; border-radius: 14px; }"
        ))
        profile_layout = QHBoxLayout(self.profile_card)
        profile_layout.setContentsMargins(8, 8, 8, 8)
        profile_layout.setSpacing(8)
        self.profile_avatar = QLabel("\U0001f464")
        self.profile_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.profile_avatar.setFixedSize(44, 44)
        self.profile_avatar.setPixmap(navigation_icon("person", 28, "accent").pixmap(QSize(28, 28)))
        self.profile_avatar.setStyleSheet(theme_qss(
            "background: @finance_active_bg; color: @accent; border: 1px solid @finance_outline; "
            "border-radius: 14px; font-size: 20px;"
        ))
        profile_layout.addWidget(self.profile_avatar, 0, Qt.AlignmentFlag.AlignVCenter)
        profile_text = QVBoxLayout()
        profile_text.setSpacing(4)
        profile_name = str(self.current_user.get("name") or self.current_user.get("username") or "AYEC Pro")
        profile_title = QLabel(profile_name)
        profile_title.setStyleSheet(theme_qss("color: @text; background: transparent; border: none; font-size: 13px; font-weight: 700;"))
        company_name = str(self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro") if self.db else "AYEC Pro"
        profile_company = QLabel(company_name)
        profile_company.setStyleSheet(theme_qss("color: @text_muted; background: transparent; border: none; font-size: 10px;"))
        profile_mode = QLabel("TEKN\u0130K SERV\u0130S MODU")
        profile_mode.setStyleSheet(theme_qss(
            "color: @accent; background: @finance_surface_alt; border: 1px solid @finance_outline; "
            "border-radius: 5px; padding: 3px 6px; font-size: 10px; font-weight: 700;"
        ))
        profile_text.addWidget(profile_title)
        profile_text.addWidget(profile_company)
        profile_text.addWidget(profile_mode, 0, Qt.AlignmentFlag.AlignLeft)
        profile_layout.addLayout(profile_text, 1)
        profile_host = QWidget(self)
        profile_host.setFixedHeight(104)
        profile_host_layout = QHBoxLayout(profile_host)
        profile_host_layout.setContentsMargins(15, 14, 15, 14)
        profile_host_layout.addWidget(self.profile_card)
        self.layout.addWidget(profile_host)

        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("Ayarlarda ara...")
        self.search_inp.textChanged.connect(self.filter_items)
        self.layout.addWidget(self.search_inp)

        self.list_widget = QListWidget()
        self.list_widget.setItemDelegate(_SettingsNavigationDelegate(self.list_widget))
        self.list_widget.setIconSize(QSize(16, 16))
        self.list_widget.currentRowChanged.connect(self.handle_row_change)
        self.list_widget.itemClicked.connect(self._handle_item_click)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.layout.addWidget(self.list_widget)

        self.footer = QFrame()
        self.footer.setStyleSheet(theme_qss("QFrame { background: @window; border-top: 1px solid @border; }"))
        footer_layout = QVBoxLayout(self.footer)
        footer_layout.setContentsMargins(14, 10, 14, 12)
        footer_layout.setSpacing(8)
        footer_actions = QHBoxLayout()
        footer_actions.setSpacing(8)
        service_button = QPushButton("Teknik Servis")
        version_button = QPushButton("v2.0.4 Premium")
        for button in (service_button, version_button):
            button.setFixedHeight(34)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: @surface; color: @text; border: 1px solid @border; "
                "border-radius: 6px; font-size: 11px; font-weight: 600; }"
            ))
        version_button.setStyleSheet(theme_qss(
            "QPushButton { background: @finance_surface_alt; color: @accent; border: 1px solid @finance_outline; "
            "border-radius: 6px; font-size: 11px; font-weight: 600; }"
        ))
        service_button.setEnabled(False)
        version_button.setEnabled(False)
        footer_actions.addWidget(service_button, 1)
        footer_actions.addWidget(version_button, 1)
        footer_layout.addLayout(footer_actions)
        self.logout_button = QPushButton("Oturumu Kapat")
        self.logout_button.setFixedHeight(38)
        self.logout_button.setStyleSheet(theme_qss(
            "QPushButton { background: @finance_action_expense_bg; color: @danger; "
            "border: 1px solid @finance_action_expense; border-radius: 6px; font-weight: 600; }"
        ))
        self.logout_button.clicked.connect(self._request_logout)
        footer_layout.addWidget(self.logout_button)
        self.layout.addWidget(self.footer)

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

    def _request_logout(self):
        main_window = self.window()
        handler = getattr(main_window, "handle_logout_requested", None)
        if callable(handler):
            handler()

    def set_embedded(self, embedded, width=244):
        self._embedded = bool(embedded)
        self.setFixedWidth(width if embedded else 274)
        self.header_label.hide()
        self.profile_card.setVisible(not embedded)
        self.footer.setVisible(not embedded)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        if embedded:
            self.list_widget.setMinimumHeight(0)
            self.list_widget.setMaximumHeight(16777215)
        else:
            self.list_widget.setMinimumHeight(0)
            self.list_widget.setMaximumHeight(16777215)

    def _refresh_embedded_geometry(self):
        if not getattr(self, "_embedded", False):
            return
        height = sum(max(36, self.list_widget.sizeHintForRow(row))
                     for row in range(self.list_widget.count())
                     if not self.list_widget.item(row).isHidden())
        margins = self.list_widget.contentsMargins()
        self.list_widget.setFixedHeight(height + margins.top() + margins.bottom() + 2 * self.list_widget.frameWidth() + 8)
        self.updateGeometry()

    @staticmethod
    def _ui_font_family():
        load_reference_fonts()
        return DesignTokens.FONT_NAME

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
                margin: 0 13px 5px 13px;
                color: @text;
            }}
            QLineEdit:focus {{
                border-color: {SIDEBAR_ACTIVE_TEXT};
            }}
            QListWidget {{
                border: none;
                background-color: transparent;
                outline: none;
                margin-top: 8px;
            }}
            QListWidget::item {{
                height: 40px;
                padding-left: 15px;
                color: {SIDEBAR_TEXT};
                border-radius: 8px;
                margin: 2px 8px;
                font-family: '{self._ui_font_family()}';
                font-size: 13px;
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
            self.header_label.setFont(QFont("Segoe UI" if classic else self._ui_font_family(), 12 if classic else 18, QFont.Weight.Bold))
            self.header_label.setStyleSheet(
                "color: #111827; margin: 14px 0 8px 14px; border: none; background: transparent;"
                if classic
                else theme_qss(
                    "color: @text; background: transparent; padding: 2px 0; "
                    "margin: 20px 0 10px 14px; border: none;"
                )
            )
        if classic and hasattr(self, "list_widget"):
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if i < len(self.items_map) and self.items_map[i] is None:
                    item.setForeground(QColor("#4B5563"))
                else:
                    item.setForeground(QColor("#111827"))
        if hasattr(self, "list_widget"):
            self._refresh_navigation_icons()

    def _refresh_navigation_icons(self):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            page_id = item.data(Qt.ItemDataRole.UserRole)
            if page_id == 'category':
                expanded = self._category_expanded.get(row, True)
                contains_active = any(self.items_map[child] == self._active_page_id
                                      for child in self._category_rows.get(row, []))
                token = 'accent' if contains_active else 'text_muted'
                item.setForeground(qc(token))
                item.setIcon(navigation_icon('chevron_down' if expanded else 'chevron_right',
                                             normal_token=token))
            elif page_id in SETTINGS_GLYPHS:
                item.setIcon(navigation_icon(SETTINGS_GLYPHS[page_id]))

    def init_menu_items(self):
        """Menu ogelerini kategorilere gore ekle."""
        structure = [
            ("GENEL", [
                ("building", "Firma Ayarlari", 4),
                ("globe", "Dil, Tarih & Para Birimi", 9),
                ("percent", "KDV & Kur Senkronizasyonu", 25),
                ("palette", "Temalar & Yazi Tipi", 6),
            ]),
            ("ENTEGRASYONLAR & API", [
                ("plug", "Entegrasyonlar & API", 21),
                ("plug", "WhatsApp Entegrasyonu", 20),
                ("plug", "Telegram Bot", 16),
            ]),
            ("TICARI & LISTELER", [
                ("truck", "Kargo Firmalari", 5),
                ("pencil", "Hizli Not Yonetimi", 14),
                ("box", "Stok Ayarlari", 12),
            ]),
            ("GUVENLIK & SISTEM", [
                ("save", "Yedekleme ve Veri Merkezi", 7),
                ("people", "Kullanici Yonetimi", 19),
                ("monitor", "Y\u00f6netim Merkezi", 24),
                ("shield", "Lisans Durumu", 10),
                ("lock", "Guvenlik Ayarlari (Sifre)", 11),
                ("document", "Sistem Islem Loglari (Audit)", 17),
            ]),
            ("UZAK BAGLANTI", [
                ("monitor", "AYEC Pro (Uzak)", 18),
            ]),
            ("SISTEM YAPISI", [
                ("settings", "Sistem Kimligi & Moduler Yapi", 22),
            ]),
        ]

        self.items_map = []
        self._category_rows = {}
        self._category_expanded = {}
        self.list_widget.clear()

        for category, items in structure:
            category_row = self.list_widget.count()
            cat_item = QListWidgetItem(category)
            cat_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            cat_item.setData(Qt.ItemDataRole.UserRole, "category")
            cat_item.setFont(QFont(self._ui_font_family(), 9, QFont.Weight.Bold))
            cat_item.setForeground(QColor("#4B5563") if self._is_classic_appearance() else qc("disabled_text"))
            cat_item.setSizeHint(QSize(200, 36))
            cat_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.list_widget.addItem(cat_item)
            self.items_map.append(None)
            child_rows = []

            for kind, text, idx in items:
                if idx == 24 and not is_admin_role(self.current_user.get("role")):
                    continue
                display_text = text
                if hasattr(self, 'db') and self.db:
                    custom_text = self.db.get_setting(f"menu_label_{idx}", text)
                    display_text = str(custom_text or "").strip() or text
                item = QListWidgetItem(display_text)
                item.setToolTip(display_text)
                item.setSizeHint(QSize(200, 50))
                item.setData(Qt.ItemDataRole.UserRole, idx)
                item.setData(Qt.ItemDataRole.UserRole + 1, kind)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.list_widget.addItem(item)
                self.items_map.append(idx)
                child_rows.append(self.list_widget.count() - 1)
            self._category_rows[category_row] = child_rows
            self._category_expanded[category_row] = True
        self._refresh_navigation_icons()

    def iter_items(self):
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            page_id = self.items_map[i] if i < len(self.items_map) else None
            if page_id is None:
                continue
            text = item.text().strip()
            items.append({"row": i, "page_id": page_id, "title": text})
        return items

    def handle_row_change(self, row):
        if row < 0 or row >= len(self.items_map):
            return
        idx = self.items_map[row]
        if idx is not None:
            self._active_page_id = idx
            self._refresh_navigation_icons()
            self.item_callback(idx)

    def _handle_item_click(self, item):
        row = self.list_widget.row(item)
        if row in self._category_rows:
            self._toggle_category(row)

    def _toggle_category(self, category_row):
        expanded = not self._category_expanded.get(category_row, True)
        self._category_expanded[category_row] = expanded
        for child_row in self._category_rows.get(category_row, []):
            self.list_widget.item(child_row).setHidden(not expanded)
        self.list_widget.clearSelection()
        self._refresh_navigation_icons()
        self._restore_active_selection()

        self._refresh_embedded_geometry()

    def _restore_active_selection(self):
        for row, page_id in enumerate(self.items_map):
            if page_id == self._active_page_id and page_id is not None:
                if not self.list_widget.item(row).isHidden():
                    previous = self.list_widget.blockSignals(True)
                    try:
                        self.list_widget.setCurrentRow(row)
                    finally:
                        self.list_widget.blockSignals(previous)
                return

    def filter_items(self, text):
        text = text.lower()
        count = self.list_widget.count()

        for i in range(count):
            item = self.list_widget.item(i)
            if i not in self._category_rows:
                item.setHidden(bool(text) and text not in item.text().lower())

        i = 0
        while i < count:
            item = self.list_widget.item(i)
            if i in self._category_rows:
                has_visible_child = False
                for child_row in self._category_rows[i]:
                    child = self.list_widget.item(child_row)
                    if not child.isHidden() and child_row < count:
                        has_visible_child = True
                        break
                item.setHidden(bool(text) and not has_visible_child)
                if text:
                    for child_row in self._category_rows[i]:
                        self.list_widget.item(child_row).setHidden(text not in self.list_widget.item(child_row).text().lower())
                else:
                    for child_row in self._category_rows[i]:
                        self.list_widget.item(child_row).setHidden(not self._category_expanded.get(i, True))
            i += 1
        self._restore_active_selection()

        self._refresh_embedded_geometry()


class PlaceholderWidget(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"{title}\n(Bu modül yapım aşamasındadır)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont(DesignTokens.FONT_NAME, 14, QFont.Weight.Bold))
        lbl.setStyleSheet(theme_qss("color: @text_muted;"))
        layout.addWidget(lbl)
