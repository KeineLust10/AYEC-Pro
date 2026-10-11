# -*- coding: utf-8 -*-

# VoiceAssistantShortcutsWidget - Separate file for shortcuts
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFrame, QComboBox, QTableView, QAbstractItemView, 
                             QHeaderView, QSizePolicy, QDialog, QFormLayout, QMenu, QTextEdit,
                             QStyledItemDelegate, QStyleOptionViewItem)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, QPoint, QTimer, QRectF
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction, QCursor, QPainter
import os
import json

from src.utils.theme_colors import theme_qss, qc
from src.utils.toast_notification import show_success, show_error
from src.utils.design_system import DesignTokens
from src.utils.path_helper import PathHelper
from src.utils.logger import logger
from src.utils.context_menu_settings import is_context_menu_enabled
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.user_permission_catalog import USER_PERMISSION_SECTIONS


class AutoPopupComboBox(QComboBox):
    """ComboBox that auto-opens popup on any click"""
    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and not self.view().isVisible():
            QTimer.singleShot(0, self.showPopup)


class ShortcutEditDialog(ModernDialog):
    """Native shortcut editor with shared persistent actions."""
    def __init__(self, shortcut_name="", triggers="", action_type="", action="", parent=None):
        super().__init__("Kestirme D\u00fczenle" if shortcut_name else "Yeni Kestirme", parent, width=620, height=420)
        self.setModal(True)
        content_layout = self.content_layout
        
        # Form
        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Shortcut Name
        self.inp_name = QLineEdit(shortcut_name)
        self.inp_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_name.setPlaceholderText("\u00f6rn: stok_sorgu")
        form.addRow("Kestirme Ad\u0131:", self.inp_name)
        
        # Triggers
        self.inp_triggers = QTextEdit()
        self.inp_triggers.setPlainText(triggers)
        self.inp_triggers.setMaximumHeight(100)
        self.inp_triggers.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_triggers.setPlaceholderText("stoklar, stok, sto\u011fa bak, envanter (virg\u00fclle ay\u0131r\u0131n)")
        form.addRow("Tetikleyici Komutlar:", self.inp_triggers)
        
        # Action Type
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Sayfa", "Fonksiyon", "Aksiyon"])
        self.cmb_type.setCurrentText(action_type if action_type != "Ba\u011flant\u0131 Yok" else "Sayfa")
        self.cmb_type.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.cmb_type.currentTextChanged.connect(self._update_action_options)
        form.addRow("\u0130\u015flem T\u00fcr\u00fc:", self.cmb_type)
        
        # Action - Auto-popup ComboBox
        self.cmb_action = AutoPopupComboBox()
        self.cmb_action.setEditable(True)
        self.cmb_action.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        form.addRow("Aksiyon:", self.cmb_action)
        
        # Populate action options based on type
        self._update_action_options(self.cmb_type.currentText())
        if action:
            self.cmb_action.setCurrentText(action)
        
        content_layout.addLayout(form)
        content_layout.addStretch()
        
        self.cancel_button = self.add_button("\u0130ptal", "secondary", self.reject)
        self.save_button = self.add_button("Kaydet", "primary", self.accept)
    
    def _update_action_options(self, action_type):
        """Update action combobox options based on selected type"""
        self.cmb_action.clear()
        
        if action_type == "Sayfa":
            pages = [
                f"{page_id} - {label}" for _section, entries in USER_PERMISSION_SECTIONS
                for page_id, label in entries
            ]
            self.cmb_action.addItems(pages)
            self.cmb_action.setCurrentText("")
        elif action_type == "Fonksiyon":
            functions = [
                "stok_comparison",
                "check_appointments",
                "panel_ac",
                "panel_kapat",
                "servis_ac",
                "musteri_bul",
            ]
            self.cmb_action.addItems(functions)
        else:
            self.cmb_action.addItems(["Özel Aksiyon"])
    
    def get_data(self):
        action_value = self.cmb_action.currentText()
        # Extract only number for pages
        if self.cmb_type.currentText() == "Sayfa" and " - " in action_value:
            action_value = action_value.split(" - ")[0]
        
        return {
            "name": self.inp_name.text().strip(),
            "triggers": [t.strip() for t in self.inp_triggers.toPlainText().split(",") if t.strip()],
            "type": self.cmb_type.currentText(),
            "action": action_value
        }


class ShortcutFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text_filter = ""
        self._action_filter = "Tümü"

    def set_text_filter(self, text):
        self._text_filter = text.lower().strip()
        self.invalidateFilter()

    def set_action_filter(self, value):
        self._action_filter = value
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        _ = source_parent
        model = self.sourceModel()
        combined_text = ""
        for col in range(4):
            item = model.item(source_row, col)
            if item:
                combined_text += item.text().lower() + " "
        
        if self._text_filter and self._text_filter not in combined_text:
            return False

        if self._action_filter and self._action_filter != "Tümü":
            type_item = model.item(source_row, 2)
            action_type = type_item.text() if type_item else ""
            if action_type != self._action_filter:
                return False
        return True


class ShortcutBadgeDelegate(QStyledItemDelegate):
    """Paint compact badges without changing model data or native selection."""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if index.column() in (2, 4):
            option.text = ""

    def paint(self, painter, option, index):
        if index.column() not in (2, 4):
            return super().paint(painter, option, index)
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        super().paint(painter, styled, index)
        if not text:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(styled.font)
        if index.column() == 4:
            foreground = qc("finance_secondary")
            background = qc("finance_success_bg")
        else:
            token = "finance_tertiary" if text == "Sayfa" else "finance_primary"
            foreground = qc(token)
            background = qc(token)
            background.setAlpha(28)
        width = min(painter.fontMetrics().horizontalAdvance(text) + 14, option.rect.width() - 16)
        badge = QRectF(option.rect.left() + 8, option.rect.center().y() - 10, max(0, width), 20)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(badge, 4, 4)
        painter.setPen(foreground)
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class VoiceAssistantShortcutsWidget(QWidget):
    """Voice Shortcuts Table"""
    def __init__(self, db, main_window=None, config_path=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.current_page = 0
        self.page_size = 4
        self.config_path = config_path or os.path.join(PathHelper.get_app_data_dir(), "asistan_ayarlari.json")
        self._allow_legacy_config = config_path is None
        self._build_ui()
        self._load_shortcuts()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        page_header = QFrame()
        page_header.setObjectName("voicePageHeader")
        page_header.setFixedHeight(66)
        page_header.setStyleSheet(theme_qss("QFrame#voicePageHeader { background: @finance_surface; border: none; border-radius: 6px; }"))
        header_layout = QHBoxLayout(page_header)
        header_layout.setContentsMargins(18, 10, 18, 10)
        header_text = QVBoxLayout()
        header_title = QLabel("Sesli Kestirmeler")
        header_title.setStyleSheet(theme_qss("color: @text; font-size: 16px; font-weight: 800; border: none;"))
        header_subtitle = QLabel("Komut Matrisi ve N\u00f6ral Tetikleyiciler")
        header_subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        header_text.addWidget(header_title)
        header_text.addWidget(header_subtitle)
        header_layout.addLayout(header_text)
        header_layout.addStretch()
        sync_button = QPushButton("Matrisi Senkronize Et")
        sync_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        sync_button.clicked.connect(self._load_shortcuts)
        header_layout.addWidget(sync_button)
        header_add_button = QPushButton("Yeni Kestirme Tanimla")
        header_add_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        header_add_button.clicked.connect(self._add_new_shortcut)
        header_layout.addWidget(header_add_button)
        layout.addWidget(page_header)

        featured = QHBoxLayout()
        featured.setContentsMargins(0, 8, 0, 8)
        featured.setSpacing(8)
        for command, detail, accent in (
            ('"Asistan finans \u00f6zet"', "G\u00fcnl\u00fck ciro, nakit ak\u0131\u015f\u0131 ve bekleyen tahsilatlar\u0131 listeler.", "@finance_secondary"),
            ('"Asistan kritik stoklar\u0131 listele"', "Kritik e\u015fik alt\u0131ndaki par\u00e7alar\u0131 ve sipari\u015fleri getirir.", "@finance_primary"),
            ('"Bekleyen servis fi\u015flerini a\u00e7"', "At\u00f6lyede bekleyen cihazlar\u0131 listeler.", "@warning"),
            ('"Teknisyen panelini g\u00f6ster"', "Aktif personelin i\u015f y\u00fck\u00fcn\u00fc ve g\u00f6revlerini g\u00f6sterir.", "@finance_tertiary"),
        ):
            card = QFrame()
            card.setObjectName("voiceFeaturedCard")
            card.setFixedHeight(147)
            card.setStyleSheet(theme_qss(f"QFrame#voiceFeaturedCard {{ background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }}"))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            label = QLabel(command)
            label.setWordWrap(True)
            label.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 800; border: none;"))
            body = QLabel(detail)
            body.setWordWrap(True)
            body.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
            marker = QLabel("\u25a3")
            marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
            marker.setFixedSize(24, 24)
            marker.setStyleSheet(theme_qss(f"color: {accent}; background: @finance_surface_alt; border: none; border-radius: 4px; font-weight: 800;"))
            test = QPushButton("Test Et   >")
            test.setToolTip("Komutu matriste bulur; herhangi bir veri de\u011fi\u015fikli\u011fi yapmaz.")
            test.setStyleSheet(theme_qss(f"QPushButton {{ text-align: left; color: @finance_primary; background: transparent; border: none; border-top: 1px solid @finance_outline; padding-top: 8px; }}"))
            test.clicked.connect(
                lambda _checked=False, phrase=command: self._preview_featured_command(phrase)
            )
            card_layout.addWidget(marker)
            card_layout.addWidget(label)
            card_layout.addWidget(body)
            card_layout.addStretch()
            card_layout.addWidget(test)
            featured.addWidget(card, 1)
        layout.addLayout(featured)

        matrix_header = QFrame()
        matrix_header.setStyleSheet(theme_qss(
            "QFrame { background: @surface; border: 1px solid @border; border-bottom: none; border-radius: 7px 7px 0 0; }"
        ))
        matrix_layout = QHBoxLayout(matrix_header)
        matrix_layout.setContentsMargins(14, 8, 14, 8)
        self.matrix_title = QLabel()
        matrix_title = self.matrix_title
        matrix_title.setStyleSheet(theme_qss(
            "color: @text; font-size: 13px; font-weight: 800; border: none;"
        ))
        matrix_layout.addWidget(matrix_title)
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Komut, ID veya hedef ara...")
        self.inp_search.setMinimumWidth(180)
        self.inp_search.setMaximumWidth(300)
        self.inp_search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_search.textChanged.connect(self._apply_search_filter)
        matrix_layout.addWidget(self.inp_search, 1)
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["Tümü", "Sayfa", "Fonksiyon", "Aksiyon", "Bağlantı Yok"])
        self.cmb_filter.setFixedWidth(150)
        self.cmb_filter.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.cmb_filter.currentTextChanged.connect(self._apply_action_filter)
        matrix_layout.addWidget(self.cmb_filter)
        layout.addWidget(matrix_header)

        # Table
        self.table = QTableView()
        self.table.setMinimumHeight(245)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMouseTracking(False)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(theme_qss("""
            QTableView {
                background: @surface;
                border: none;
                color: @text;
                gridline-color: transparent;
                selection-background-color: transparent;
                selection-color: @text;
                alternate-background-color: @surface_alt;
                outline: none;
            }
            QTableView::item {
                padding: 6px 10px;
                border-bottom: 1px solid @surface_alt;
                border: none;
                outline: none;
            }
            QTableView::item:selected {
                background: @selection_bg;
                border: none;
                outline: none;
            }
            QTableView::item:focus {
                border: none;
                outline: none;
                background: @selection_bg;
            }
            QHeaderView::section {
                background: @surface_alt;
                color: @text;
                font-weight: 600;
                padding: 8px 10px;
                border: none;
                border-right: 1px solid @border;
                text-transform: uppercase;
                font-size: 10px;
                letter-spacing: 0.5px;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """))
        
        self.model = QStandardItemModel(0, 6, self)
        self.model.setHorizontalHeaderLabels(["KEST\u0130RME ADI", "TET\u0130KLEY\u0130C\u0130 KOMUTLAR", "\u0130\u015eLEM T\u00dcR\u00dc", "HEDEF ROTA / ID", "DURUM", "\u0130\u015eLEMLER"])
        self.proxy = ShortcutFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        self.table.setItemDelegate(ShortcutBadgeDelegate(self.table))
        self.table.setSortingEnabled(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 170)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(2, 140)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(3, 150)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        # Context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._edit_shortcut)
        self.table.clicked.connect(self._activate_row_action)

        layout.addWidget(self.table, 1)
        pager = QHBoxLayout()
        pager.setContentsMargins(14, 8, 14, 8)
        self.page_result_label = QLabel()
        self.page_result_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        pager.addWidget(self.page_result_label)
        pager.addStretch()
        self.previous_page = QPushButton("\u00d6nceki")
        self.page_label = QLabel("1 / 1")
        self.page_label.setMinimumWidth(48)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_page = QPushButton("Sonraki")
        for button in (self.previous_page, self.next_page):
            button.setFixedSize(70, 30)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.previous_page.clicked.connect(lambda: self._change_page(-1))
        self.next_page.clicked.connect(lambda: self._change_page(1))
        pager.addWidget(self.previous_page)
        pager.addWidget(self.page_label)
        pager.addWidget(self.next_page)
        layout.addLayout(pager)

    def _preview_featured_command(self, phrase):
        query = str(phrase or "").strip().strip('"')
        self.cmb_filter.setCurrentIndex(0)
        self.inp_search.setText(query)
        if self.proxy.rowCount():
            show_success(self, f"'{query}' komutu matriste bulundu.")
        else:
            self.inp_search.clear()
            show_error(self, f"'{query}' komutu matriste bulunamadi.")

    def _apply_search_filter(self, text):
        self.current_page = 0
        self.proxy.set_text_filter(text)
        self._apply_pagination()

    def _apply_action_filter(self, value):
        self.current_page = 0
        self.proxy.set_action_filter(value)
        self._apply_pagination()

    def _change_page(self, delta):
        self.current_page += delta
        self._apply_pagination()

    def _apply_pagination(self):
        self.matrix_title.setText(
            f"Kapsaml\u0131 Kestirme Matrisi   {self.model.rowCount()} Kay\u0131tl\u0131 Komut"
        )
        total = self.proxy.rowCount()
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        self.current_page = max(0, min(self.current_page, total_pages - 1))
        start = self.current_page * self.page_size
        end = min(total, start + self.page_size)
        for row in range(total):
            self.table.setRowHidden(row, row < start or row >= end)
        self.page_result_label.setText(
            f"Toplam {total} komuttan {0 if total == 0 else start + 1}-{end} arasi gosteriliyor"
        )
        self.page_label.setText(f"{self.current_page + 1} / {total_pages}")
        self.previous_page.setEnabled(self.current_page > 0)
        self.next_page.setEnabled(self.current_page + 1 < total_pages)

    def _activate_row_action(self, index):
        if index.isValid() and index.column() == 5:
            self._edit_shortcut(index)

    def _show_context_menu(self, position: QPoint):
        if not is_context_menu_enabled(self.db):
            return
        menu = QMenu(self)
        menu.setStyleSheet(theme_qss("""
            QMenu {
                background: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: @selection_bg;
                color: @selection_text;
            }
        """))
        
        index = self.table.indexAt(position)
        
        if index.isValid():
            edit_action = QAction("✏️ Düzenle", self)
            edit_action.triggered.connect(lambda: self._edit_shortcut(index))
            menu.addAction(edit_action)
            
            delete_action = QAction("🗑️ Sil", self)
            delete_action.triggered.connect(lambda: self._delete_shortcut(index))
            menu.addAction(delete_action)
            
            menu.addSeparator()
        
        add_action = QAction("➕ Yeni Kestirme Ekle", self)
        add_action.triggered.connect(self._add_new_shortcut)
        menu.addAction(add_action)
        
        menu.exec(QCursor.pos())
    
    def _edit_shortcut(self, index):
        if not index.isValid():
            return
        
        source_index = self.proxy.mapToSource(index)
        row = source_index.row()
        
        name = self.model.item(row, 0).text()
        triggers = self.model.item(row, 1).text()
        action_type = self.model.item(row, 2).text()
        action = self.model.item(row, 3).text()
        
        dialog = ShortcutEditDialog(name, triggers, action_type, action, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data["name"] or not data["triggers"]:
                show_error(self, "Lütfen en az kestirme adı ve tetikleyici komut girin!")
                return
            
            # Update model and save
            self._update_shortcut_in_config(name, data)
            self._load_shortcuts()
    
    def _delete_shortcut(self, index):
        source_index = self.proxy.mapToSource(index)
        row = source_index.row()
        name = self.model.item(row, 0).text()
        
        # Remove from config
        self._remove_shortcut_from_config(name)
        self._load_shortcuts()
        show_success(self, f"'{name}' kestirmesi silindi!")
    
    def _add_new_shortcut(self):
        dialog = ShortcutEditDialog("", "", "Sayfa", "", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data["name"] or not data["triggers"]:
                show_error(self, "Lütfen en az kestirme adı ve tetikleyici komut girin!")
                return
            
            self._add_shortcut_to_config(data)
            self._load_shortcuts()
            show_success(self, f"'{data['name']}' kestirmesi eklendi!")

    def _load_shortcuts(self):
        self.model.removeRows(0, self.model.rowCount())
        self.current_page = 0
        self._apply_pagination()

        path = self.config_path
        if not os.path.exists(path):
            if not self._allow_legacy_config:
                return
            legacy = os.path.join(os.getcwd(), "asistan_ayarlari.json")
            if os.path.exists(legacy):
                path = legacy
            else:
                return

        try:
            with open(path, "r", encoding="utf-8") as f:
                shortcuts = json.load(f)
        except Exception as e:
            logger.error(f"VoiceAssistantShortcutsWidget load/remove shortcuts error: {e}")
            return

        shortcuts = self._normalize_shortcuts(shortcuts)

        for name, data in shortcuts.items():
            if not isinstance(data, dict):
                continue
            
            # Compatibility with VoiceTrainingWidget's triggers or tetikleyiciler
            triggers = data.get("triggers") or data.get("tetikleyiciler") or []
            if isinstance(triggers, str):
                triggers = [t.strip() for t in triggers.replace(";", ",").split(",") if t.strip()]
            elif not isinstance(triggers, list):
                triggers = []

            triggers_str = ",  ".join([str(t) for t in triggers])
            
            # Action data resolution
            action_data = data.get("action")
            action_type = "Bağlantı Yok"
            action_value = ""
            
            if isinstance(action_data, dict):
                a_type = action_data.get("type")
                if a_type == "page":
                    action_type = "Sayfa"
                    action_value = str(action_data.get("index", ""))
                elif a_type == "builtin":
                    action_type = "Fonksiyon"
                    action_value = action_data.get("name", "")
                elif a_type == "action":
                    action_type = "Aksiyon"
                    action_value = action_data.get("name", "")
            elif isinstance(action_data, str):
                action_type = "Fonksiyon"
                action_value = action_data
            elif data.get("tur") and data.get("aksiyon"): # Legacy or other structure
                action_type = str(data.get("tur"))
                action_value = str(data.get("aksiyon"))
            
            row = [
                QStandardItem(name),
                QStandardItem(triggers_str),
                QStandardItem(action_type),
                QStandardItem(action_value),
                QStandardItem("Aktif"),
                QStandardItem(">   Edit")
            ]
            
            for item in row:
                item.setEditable(False)
                item.setToolTip(item.text())
            
            self.model.appendRow(row)
        self.current_page = 0
        self._apply_pagination()

    def _normalize_shortcuts(self, raw):
        if not isinstance(raw, dict):
            return {}

        normalized = {}
        legacy_builtin_map = {
            "stok_sorgu": {"type": "builtin", "name": "list_critical_stock"},
            "servis_ac": {"type": "builtin", "name": "servis_ac"},
            "excel_islem": {"type": "builtin", "name": "accounting_summary"},
            "panel_ac": {"type": "builtin", "name": "panel_ac"},
        }

        for key, value in raw.items():
            if not isinstance(key, str) or not key.strip():
                continue

            if isinstance(value, list):
                normalized[key] = {
                    "triggers": [str(v).strip() for v in value if str(v).strip()],
                    "action": legacy_builtin_map.get(key),
                }
                continue

            if not isinstance(value, dict):
                continue

            triggers = value.get("triggers")
            if triggers is None:
                triggers = value.get("tetikleyiciler")
            if triggers is None:
                triggers = value.get("kelimeler")

            if isinstance(triggers, str):
                triggers = [t.strip() for t in triggers.replace(";", ",").split(",") if t.strip()]
            elif not isinstance(triggers, list):
                triggers = []

            action = value.get("action")
            if isinstance(action, str):
                action = {"type": "builtin", "name": action}
            elif not isinstance(action, dict):
                action = legacy_builtin_map.get(key)

            normalized[key] = {
                "triggers": [str(v).strip() for v in triggers if str(v).strip()],
                "action": action,
            }

        return normalized

    def _add_shortcut_to_config(self, data):
        config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                logger.debug(f"VoiceAssistantShortcutsWidget config fallback: {e}")
        
        # Consistent action structure
        action_payload = None
        if data["type"] == "Sayfa":
            action_payload = {"type": "page", "index": int(data["action"]) if str(data["action"]).isdigit() else data["action"]}
        elif data["type"] == "Fonksiyon":
            action_payload = {"type": "builtin", "name": data["action"]}
        elif data["type"] == "Aksiyon":
            action_payload = {"type": "action", "name": data["action"]}

        config[data["name"]] = {
            "triggers": data["triggers"],
            "action": action_payload
        }
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _update_shortcut_in_config(self, old_name, data):
        config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                logger.debug(f"VoiceAssistantShortcutsWidget config fallback: {e}")
        
        previous_entry = config.pop(old_name, {})
        updated_entry = dict(previous_entry) if isinstance(previous_entry, dict) else {}
        
        # Consistent action structure
        action_payload = None
        if data["type"] == "Sayfa":
            action_payload = {"type": "page", "index": int(data["action"]) if str(data["action"]).isdigit() else data["action"]}
        elif data["type"] == "Fonksiyon":
            action_payload = {"type": "builtin", "name": data["action"]}
        elif data["type"] == "Aksiyon":
            action_payload = {"type": "action", "name": data["action"]}

        updated_entry.update({"triggers": data["triggers"], "action": action_payload})
        config[data["name"]] = updated_entry
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _remove_shortcut_from_config(self, name):
        if not os.path.exists(self.config_path):
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"VoiceAssistantShortcutsWidget remove shortcuts error: {e}")
            return
        
        if name in config:
            del config[name]
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
