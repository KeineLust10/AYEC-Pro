# -*- coding: utf-8 -*-
# _tp_tabs.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, 
    QHeaderView, QFrame, QScrollArea, QGridLayout
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.automotive_defaults import AUTOMOTIVE_PRESET
from src.utils.technical_service_profiles import get_profile_labels

class _TpTabs:
    def _create_technician_workflow_strip(self):
        strip = QFrame()
        strip.setObjectName("TechnicianWorkflowStrip")
        strip.setStyleSheet(theme_qss(
            """
            QFrame#TechnicianWorkflowStrip {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 8px;
            }
            """
        ))
        row = QHBoxLayout(strip)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)
        labels = (
            ["Ara\u00e7 Kabul", "Ar\u0131za", "Par\u00e7a ve \u0130\u015flem", "Teslim"]
            if self._is_automotive()
            else ["Cihaz Kabul", "Ar\u0131za", "Par\u00e7a ve \u0130\u015flem", "Teslim"]
        )
        for index, label_text in enumerate(labels):
            badge = QLabel(str(index + 1))
            badge.setFixedSize(22, 22)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(theme_qss(
                "background: @accent; color: @selection_text; border-radius: 11px;"
                "font-weight: 800; border: none;"
            ))
            label = QLabel(label_text)
            label.setStyleSheet(theme_qss(
                "color: @text; font-size: 11px; font-weight: 700; border: none;"
            ))
            row.addWidget(badge)
            row.addWidget(label)
            if index < len(labels) - 1:
                row.addStretch(1)
                separator = QLabel(">")
                separator.setStyleSheet(theme_qss(
                    "color: @text_muted; font-weight: 800; border: none;"
                ))
                row.addWidget(separator)
                row.addStretch(1)
        return strip

    def create_general_tab(self):
        """Build the default non-automotive General tab"""
        self.general_widget = QWidget()
        self.general_widget.setObjectName("TechnicianPanelGeneral")
        layout = QVBoxLayout(self.general_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self._create_technician_workflow_strip())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget(scroll)
        self.general_content_layout = QVBoxLayout(content)
        self.general_content_layout.setContentsMargins(0, 0, 0, 0)
        self.general_content_layout.setSpacing(15)

        from src.ui.dialogs.technician_wizard_page1 import TechnicianWizardPage1
        from src.ui.dialogs.technician_wizard_page2 import TechnicianWizardPage2
        from src.ui.dialogs.technician_wizard_page3 import TechnicianWizardPage3

        self.wizard_page1 = TechnicianWizardPage1(self.db, self.tracking_no, self.device_dict, content, sector_manager=self.sector_manager)
        self.wizard_page2 = TechnicianWizardPage2(self.db, self.tracking_no, self.device_dict, content, sector_manager=self.sector_manager)
        self.wizard_page3 = TechnicianWizardPage3(self.db, self.tracking_no, self.device_dict, content)

        self.general_content_layout.addWidget(self.wizard_page1)
        self.general_content_layout.addWidget(self.wizard_page2)
        self.general_content_layout.addWidget(self.wizard_page3)
        self.general_content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        

    def create_test_tab(self):
        self.test_widget = QWidget()
        self.test_widget.setObjectName("TechnicianPanelTest")
        layout = QVBoxLayout(self.test_widget)

        header = QHBoxLayout()
        test_title = "Ara\u00e7 Kontrol ve Test Formu" if self._is_automotive() else "Cihaz Kontrol & Test Formu"
        self.test_header = QLabel(test_title)
        self.test_header.setFont(QFont(DesignTokens.FONT_FAMILY, 12, QFont.Weight.Bold))
        header.addWidget(self.test_header)
        header.addStretch()
        
        btn_edit = QPushButton("Testleri D\u00fczenle")
        btn_edit.setFixedWidth(140)
        btn_edit.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_edit.clicked.connect(self.open_test_toggle_editor)
        header.addWidget(btn_edit)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.test_container = QWidget()
        self.test_grid = QGridLayout(self.test_container)
        self.test_grid.setSpacing(10)
        self.test_grid.setContentsMargins(5, 5, 5, 5)
        
        scroll.setWidget(self.test_container)
        layout.addWidget(scroll)
        
        QTimer.singleShot(50, self.reload_test_toggles)

    def create_logs_tab(self):
        self.log_widget = QWidget()
        self.log_widget.setObjectName("TechnicianPanelLog")
        layout = QVBoxLayout(self.log_widget)
        
        self.table_logs = QTableWidget(0, 3)
        self.table_logs.setHorizontalHeaderLabels(["Tarih/Saat", "Tür", "İşlem / Mesaj"])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_logs.horizontalHeader().setStretchLastSection(True)
        self.table_logs.setColumnWidth(0, 160)
        self.table_logs.setColumnWidth(1, 100)
        self.table_logs.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_logs.setAlternatingRowColors(True)
        self.table_logs.setStyleSheet(theme_qss(f"""
            QTableWidget {{
                background-color: white;
                alternate-background-color: @surface_alt;
                color: {DesignTokens.FOREGROUND};
                border-bottom: 1px solid @border;
                outline: none;
            }}
            QTableWidget::item {{
                outline: none;
            }}
            QTableWidget::item:focus {{
                outline: none;
                border: none;
            }}
            QTableWidget QHeaderView::section {{
                background-color: @surface_alt;
                color: @selection_text;
                padding: 10px;
                border: none;
                border-bottom: 2px solid @border;
                font-weight: bold;
                font-size: 12px;
                text-align: left;
            }}
        """))
        layout.addWidget(self.table_logs)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_refresh = QPushButton("Yenile")
        btn_refresh.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_refresh.setFixedHeight(40)
        btn_refresh.clicked.connect(self.refresh_logs)
        btn_row.addWidget(btn_refresh)
        layout.addLayout(btn_row)
        
        QTimer.singleShot(0, self.refresh_logs)

    def open_test_toggle_editor(self):
        from src.ui.dialogs.quick_notes_editor import QuickNotesEditor

        checklist_category = self._get_checklist_category()
        try:
            editor = QuickNotesEditor(
                self.db,
                self,
                initial_category=checklist_category,
                sector_manager=self.sector_manager,
                profile_name=self.get_technical_service_profile(),
            )
        except TypeError:
            editor = QuickNotesEditor(
                self.db, self, initial_category=checklist_category
            )
        try:
            editor.exec()
        finally:
            self.reload_test_toggles()

    def _get_test_items(self):
        tests = []
        checklist_category = self._get_checklist_category()
        try:
            rows, _ = self._get_fast_notes_for_category(checklist_category)
            for row in rows:
                if isinstance(row, dict):
                    label = str(row.get("label", "") or "").strip()
                    active_val = row.get("is_active", 1)
                else:
                    try:
                        label = (
                            str(row["label"]).strip()
                            if hasattr(row, "keys") and "label" in row.keys()
                            else str(row[2]).strip()
                        )
                        active_val = (
                            row["is_active"]
                            if hasattr(row, "keys") and "is_active" in row.keys()
                            else row[3]
                        )
                    except Exception:
                        label = ""
                        active_val = 1
                if not label:
                    continue
                try:
                    is_active = int(active_val) == 1
                except Exception:
                    is_active = bool(active_val)
                tests.append((label, is_active))
        except Exception:
            tests = []

        if not tests and self._is_automotive():
            tests = [
                (label, True)
                for label in AUTOMOTIVE_PRESET.get(checklist_category, [])
            ]
        elif not tests:
            tests = [
                (label, True)
                for label in get_profile_labels(
                    self.get_technical_service_profile(), "Cihaz Testi"
                )
            ]
        return tests

    def reload_test_toggles(self):
        if not hasattr(self, "test_grid"):
            return
        self._clear_layout(self.test_grid)
        self.test_toggles = []
        
        test_items = self._get_test_items()
        current_status = self._load_cached_checklist_status()
        active_items = [x.strip().upper() for x in current_status.split(",") if x.strip()]
        
        from src.ui.widgets.animated_toggle import AnimatedToggle
        
        col_count = 3
        for idx, (label, is_visible) in enumerate(test_items):
            if not is_visible:
                continue
            
            row = idx // col_count
            col = idx % col_count
            
            item_widget = QFrame()
            item_widget.setObjectName("ClassicQuickToggleItem")
            item_widget.setMinimumHeight(42)
            item_widget.setStyleSheet(theme_qss("""
                QFrame { background: @surface; border: 1px solid @border; border-radius: 10px; }
            """))
            item_lay = QHBoxLayout(item_widget)
            item_lay.setContentsMargins(10, 8, 10, 8)
            
            lbl = QLabel(label)
            lbl.setFont(QFont(DesignTokens.FONT_FAMILY, 9))
            lbl.setWordWrap(True)
            
            toggle = AnimatedToggle()
            toggle.setFixedSize(50, 26)
            if label.upper() in active_items:
                toggle.setChecked(True)
            
            toggle.toggled.connect(lambda checked, n=label: self._handle_toggle_changed(n, checked))
            
            item_lay.addWidget(lbl, 1)
            item_lay.addWidget(toggle)
            self.test_grid.addWidget(item_widget, row, col)
            self.test_toggles.append((label, toggle))
        self.test_grid.setRowStretch((len(test_items)//col_count)+1, 1)
        self._schedule_classic_panel_styles()
