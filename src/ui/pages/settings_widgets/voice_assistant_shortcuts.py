# -*- coding: utf-8 -*-

# VoiceAssistantShortcutsWidget - Separate file for shortcuts
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QFrame, QComboBox, QTableView, QAbstractItemView, 
                             QHeaderView, QSizePolicy, QDialog, QFormLayout, QMenu, QTextEdit)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, QPoint, QTimer
from PyQt6.QtGui import QFont, QStandardItemModel, QStandardItem, QAction, QCursor
import os
import json

from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error
from src.utils.design_system import DesignTokens
from src.utils.path_helper import PathHelper
from src.utils.logger import logger
from src.utils.context_menu_settings import is_context_menu_enabled


class AutoPopupComboBox(QComboBox):
    """ComboBox that auto-opens popup on any click"""
    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and not self.view().isVisible():
            QTimer.singleShot(0, self.showPopup)


class ShortcutEditDialog(QDialog):
    """Premium frameless dialog for editing shortcuts"""
    def __init__(self, shortcut_name="", triggers="", action_type="", action="", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # Main container with shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Content frame (rounded)
        content = QFrame()
        content.setObjectName("contentFrame")
        content.setStyleSheet(theme_qss("""
            QFrame#contentFrame {
                background: @surface;
                border-radius: 16px;
                border: 1px solid @border;
            }
        """))
        
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(20)
        
        # Title bar with close
        title_bar = QFrame()
        title_bar.setStyleSheet(theme_qss("background: transparent; border: none;"))
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("✏️ Kestirme Düzenle")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet(theme_qss("color: @text;"))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(theme_qss("""
            QPushButton {
                background: transparent;
                border: none;
                color: @text_muted;
                font-size: 18px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: @surface_alt;
                color: @text;
            }
        """))
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        content_layout.addWidget(title_bar)
        
        # Form
        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Shortcut Name
        self.inp_name = QLineEdit(shortcut_name)
        self.inp_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_name.setPlaceholderText("örn: stok_sorgu")
        form.addRow("Kestirme Adı:", self.inp_name)
        
        # Triggers
        self.inp_triggers = QTextEdit()
        self.inp_triggers.setPlainText(triggers)
        self.inp_triggers.setMaximumHeight(100)
        self.inp_triggers.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_triggers.setPlaceholderText("stoklar, stok, stoğa bak, envanter (virgülle ayırın)")
        form.addRow("Tetikleyici Komutlar:", self.inp_triggers)
        
        # Action Type
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Sayfa", "Fonksiyon", "Aksiyon"])
        self.cmb_type.setCurrentText(action_type if action_type != "Bağlantı Yok" else "Sayfa")
        self.cmb_type.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.cmb_type.currentTextChanged.connect(self._update_action_options)
        form.addRow("İşlem Türü:", self.cmb_type)
        
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
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedWidth(100)
        btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="md")))
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("💾 Kaydet")
        btn_save.setFixedWidth(120)
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="md")))
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)
        
        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content)
        
        # Allow dragging
        self.drag_pos = None
    
    def _update_action_options(self, action_type):
        """Update action combobox options based on selected type"""
        self.cmb_action.clear()
        
        if action_type == "Sayfa":
            pages = [
                "10 - Ana Sayfa",
                "20 - Servis Yönetimi",
                "30 - Müşteriler",
                "40 - Stok Yönetimi",
                "50 - Satış",
                "60 - Raporlar",
                "70 - Finans",
                "80 - Ayarlar",
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
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
        super().mouseMoveEvent(event)
    
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


class VoiceAssistantShortcutsWidget(QWidget):
    """Voice Shortcuts Table"""
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.config_path = os.path.join(PathHelper.get_app_data_dir(), "asistan_ayarlari.json")
        self._build_ui()
        self._load_shortcuts()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Bar
        top_bar_frame = QFrame()
        top_bar_frame.setStyleSheet(theme_qss("background: @surface; border-bottom: 1px solid @border;"))
        top_bar_frame.setFixedHeight(60)
        
        top_layout = QHBoxLayout(top_bar_frame)
        top_layout.setContentsMargins(24, 10, 24, 10)
        top_layout.setSpacing(12)

        # Search
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("🔍 Ara...")
        self.inp_search.setFixedWidth(240)
        self.inp_search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_search.textChanged.connect(self._apply_search_filter)
        top_layout.addWidget(self.inp_search)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["Tümü", "Sayfa", "Fonksiyon", "Aksiyon", "Bağlantı Yok"])
        self.cmb_filter.setFixedWidth(140)
        self.cmb_filter.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.cmb_filter.currentTextChanged.connect(self._apply_action_filter)
        top_layout.addWidget(self.cmb_filter)

        top_layout.addStretch()

        # Add Button
        self.btn_add_shortcut = QPushButton("+ Yeni")
        self.btn_add_shortcut.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_shortcut.setFixedWidth(80)
        self.btn_add_shortcut.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.btn_add_shortcut.clicked.connect(self._add_new_shortcut)
        top_layout.addWidget(self.btn_add_shortcut)

        layout.addWidget(top_bar_frame)

        # Table
        self.table = QTableView()
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
                padding: 8px 16px;
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
                padding: 12px 16px;
                border: none;
                border-right: 1px solid @border;
                text-transform: uppercase;
                font-size: 12px;
                letter-spacing: 0.5px;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """))
        
        self.model = QStandardItemModel(0, 4, self)
        self.model.setHorizontalHeaderLabels(["KESTİRME ADI", "TETİKLEYİCİ KOMUTLAR", "İŞLEM TÜRÜ", "AKSİYON"])
        self.proxy = ShortcutFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        # Context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.doubleClicked.connect(self._edit_shortcut)

        layout.addWidget(self.table)

    def _apply_search_filter(self, text):
        self.proxy.set_text_filter(text)

    def _apply_action_filter(self, value):
        self.proxy.set_action_filter(value)

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

        path = self.config_path
        if not os.path.exists(path):
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
                QStandardItem(action_value)
            ]
            
            for item in row:
                item.setEditable(False)
            
            self.model.appendRow(row)

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
        
        if old_name in config:
            del config[old_name]
        
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
