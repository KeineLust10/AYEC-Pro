# -*- coding: utf-8 -*-
# _tp_tabs.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QBoxLayout,
    QHeaderView, QFrame, QScrollArea, QGridLayout, QSizePolicy, QComboBox, QDateEdit
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.modern_inputs import ModernComboBox
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
                border-radius: 4px;
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
        self.general_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.general_widget.setStyleSheet(theme_qss("QWidget#TechnicianPanelGeneral{background:@finance_canvas;border:none;}"))
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
        self.wizard_page2.workflow_strip.hide()
        self.wizard_page2.setObjectName("TechnicianNotesCard")
        self.wizard_page2.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.wizard_page2.setStyleSheet(theme_qss("QWidget#TechnicianNotesCard{background:@finance_surface;border:1px solid @finance_outline;border-radius:4px;}"))
        for control in self.wizard_page3.findChildren((QComboBox, QDateEdit)):
            control.setMinimumHeight(26)
            control.setMaximumHeight(30)
            control.setStyleSheet(theme_qss("QComboBox,QDateEdit{background:@finance_canvas;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:2px 6px;min-height:24px;max-height:28px;font-size:11px;}QComboBox::drop-down,QDateEdit::drop-down{border:none;width:16px;}"))
            if isinstance(control, ModernComboBox):
                control.set_reference_chevron()
            elif isinstance(control, QDateEdit):
                control.setFixedHeight(30)
                control.setStyleSheet(control.styleSheet() + "QDateEdit::drop-down{width:28px;background:transparent;}QDateEdit::down-arrow{image:none;width:0;height:0;border:none;}")

        for wizard_page in (self.wizard_page1, self.wizard_page2, self.wizard_page3):
            wizard_page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        workflow_columns = QHBoxLayout()
        workflow_columns.setSpacing(10)
        columns = []
        column_layouts = []
        for unused in range(2):
            column = QWidget()
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setSpacing(8)
            column_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            columns.append(column)
            column_layouts.append(column_layout)
        fault = self.wizard_page2.fault_group
        self.wizard_page2.layout().removeWidget(fault)
        parts = self.wizard_page3.parts_group
        self.wizard_page3.layout().removeWidget(parts)
        hardware = QFrame()
        hardware.setObjectName("TechnicianHardwareSummary")
        hardware.setStyleSheet(theme_qss("QFrame#TechnicianHardwareSummary{background:@finance_surface;border:1px solid @finance_outline;border-radius:4px;}QLabel{background:transparent;border:none;color:@finance_text;}"))
        hardware_layout = QGridLayout(hardware)
        self.reference_hardware_layout = hardware_layout
        hardware_layout.setContentsMargins(6, 6, 6, 6)
        hardware_layout.setSpacing(2)
        device = self.device_dict
        self.reference_hardware_values = {}
        values = (
            ("CIHAZ MODELI", " ".join(str(device.get(key) or "") for key in ("device_brand", "device_model")).strip() or "-"),
            ("SERI NUMARASI", str(device.get("serial_no") or "-")),
            ("SERVIS TIPI", str(device.get("device_type") or self.technical_service_profile or "-")),
            ("KABUL TARIHI", str(device.get("entry_date") or "-")),
        )
        for index, (caption, value) in enumerate(values):
            block = QVBoxLayout()
            block.setSpacing(2)
            heading = QLabel(caption)
            heading.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:9px;font-weight:700;"))
            text = QLabel(value)
            text.setTextFormat(Qt.TextFormat.PlainText)
            text.setWordWrap(True)
            text.setToolTip(value)
            is_reference_value = caption in ("SERI NUMARASI", "KABUL TARIHI")
            text.setFont(QFont(DesignTokens.MONO_FONT_NAME if is_reference_value else DesignTokens.FONT_NAME, 9, QFont.Weight.Bold))
            text.setStyleSheet(theme_qss("color:@finance_text;font-size:11px;font-weight:700;"))
            if is_reference_value:
                text.setProperty("referenceFont", "mono")
                text.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9, QFont.Weight.Bold))
                QTimer.singleShot(0, lambda label=text: label.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9, QFont.Weight.Bold)))
            self.reference_hardware_values[caption] = text
            block.addWidget(heading)
            block.addWidget(text)
            hardware_layout.addLayout(block, 0, index)
            hardware_layout.setColumnStretch(index, 1)
        intake_card = QFrame()
        intake_card.setObjectName("TechnicianIntakeCard")
        intake_card.setStyleSheet(theme_qss("QFrame#TechnicianIntakeCard{background:@finance_surface;border:1px solid @finance_outline;border-radius:4px;}"))
        intake_layout = QVBoxLayout(intake_card)
        intake_layout.setContentsMargins(6, 6, 6, 6)
        intake_layout.setSpacing(4)
        hardware.setStyleSheet(theme_qss("QFrame#TechnicianHardwareSummary{background:transparent;border:none;}QLabel{background:transparent;border:none;color:@finance_text;}"))
        intake_layout.addWidget(hardware)
        column_layouts[0].addWidget(intake_card)
        self.wizard_page1.setVisible(True)
        intake_layout.addWidget(self.wizard_page1)
        if hasattr(self.wizard_page1, "pattern_button"):
            self.wizard_page1.pattern_button.setFixedHeight(24)
            self.wizard_page1.pattern_button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:0 6px;min-height:20px;font-size:10px;}"))
            pattern_layout = self.wizard_page1.layout().itemAt(0).layout()
            if pattern_layout is not None:
                pattern_layout.removeWidget(self.wizard_page1.pattern_button)
                self.wizard_page1.layout().removeItem(pattern_layout)
                pattern_layout.deleteLater()
            hardware_layout.addWidget(self.wizard_page1.pattern_button, 1, 2, 1, 2)
        for group in (self.wizard_page1.accessories_group, self.wizard_page1.photo_group):
            group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            group.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        for index in range(self.wizard_page1.layout().count()):
            nested = self.wizard_page1.layout().itemAt(index).layout()
            if isinstance(nested, QBoxLayout) and nested.count() > 1:
                nested.setDirection(QBoxLayout.Direction.TopToBottom)
                for child in range(nested.count()):
                    nested.setStretch(child, 0)
        column_layouts[0].addWidget(fault)
        column_layouts[1].addWidget(self.wizard_page2)
        self._reference_embedded_tests = False
        self.create_test_tab()
        self.test_loaded = True
        self.tabs.removeTab(1)
        self.tabs.insertTab(1, self.test_widget, " Test Uygulama ")
        column_layouts[1].addWidget(self.wizard_page3)
        column_layouts[1].addWidget(parts)
        self.wizard_page3.setObjectName("TechnicianServiceFinanceCard")
        self.wizard_page3.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.wizard_page3.setStyleSheet(theme_qss("QWidget#TechnicianServiceFinanceCard{background:@finance_surface;border:1px solid @finance_outline;border-radius:4px;}"))
        heading = self.wizard_page3.layout().itemAt(0).widget()
        if isinstance(heading, QLabel):
            heading.setText("SERVIS DURUMU, TESLIMAT VE FINANSAL HESAPLAMA")
            heading.setStyleSheet(theme_qss("color:@finance_text;font-size:10px;font-weight:700;border:none;background:transparent;"))
            heading.setFixedHeight(18)
        for index in range(self.wizard_page3.layout().count()):
            nested = self.wizard_page3.layout().itemAt(index).layout()
            if isinstance(nested, QBoxLayout):
                nested.setDirection(QBoxLayout.Direction.TopToBottom)
                for child in range(nested.count()):
                    nested.setStretch(child, 0)
        for group in (self.wizard_page3.status_group, self.wizard_page3.finance_group):
            group.setTitle("")
            group.setStyleSheet(theme_qss("QGroupBox{background:transparent;border:none;padding:0;margin-top:0;}"))
            group.layout().setContentsMargins(0, 0, 0, 0)
            group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            for index in range(group.layout().count()):
                grid = group.layout().itemAt(index).layout()
                if isinstance(grid, QGridLayout):
                    entries = []
                    while grid.count():
                        row, col, unused_row_span, unused_col_span = grid.getItemPosition(0)
                        entries.append((row, col, grid.takeAt(0)))
                    for row, col, item in entries:
                        if item.widget() is not None:
                            grid.addWidget(item.widget(), row % 2, col + 2 * (row // 2))
                            if isinstance(item.widget(), QLabel):
                                item.widget().setWordWrap(True)
                            else:
                                item.widget().setMinimumWidth(0)
                                item.widget().setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                    for col in range(4):
                        grid.setColumnStretch(col, 1)
        for group_name, grid_name in (("fault_group", "fault_grid"), ("process_group", "process_grid"), ("private_group", "private_grid")):
            group = getattr(self.wizard_page2, group_name, None)
            if group is not None and isinstance(group.layout(), QBoxLayout):
                group.layout().setDirection(QBoxLayout.Direction.TopToBottom)
                group.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
                for index in range(group.layout().count()):
                    group.layout().setStretch(index, 0)
            grid = getattr(self.wizard_page2, grid_name, None)
            if grid is not None:
                entries = []
                while grid.count():
                    entries.append(grid.takeAt(0))
                for row, entry in enumerate(entries):
                    widget = entry.widget()
                    if widget is not None:
                        grid.addWidget(widget, row, 0)
                        for label in widget.findChildren(QLabel):
                            label.setWordWrap(True)
            if group is not None and group.layout().count() > 1:
                right_item = group.layout().takeAt(1)
                quick_layout = right_item.layout()
                if quick_layout is not None:
                    quick_container = QWidget()
                    quick_layout.setParent(None)
                    quick_container.setLayout(quick_layout)
                    if quick_layout.count() and isinstance(quick_layout.itemAt(0).widget(), QLabel):
                        quick_layout.itemAt(0).widget().hide()
                    if group_name == "fault_group":
                        group.layout().addWidget(quick_container)
                    else:
                        group.layout().setDirection(QBoxLayout.Direction.LeftToRight)
                        group.layout().addWidget(quick_container)
                        group.layout().setStretch(0, 3)
                        group.layout().setStretch(1, 2)
        self.wizard_page2.layout().removeItem(self.wizard_page2.header_layout)
        fault.layout().insertLayout(0, self.wizard_page2.header_layout)
        fault.setTitle("")
        fault.setObjectName("TechnicianFaultCard")
        fault.setStyleSheet(theme_qss("QGroupBox#TechnicianFaultCard{background:@finance_surface;border:1px solid @finance_outline;border-radius:4px;padding:6px;margin-top:0;}"))
        for index in range(self.wizard_page2.header_layout.count()):
            control = self.wizard_page2.header_layout.itemAt(index).widget()
            if isinstance(control, QLabel):
                control.setStyleSheet(theme_qss("font-size:10px;font-weight:700;color:@finance_text;background:transparent;border:none;"))
            elif isinstance(control, QPushButton):
                control.setFixedSize(156, 30)
                control.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@accent;border:1px solid @finance_outline;border-radius:4px;padding:0 6px;min-height:22px;font-size:10px;}"))
        self.wizard_page2.txt_fault.setFixedHeight(56)
        self.wizard_page2.txt_public_notes.setFixedHeight(64)
        for editor in (self.wizard_page2.txt_fault, self.wizard_page2.txt_public_notes):
            editor.setStyleSheet(theme_qss("QPlainTextEdit{background:@finance_canvas;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:4px;font-size:11px;}"))
        part_layout = parts.layout()
        selection_item = part_layout.takeAt(0)
        selection_row = selection_item.layout()
        if selection_row is not None:
            selection_grid = QGridLayout()
            selection_grid.setSpacing(6)
            positions = tuple((0, index, 1, 1) for index in range(5))
            for position in positions:
                item = selection_row.takeAt(0)
                if item is not None and item.widget() is not None:
                    control = item.widget()
                    control.setMinimumWidth(0)
                    if isinstance(control, QPushButton):
                        control.setToolTip(control.text())
                        control.setText("Secileni Ekle" if position[1] == 2 else "Manuel")
                        control.setFixedWidth(100 if position[1] == 2 else 66)
                        control.setFixedHeight(28)
                        control.setStyleSheet(theme_qss("QPushButton{background:@accent;color:@selection_text;border:1px solid @finance_outline;border-radius:4px;padding:0 6px;min-height:24px;font-size:10px;}"))
                    elif position[1] == 3:
                        control.setFixedWidth(84)
                        control.setFixedHeight(28)
                        control.setToolTip(control.placeholderText())
                        control.setPlaceholderText("Barkod")
                    else:
                        control.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                        selection_grid.setColumnStretch(position[1], 1 if position[1] == 0 else 2)
                    selection_grid.addWidget(control, *position)
            part_layout.insertLayout(0, selection_grid)
        self.wizard_page3.table_used_parts.setFixedHeight(96)
        self.wizard_page3.table_used_parts.horizontalHeader().setFixedHeight(26)
        self.wizard_page3.table_used_parts.setStyleSheet(theme_qss("QTableWidget{background:@finance_canvas;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;}QHeaderView::section{background:@finance_surface_alt;color:@finance_text_muted;border:none;border-bottom:1px solid @finance_outline;padding:2px 4px;font-size:10px;font-weight:700;}QTableWidget::item{padding:2px 4px;}QTableWidget::item:selected{background:@finance_active_bg;color:@finance_text;}"))
        parts.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        parts.setObjectName("TechnicianPartsCard")
        parts.setStyleSheet(theme_qss("QGroupBox#TechnicianPartsCard{background:@finance_surface;border:1px solid @finance_outline;border-radius:4px;padding:6px;margin-top:12px;font-size:10px;}QGroupBox#TechnicianPartsCard::title{color:@finance_text;subcontrol-origin:margin;subcontrol-position:top left;left:8px;padding:0 4px;}"))
        self.wizard_page3.table_used_parts.verticalHeader().setDefaultSectionSize(32)
        self.wizard_page2.toggles_updated.connect(self._compact_reference_toggle_grids)
        self._compact_reference_toggle_grids()
        for column, stretch in zip(columns, (41, 59)):
            column_scroll = QScrollArea()
            column_scroll.setWidgetResizable(True)
            column_scroll.setFrameShape(QFrame.Shape.NoFrame)
            column_scroll.setStyleSheet(theme_qss("QScrollArea{background:@finance_canvas;border:none;}QScrollArea>QWidget>QWidget{background:@finance_canvas;}"))
            column_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            column_scroll.setWidget(column)
            workflow_columns.addWidget(column_scroll, stretch)
        self.general_content_layout.addLayout(workflow_columns, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)
        

    def _place_reference_test_panel(self, index):
        if not getattr(self, "_reference_embedded_tests", False):
            return
        if index == 1:
            self.reference_test_column.removeWidget(self.test_widget)
            self.reference_test_tab_layout.addWidget(self.test_widget)
            self.test_widget.setMinimumHeight(0)
            self.test_widget.setMaximumHeight(16777215)
        elif index == 0:
            self.reference_test_tab_layout.removeWidget(self.test_widget)
            self.reference_test_column.insertWidget(0, self.test_widget)
            self.test_widget.setFixedHeight(370)
        self.test_widget.show()

    def _compact_reference_toggle_grids(self):
        for group_name, grid_name in (("fault_group", "fault_grid"), ("process_group", "process_grid"), ("private_group", "private_grid")):
            group = getattr(self.wizard_page2, group_name, None)
            if group is not None:
                group.setMinimumHeight(0)
                group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                group_layout = group.layout()
                if group_layout is not None:
                    for index in range(group_layout.count()):
                        nested = group_layout.itemAt(index).layout()
                        if nested is not None:
                            nested.setAlignment(Qt.AlignmentFlag.AlignTop)
                            if isinstance(nested, QBoxLayout):
                                for child in range(nested.count()):
                                    nested.setStretch(child, 0)
                                    child_widget = nested.itemAt(child).widget()
                                    if isinstance(child_widget, QLabel):
                                        child_widget.setFixedHeight(18)
                                    if child_widget is not None:
                                        nested.setAlignment(child_widget, Qt.AlignmentFlag.AlignTop)
            grid = getattr(self.wizard_page2, grid_name, None)
            if grid is None:
                continue
            entries = []
            while grid.count():
                entries.append(grid.takeAt(0))
            columns = 1 if grid_name == "process_grid" else 2
            grid.setVerticalSpacing(4)
            if grid.parentWidget() is not None:
                frame = grid.parentWidget()
                rows = max(1, (len(entries) + columns - 1) // columns)
                frame.setFixedHeight(rows * 28 + max(0, rows - 1) * grid.verticalSpacing() + 8)
                frame.setStyleSheet(theme_qss("QFrame{background:transparent;border:none;}"))
            for row, entry in enumerate(entries):
                widget = entry.widget()
                if widget is not None:
                    grid.addWidget(widget, row // columns, row % columns)
                    widget.setFixedHeight(28)
                    widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                    widget.setStyleSheet(theme_qss("QWidget#ClassicQuickToggleItem{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;}"))
                    if widget.layout() is not None:
                        widget.layout().setContentsMargins(4, 2, 4, 2)
                        widget.layout().setSpacing(4)
                    for label in widget.findChildren(QLabel):
                        label.setWordWrap(True)
                        label.setStyleSheet(theme_qss("color:@finance_text;background:transparent;border:none;font-size:10px;"))
                    for toggle in widget.findChildren(AnimatedToggle):
                        toggle.setFixedSize(18, 18)
                        toggle.setProperty("referenceCheckbox", True)

    def create_test_tab(self):
        self.test_widget = QWidget()
        self.test_widget.setObjectName("TechnicianPanelTest")
        layout = QVBoxLayout(self.test_widget)

        header = QVBoxLayout() if getattr(self, "_reference_embedded_tests", False) else QHBoxLayout()
        test_title = "Ara\u00e7 Kontrol ve Test Formu" if self._is_automotive() else "Cihaz Kontrol & Test Formu"
        self.test_header = QLabel(test_title)
        self.test_header.setWordWrap(True)
        self.test_header.setFont(QFont(DesignTokens.FONT_NAME, 12, QFont.Weight.Bold))
        header.addWidget(self.test_header)
        if not getattr(self, "_reference_embedded_tests", False):
            header.addStretch()
        else:
            header.setSpacing(4)
        
        btn_edit = QPushButton("Testleri D\u00fczenle")
        btn_edit.setFixedWidth(140)
        btn_edit.setFixedHeight(28)
        btn_edit.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        if getattr(self, "_reference_embedded_tests", False):
            btn_edit.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:0 6px;min-height:24px;font-size:10px;}"))
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
        
        col_count = 1 if getattr(self, "_reference_embedded_tests", False) else 3
        for idx, (label, is_visible) in enumerate(test_items):
            if not is_visible:
                continue
            
            row = idx // col_count
            col = idx % col_count
            
            item_widget = QFrame()
            item_widget.setObjectName("ClassicQuickToggleItem")
            item_widget.setMinimumHeight(42)
            item_widget.setStyleSheet(theme_qss("""
                QFrame { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 4px; }
            """))
            item_lay = QHBoxLayout(item_widget)
            item_lay.setContentsMargins(10, 8, 10, 8)
            
            lbl = QLabel(label)
            lbl.setFont(QFont(DesignTokens.FONT_NAME, 9))
            lbl.setWordWrap(True)
            
            toggle = AnimatedToggle()
            toggle.setFixedSize(18, 18)
            toggle.setProperty("referenceCheckbox", True)
            if label.upper() in active_items:
                toggle.setChecked(True)
            
            toggle.toggled.connect(lambda checked, n=label: self._handle_toggle_changed(n, checked))
            
            item_lay.addWidget(lbl, 1)
            item_lay.addWidget(toggle)
            self.test_grid.addWidget(item_widget, row, col)
            self.test_toggles.append((label, toggle))
        self.test_grid.setRowStretch((len(test_items)//col_count)+1, 1)
        if getattr(self, "read_only", False):
            self._apply_read_only_mode(self.test_widget)
        self._schedule_classic_panel_styles()
