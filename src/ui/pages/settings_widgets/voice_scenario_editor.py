# -*- coding: utf-8 -*-

"""
Voice Scenario Editor Dialog
Sesli Komut Senaryo Editoru
"""

import json

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_warning


class VoiceScenarioEditorDialog(ModernDialog):
    """Sesli komut senaryo editoru dialogu."""

    def __init__(self, widget):
        super().__init__(title="Sesli Komut Senaryolari", parent=(widget.main_window or widget), width=1160, height=760)
        self.widget = widget
        self.setModal(True)
        self.set_footer_visible(False)
        self._action_setting = False
        self._build_ui()
        self.refresh_scenarios()

    def _build_ui(self):
        self.setStyleSheet(theme_qss("QDialog { background: @surface_alt; }"))
        layout = self.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        hero = QFrame()
        hero.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 18px; }"))
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)

        hero_text = QVBoxLayout()
        title = QLabel("Sesli Komut Senaryolari")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        desc = QLabel("Senaryo adi, tetikleyici kelimeler ve bagli islemleri tek pencerede yonetin.")
        desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 600;"))
        desc.setWordWrap(True)
        hero_text.addWidget(title)
        hero_text.addWidget(desc)
        hero_layout.addLayout(hero_text, 1)

        self.lbl_current = QLabel("Senaryo secin")
        self.lbl_current.setStyleSheet(
            theme_qss(
                "QLabel { background: @surface_alt; color: @text; border: 1px solid @border; "
                "border-radius: 10px; padding: 8px 12px; font-weight: 700; }"
            )
        )
        hero_layout.addWidget(self.lbl_current, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(hero)

        body = QHBoxLayout()
        body.setSpacing(14)

        left = QFrame()
        left.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 16px; }"))
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Senaryo ara...")
        self.inp_search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_search.textChanged.connect(self.refresh_scenarios)
        left_layout.addWidget(self.inp_search)

        list_qss = theme_qss(
            """
            QListWidget {
                padding: 8px;
                border: 1px solid @border;
                border-radius: 12px;
                background: @surface_alt;
            }
            QListWidget::item {
                margin-bottom: 6px;
                padding: 10px 12px;
                border-radius: 10px;
                background: @surface;
                color: @text;
                font-weight: 600;
            }
            QListWidget::item:selected {
                background: @selection_bg;
                color: @accent_pressed;
            }
            """
        )

        self.list_scenarios = QListWidget()
        self.list_scenarios.setStyleSheet(list_qss)
        self.list_scenarios.itemClicked.connect(self.on_scenario_selected)
        left_layout.addWidget(self.list_scenarios, 1)

        left_buttons = QHBoxLayout()
        self.btn_add = QPushButton("➕ Senaryo Ekle")
        self.btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.btn_add.clicked.connect(self.add_scenario)
        self.btn_delete = QPushButton("🗑️ Sil")
        self.btn_delete.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_delete.clicked.connect(self.delete_scenario)
        left_buttons.addWidget(self.btn_add)
        left_buttons.addWidget(self.btn_delete)
        left_layout.addLayout(left_buttons)

        right = QFrame()
        right.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 16px; }"))
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        self.lbl_editor_title = QLabel("Senaryo detaylari")
        self.lbl_editor_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_editor_title.setStyleSheet(theme_qss("color: @text;"))
        right_layout.addWidget(self.lbl_editor_title)

        trig_title = QLabel("Tetikleyici Kelimeler")
        trig_title.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
        right_layout.addWidget(trig_title)

        self.list_triggers = QListWidget()
        self.list_triggers.setStyleSheet(list_qss)
        self.list_triggers.setMinimumHeight(200)
        right_layout.addWidget(self.list_triggers)

        trig_row = QHBoxLayout()
        self.inp_trigger = QLineEdit()
        self.inp_trigger.setPlaceholderText("Yeni tetikleyici yaz...")
        self.inp_trigger.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_trigger.returnPressed.connect(self.add_trigger)
        self.btn_add_trigger = QPushButton("Ekle")
        self.btn_add_trigger.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.btn_add_trigger.clicked.connect(self.add_trigger)
        self.btn_delete_trigger = QPushButton("Sil")
        self.btn_delete_trigger.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_delete_trigger.clicked.connect(self.delete_trigger)
        trig_row.addWidget(self.inp_trigger)
        trig_row.addWidget(self.btn_add_trigger)
        trig_row.addWidget(self.btn_delete_trigger)
        right_layout.addLayout(trig_row)

        action_title = QLabel("Bagli Islem")
        action_title.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
        right_layout.addWidget(action_title)

        self.cmb_action = QComboBox()
        self.cmb_action.setFixedHeight(44)
        self.cmb_action.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        right_layout.addWidget(self.cmb_action)
        self.widget._init_action_options(self.cmb_action)
        self.cmb_action.currentIndexChanged.connect(self.on_action_changed)

        self.chk_auto_search = QCheckBox("Sesli parametreyi acilan sayfada ara")
        self.chk_auto_search.setStyleSheet(
            theme_qss(
                """
                QCheckBox { color: @text_muted; font-weight: 600; }
                QCheckBox::indicator { width: 18px; height: 18px; border-radius: 6px; border: 2px solid @border; background: @surface; }
                QCheckBox::indicator:checked { background: @accent; border-color: @accent; }
                """
            )
        )
        self.chk_auto_search.stateChanged.connect(self.on_auto_search_changed)
        right_layout.addWidget(self.chk_auto_search)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(150)
        self.preview.setStyleSheet(
            theme_qss(
                "QTextEdit { background: @surface_alt; border: 1px solid @border; border-radius: 12px; "
                "padding: 10px; color: @text; font-size: 12px; }"
            )
        )
        right_layout.addWidget(self.preview)

        body.addWidget(left, 1)
        body.addWidget(right, 2)
        layout.addLayout(body, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        self.btn_test = QPushButton("🎙️ Aktif Senaryoyu Test Et")
        self.btn_test.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_test.clicked.connect(self.widget.test_active_scenario)
        self.btn_close = QPushButton("Kapat")
        self.btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.btn_close.clicked.connect(self.accept)
        footer.addWidget(self.btn_test)
        footer.addWidget(self.btn_close)
        layout.addLayout(footer)

    def refresh_scenarios(self):
        self.list_scenarios.clear()
        search = self.inp_search.text().strip().lower()
        for key in sorted(self.widget.data.keys()):
            if search and search not in key.lower():
                continue
            self.list_scenarios.addItem(QListWidgetItem(key))
        if self.list_scenarios.count():
            self.list_scenarios.setCurrentRow(0)
            self.on_scenario_selected(self.list_scenarios.currentItem())
        else:
            self.lbl_current.setText("Senaryo bulunamadi")
            self.preview.setPlainText("")

    def _selected_name(self):
        item = self.list_scenarios.currentItem()
        return item.text() if item else ""

    def on_scenario_selected(self, item):
        if not item:
            return
        name = item.text()
        self.widget.current_scenario_name = name
        self.lbl_current.setText(name)
        self.lbl_editor_title.setText(f"{name} detaylari")
        cfg = self.widget.data.get(name, {})
        triggers = cfg.get("triggers", []) if isinstance(cfg, dict) else []
        self.list_triggers.clear()
        for trig in triggers:
            self.list_triggers.addItem(trig)

        current_action = cfg.get("action") if isinstance(cfg, dict) else None
        base_action = current_action
        is_auto_search = False
        if isinstance(current_action, dict) and current_action.get("type") == "page_search":
            base_action = {"type": "page", "index": current_action.get("index")}
            is_auto_search = True
        elif isinstance(current_action, dict):
            is_auto_search = bool(current_action.get("auto_search"))

        current_payload = "" if base_action is None else json.dumps(base_action, ensure_ascii=False, sort_keys=True)
        self._action_setting = True
        try:
            for i in range(self.cmb_action.count()):
                if self.cmb_action.itemData(i, Qt.ItemDataRole.UserRole) == current_payload:
                    self.cmb_action.setCurrentIndex(i)
                    break
        finally:
            self._action_setting = False

        self.chk_auto_search.setEnabled(isinstance(base_action, dict) and base_action.get("type") == "page")
        self.chk_auto_search.setChecked(is_auto_search)

        lines = [
            f"Senaryo: {name}",
            f"Tetikleyici sayisi: {len(triggers)}",
            f"Bagli islem: {self.cmb_action.currentText() or 'Baglanti yok'}",
            "",
            "Tetikleyiciler:",
        ]
        lines.extend([f"- {trig}" for trig in triggers] or ["- Henuz tetikleyici yok"])
        self.preview.setPlainText("\n".join(lines))

    def add_scenario(self):
        self.widget.add_scenario()
        self.refresh_scenarios()

    def delete_scenario(self):
        name = self._selected_name()
        if not name:
            return
        self.widget.delete_scenario_by_name(name)
        self.refresh_scenarios()

    def add_trigger(self):
        name = self._selected_name()
        if not name:
            show_warning(self.widget.main_window or self, "Once bir senaryo secin.")
            return
        self.widget.add_trigger_to_scenario(name, self.inp_trigger.text())
        self.inp_trigger.clear()
        self.on_scenario_selected(self.list_scenarios.currentItem())

    def delete_trigger(self):
        name = self._selected_name()
        trigger_item = self.list_triggers.currentItem()
        if not name or not trigger_item:
            return
        self.widget.delete_trigger_from_scenario(name, trigger_item.text())
        self.on_scenario_selected(self.list_scenarios.currentItem())

    def on_action_changed(self, _index):
        if self._action_setting:
            return
        name = self._selected_name()
        if not name:
            return
        payload = self.cmb_action.currentData(Qt.ItemDataRole.UserRole)
        self.widget.set_scenario_action(name, payload, self.chk_auto_search.isChecked())
        self.on_scenario_selected(self.list_scenarios.currentItem())

    def on_auto_search_changed(self, *_):
        name = self._selected_name()
        if not name:
            return
        payload = self.cmb_action.currentData(Qt.ItemDataRole.UserRole)
        self.widget.set_scenario_action(name, payload, self.chk_auto_search.isChecked())
