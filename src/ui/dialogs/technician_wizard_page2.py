
# -*- coding: utf-8 -*-

"""
Wizard Page 2: Fault Details and Quick Notes
Part of the modernized Technician Panel wizard interface
Includes categorized toggle switches and edit functionality
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
                             QPushButton, QFrame, QGroupBox, QLineEdit, QDialog, QPlainTextEdit, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import re
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.modern_inputs import ValidatedLineEdit
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.logger import logger
from src.utils.system_config import SystemConfig
from src.utils.automotive_defaults import AUTOMOTIVE_FAULT_CATEGORY, AUTOMOTIVE_PROCESS_CATEGORY, AUTOMOTIVE_PRESET
from src.utils.technical_service_profiles import (
    build_profile_category,
    get_profile_labels,
    normalize_technical_service_profile,
)



class TechnicianWizardPage2(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """Page 2: Fault Details and Quick Notes with categorized toggles"""
    
    toggles_updated = pyqtSignal()  # Signal to refresh toggles after edit
    
    def __init__(self, db, tracking_no, device_dict, parent=None, sector_manager=None):
        super().__init__(parent)
        self.db = db
        self.sector_manager = sector_manager
        self.tracking_no = tracking_no
        self.device_dict = device_dict
        self.parent_dialog = parent
        
        # Storage for dynamic toggles
        self.fault_toggles = []  # [(text, toggle_widget), ...]
        self.process_toggles = []
        self.private_toggles = []
        self.fault_grid = None
        self.process_grid = None
        self.private_grid = None
        
        # Get existing data
        self.fault_desc = device_dict.get('fault_description', '')
        self.repair_details = device_dict.get('repair_details', '')
        self.internal_notes = device_dict.get('internal_notes', '')
        self.checklist_status = device_dict.get('checklist_status', '')
        self.fault_quick_category = self._fault_category()
        if not self.checklist_status and self.parent_dialog and hasattr(self.parent_dialog, "get_cached_checklist_status"):
            cached = self.parent_dialog.get_cached_checklist_status()
            if cached:
                self.checklist_status = cached
        
        self.setup_ui()

        self._wire_ui_signals()
    def _is_automotive(self):
        try:
            if self.parent_dialog and hasattr(self.parent_dialog, "_is_automotive"):
                return bool(self.parent_dialog._is_automotive())
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _process_category(self):
        if self._is_automotive():
            return AUTOMOTIVE_PROCESS_CATEGORY
        return build_profile_category(self._technical_service_profile(), "\u0130\u015flem Detay\u0131")
        
    def _technical_service_profile(self):
        if self.parent_dialog and hasattr(self.parent_dialog, "get_technical_service_profile"):
            return self.parent_dialog.get_technical_service_profile()
        return normalize_technical_service_profile(self.device_dict.get("device_type"))

    def _fault_category(self):
        if self._is_automotive():
            return AUTOMOTIVE_FAULT_CATEGORY
        return build_profile_category(self._technical_service_profile(), "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi")

    def _private_category(self):
        if self._is_automotive():
            return "Gizli Not"
        return build_profile_category(self._technical_service_profile(), "Gizli Not")

    def _is_classic_appearance(self):
        parent_dialog = getattr(self, "parent_dialog", None) or self.parent()
        if parent_dialog and not hasattr(parent_dialog, "_is_classic_appearance") and hasattr(parent_dialog, "parent") and parent_dialog.parent():
            parent_dialog = parent_dialog.parent()
        return bool(
            parent_dialog
            and hasattr(parent_dialog, "_is_classic_appearance")
            and parent_dialog._is_classic_appearance()
        )

    def _classic_group_qss(self):
        return """
            QGroupBox {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                margin-top: 12px;
                padding: 18px 8px 8px 8px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                padding: 0 4px;
                background: #FFFFFF;
                color: #111827;
            }
            QGroupBox QWidget {
                background: #FFFFFF;
                color: #111827;
            }
            QGroupBox QLabel {
                background: transparent;
                color: #111827;
                border: none;
            }
        """

    def _classic_input_qss(self):
        return """
            QLineEdit, QPlainTextEdit {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #AEB4BD;
                border-radius: 2px;
                padding: 5px 7px;
                selection-background-color: #DCEBFF;
                selection-color: #111827;
            }
            QLineEdit:focus, QPlainTextEdit:focus {
                border-color: #1F4E79;
                background: #FFFFFF;
            }
        """

    def _classic_toggle_item_qss(self):
        return """
            QWidget#ClassicQuickToggleItem {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 0px;
            }
            QWidget#ClassicQuickToggleItem QLabel {
                background: transparent;
                color: #111827;
                border: none;
            }
        """

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 2)
        main_layout.setSpacing(8)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Header with Edit button
        self.header_layout = self.create_header_with_edit_button()
        main_layout.addLayout(self.header_layout)
        
        self.fault_group = self.create_fault_notes_section()
        self.fault_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        main_layout.addWidget(self.fault_group)
        
        self.process_group = self.create_process_notes_section()
        self.process_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        main_layout.addWidget(self.process_group)
        
        self.private_group = self.create_private_notes_section()
        self.private_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        main_layout.addWidget(self.private_group)
    
    def _wire_ui_signals(self):
        self.btn_private_eye.clicked.connect(self._on_ui_widget_changed)

    def create_header_with_edit_button(self):
        """Create page header with edit button"""
        header = QHBoxLayout()
        header.setSpacing(12)
        
        # Title
        title = QLabel("Ar\u0131za ve \u0130\u015flem Detaylar\u0131")
        title.setText("Ariza ve Islem Detaylari")
        title.setFont(QFont(DesignTokens.FONT_FAMILY, 12, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; border: none; background: transparent; font-weight: bold;"))
        
        # Edit button
        btn_edit = QPushButton("\u270f Toggle-Switch D\u00fczenle")
        btn_edit.setFixedHeight(36)
        btn_edit.setText("Toggle Duzenle")
        btn_edit.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        btn_edit.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: {DesignTokens.ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: @accent_hover;
            }}
            QPushButton:pressed {{
                background-color: @accent_pressed;
            }}
        """))
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.clicked.connect(self.open_quick_notes_editor)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_edit)
        
        return header
    
    def create_fault_notes_section(self):
        """Create fault notes section with text input and toggles side-by-side"""
        group = QGroupBox("\U0001f527 Ar\u0131za Notu ve Tan\u0131m\u0131")
        group.setTitle("Ariza Notu ve Tanimi")
        if self._is_automotive():
            group.setTitle("Ara\u00e7 Ar\u0131za / M\u00fc\u015fteri \u015eikayeti")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        group.setStyleSheet(theme_qss(f"""
            QGroupBox {{
                background: transparent;
                border: none;
                border-top: 1px solid {DesignTokens.BORDER};
                border-radius: 0;
                padding: 4px 0 0 0;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                padding: 0 8px 4px 0;
                color: {DesignTokens.FOREGROUND};
            }}
        """))

        h_layout = QHBoxLayout(group)
        h_layout.setContentsMargins(0, 6, 0, 0)
        h_layout.setSpacing(15)

        # Left column (Text input)
        left_v = QVBoxLayout()
        left_v.setSpacing(6)
        label = QLabel("Ar\u0131za Tan\u0131m\u0131:")
        label.setText("Ariza Tanimi:")
        label.setFont(QFont(DesignTokens.FONT_FAMILY, 9))
        label.setStyleSheet(theme_qss("color: @text; font-weight: bold; border: none; background: transparent;"))
        left_v.addWidget(label)
        
        self.txt_fault = QPlainTextEdit()
        self.txt_fault.setPlaceholderText("Ar\u0131za tan\u0131m\u0131...")
        self.txt_fault.setPlainText(str(self.fault_desc or ""))
        self.txt_fault.setStyleSheet(theme_qss(f"color: @text; border: 1px solid {DesignTokens.BORDER}; border-radius: 8px; padding: 8px;"))
        self.txt_fault.setMinimumHeight(80)
        self.txt_fault.setAccessibleName("ar\u0131za_tan\u0131m\u0131_giri\u015fi")
        left_v.addWidget(self.txt_fault)
        h_layout.addLayout(left_v, 50)

        # Right column (Toggles)
        right_v = QVBoxLayout()
        right_v.setSpacing(6)
        r_label = QLabel("H\u0131zl\u0131 Se\u00e7im:")
        r_label.setFont(QFont(DesignTokens.FONT_FAMILY, 9))
        r_label.setStyleSheet(theme_qss("color: @text; font-weight: bold; border: none; background: transparent;"))
        right_v.addWidget(r_label)

        self.fault_grid = QGridLayout()
        self.fault_grid.setSpacing(6)
        self.fault_grid.setHorizontalSpacing(10)
        self.load_category_toggles(self.fault_quick_category, self.fault_grid, self.fault_toggles, target_widget=self.txt_fault)
        
        right_v.addWidget(self._create_toggle_grid_frame(self.fault_grid, len(self.fault_toggles)))
        h_layout.addLayout(right_v, 50)

        return group
    
    def create_process_notes_section(self):
        """Create process/customer notes section and its quick selects side-by-side"""
        group = QGroupBox("\U0001f4ac \u0130\u015flem Detay\u0131 (M\u00fc\u015fteri \u0130\u00e7in)")
        group.setTitle("Islem Detayi (Musteri Icin)")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        group.setStyleSheet(theme_qss(f"""
            QGroupBox {{
                background: transparent;
                border: none;
                border-top: 1px solid @accent;
                border-radius: 0;
                padding: 4px 0 0 0;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                padding: 0 8px 4px 0;
                color: @accent;
            }}
        """))

        h_layout = QHBoxLayout(group)
        h_layout.setContentsMargins(0, 6, 0, 0)
        h_layout.setSpacing(15)

        # Left column (Text input)
        left_v = QVBoxLayout()
        left_v.setSpacing(6)
        label = QLabel("M\u00fc\u015fteriye G\u00f6sterilecek Not:")
        label.setText("Musteriye Gosterilecek Not:")
        label.setFont(QFont(DesignTokens.FONT_FAMILY, 9))
        label.setStyleSheet(theme_qss("color: @accent; border: none; background: transparent;"))
        left_v.addWidget(label)
        
        self.txt_public_notes = QPlainTextEdit()
        self.txt_public_notes.setPlaceholderText("M\u00fc\u015fteri i\u00e7in not...")
        self.txt_public_notes.setPlainText(str(self.repair_details or ""))
        self.txt_public_notes.setStyleSheet(theme_qss(f"color: @text; border: 1px solid {DesignTokens.BORDER}; border-radius: 8px; padding: 8px;"))
        self.txt_public_notes.setMinimumHeight(80)
        self.txt_public_notes.setAccessibleName("m\u00fc\u015fteri_notu_giri\u015fi")
        left_v.addWidget(self.txt_public_notes)
        h_layout.addLayout(left_v, 50)

        # Right column (Toggles)
        right_v = QVBoxLayout()
        right_v.setSpacing(6)
        r_label = QLabel("H\u0131zl\u0131 Se\u00e7im:")
        r_label.setFont(QFont(DesignTokens.FONT_FAMILY, 9))
        r_label.setStyleSheet(theme_qss("color: @accent; font-weight: bold; border: none; background: transparent;"))
        right_v.addWidget(r_label)

        self.process_grid = QGridLayout()
        self.process_grid.setSpacing(6)
        self.process_grid.setHorizontalSpacing(10)
        self.load_category_toggles(self._process_category(), self.process_grid, self.process_toggles, target_widget=self.txt_public_notes)

        right_v.addWidget(self._create_toggle_grid_frame(self.process_grid, len(self.process_toggles)))
        h_layout.addLayout(right_v, 50)

        return group
    
    def create_private_notes_section(self):
        """Create private/technical notes section and its quick selects side-by-side"""
        group = QGroupBox("\U0001f512 Teknik / Gizli Not (Sadece Personel)")
        group.setTitle("Teknik / Gizli Not")
        group.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        group.setStyleSheet(theme_qss(f"""
            QGroupBox {{
                background: transparent;
                border: none;
                border-top: 1px solid @warning;
                border-radius: 0;
                padding: 4px 0 0 0;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                padding: 0 8px 4px 0;
                color: @warning;
            }}
        """))

        h_layout = QHBoxLayout(group)
        h_layout.setContentsMargins(0, 6, 0, 0)
        h_layout.setSpacing(15)

        # Left column (Text input)
        left_v = QVBoxLayout()
        left_v.setSpacing(6)
        label = QLabel("Dahili Notlar:")
        label.setFont(QFont(DesignTokens.FONT_FAMILY, 9))
        label.setStyleSheet(theme_qss("color: @warning; border: none; background: transparent;"))
        left_v.addWidget(label)
        
        self.txt_private_notes = ValidatedLineEdit("Dahili notlar...")
        self.txt_private_notes.setText(str(self.internal_notes or ""))
        self.txt_private_notes.setStyleSheet(theme_qss("color: @text;"))
        self.txt_private_notes.setAccessibleName("dahili_not_giri\u015fi")
        self.txt_private_notes.setMinimumHeight(32)
        try:
            self.txt_private_notes.setEchoMode(QLineEdit.EchoMode.Password)
        except Exception:
            pass
        
        notes_row = QHBoxLayout()
        notes_row.setContentsMargins(0, 0, 0, 0)
        notes_row.setSpacing(6)
        notes_row.addWidget(self.txt_private_notes)
        
        self.btn_private_eye = QPushButton("\U0001f441")
        self.btn_private_eye.setFixedSize(36, 32)
        self.btn_private_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_private_eye.setCheckable(True)
        self.btn_private_eye.setToolTip("Dahili notu g\u00f6ster/gizle")
        self.btn_private_eye.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @warning_bg;
                border-radius: 8px;
                border: 1px solid @warning;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: @warning;
            }
            QPushButton:pressed {
                background-color: @warning;
            }
        """))
        self.btn_private_eye.toggled.connect(self._toggle_private_notes_visibility)
        notes_row.addWidget(self.btn_private_eye)
        
        left_v.addLayout(notes_row)
        left_v.addStretch()
        h_layout.addLayout(left_v, 50)

        # Right column (Toggles)
        right_v = QVBoxLayout()
        right_v.setSpacing(6)
        r_label = QLabel("Gizli Not H\u0131zl\u0131 Se\u00e7im:")
        r_label.setFont(QFont(DesignTokens.FONT_FAMILY, 9, QFont.Weight.DemiBold))
        r_label.setStyleSheet(theme_qss("color: @warning; border: none; background: transparent;"))
        right_v.addWidget(r_label)

        self.private_grid = QGridLayout()
        self.private_grid.setSpacing(6)
        self.private_grid.setHorizontalSpacing(10)
        self.load_category_toggles(self._private_category(), self.private_grid, self.private_toggles, target_widget=self.txt_private_notes)

        right_v.addWidget(self._create_toggle_grid_frame(self.private_grid, len(self.private_toggles)))
        h_layout.addLayout(right_v, 50)

        return group
    
    def _toggle_frame_height(self, item_count):
        rows = max(1, (max(0, item_count) + 1) // 2)
        return max(56, (rows * 44) + 18)

    def _fallback_toggle_labels(self, category):
        raw = str(category or "")
        base = raw.split("::")[-1]
        labels = get_profile_labels(self._technical_service_profile(), base)
        if labels:
            return labels
        key = raw.casefold()
        if "gizli" in key:
            return ["TEST OK", "VERI YEDEKLENDI", "SIVI TEMASI SUPHELI", "ACIL TESLIM"]
        if "islem" in key or "detay" in key:
            return ["FORMAT ATILDI", "PARCA DEGISTI", "TEMIZLIK YAPILDI", "TEST EDILIYOR", "ONAY BEKLIYOR"]
        if "test" in key:
            return ["LCD GORUNTU", "ACILIS", "KLAVYE", "TOUCHPAD", "USB PORTLARI", "FAN / SOGUTMA"]
        return [
            "GORUNTU YOK",
            "ACILMIYOR",
            "SARJ OLMUYOR",
            "ISINMA / FAN SESI",
            "YAVAS CALISIYOR",
            "MAVI EKRAN",
            "KLAVYE CALISMIYOR",
            "PORT / SOKET SORUNU",
        ]

    def _create_toggle_grid_frame(self, grid_layout, item_count=0):
        frame = QFrame()
        if self._is_classic_appearance():
            frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #B8C0CC; border-radius: 0px; }")
        else:
            frame.setStyleSheet(theme_qss(f"QFrame {{ background: @surface; border: 1px solid {DesignTokens.BORDER}; border-radius: 8px; }}"))
        frame.setMinimumHeight(self._toggle_frame_height(item_count))
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(6, 4, 6, 4)
        f_layout.addLayout(grid_layout)
        return frame
    
    def load_category_toggles(self, category, grid_layout, storage_list, target_widget=None):
        """Load toggles for a specific category from database"""
        try:
            notes = self.db.get_fast_notes(category) or []
            if not notes and not self._is_automotive() and category.startswith("Teknik Servis::"):
                base_category = category.split("::")[-1]
                notes = [{"label": label, "is_active": 1} for label in get_profile_labels(self._technical_service_profile(), base_category)]
            if self._is_automotive() and not notes and category in AUTOMOTIVE_PRESET:
                notes = [{"label": label, "is_active": 1} for label in AUTOMOTIVE_PRESET[category]]
            if category == "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi" and not notes:
                notes = self.db.get_fast_notes("Ar\u0131za Notu") or []

            def _note_value(note, key, index, default=None):
                if isinstance(note, dict):
                    return note.get(key, default)
                try:
                    if hasattr(note, "keys") and key in note.keys():
                        return note[key]
                except Exception:
                    pass
                try:
                    return note[index]
                except Exception:
                    return default

            def _is_active(note):
                val = _note_value(note, "is_active", 3, 1)
                try:
                    return int(val) == 1
                except Exception:
                    return bool(val)

            active_notes = [n for n in notes if _is_active(n)]
            if not active_notes:
                active_notes = notes
            if not active_notes:
                active_notes = [
                    {"label": label, "is_active": 1}
                    for label in self._fallback_toggle_labels(category)
                ]
            
            # Get saved checklist items from target_widget if provided, otherwise from checklist_status
            saved_items = []
            if target_widget is not None:
                current_text = target_widget.toPlainText() if hasattr(target_widget, "toPlainText") else target_widget.text()
                saved_items = [s.strip().upper() for s in str(current_text or "").split(',') if s.strip()]
            elif self.checklist_status and isinstance(self.checklist_status, str):
                saved_items = [s.strip().upper() for s in self.checklist_status.split(',') if s.strip()]
            
            row, col = 0, 0
            for note in active_notes:
                label_text = str(_note_value(note, "label", 2, "") or "").strip()
                if not label_text:
                    continue
                is_checked = label_text.upper() in saved_items
                
                toggle_widget = self.create_toggle_item(label_text, is_checked)
                grid_layout.addWidget(toggle_widget, row, col)
                
                # Store for later retrieval
                toggle = toggle_widget.findChild(AnimatedToggle)
                storage_list.append((label_text, toggle))
                if target_widget is not None and toggle is not None:
                    toggle.toggled.connect(lambda c, t=label_text, w=target_widget: self._sync_text_with_toggle(w, t, c))
                if toggle is not None:
                    toggle.toggled.connect(self._handle_toggle_state_change)
                
                col += 1
                if col >= 2:  # 2 columns
                    col = 0
                    row += 1
                    
        except Exception as e:
            logger.error(f"TechnicianWizardPage2 toggle load error for {category}: {e}")
            # Fallback defaults
            defaults = {
                "Ar\u0131za Notu": ["G\u00d6R\u00dcNT\u00dc YOK", "A\u00c7ILMIYOR", "\u015eARJ OLMUYOR", "ISINMA / FAN SES\u0130"],
                "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi": ["G\u00d6R\u00dcNT\u00dc YOK", "A\u00c7ILMIYOR", "\u015eARJ OLMUYOR", "ISINMA / FAN SES\u0130", "YAVA\u015e \u00c7ALI\u015eIYOR", "MAV\u0130 EKRAN", "KLAVYE \u00c7ALI\u015eMIYOR", "PORT / SOKET SORUNU"],
                "\u0130\u015flem Detay\u0131": ["FORMAT ATILDI", "PAR\u00c7A DE\u011e\u0130\u015eT\u0130", "TEM\u0130ZL\u0130K YAPILDI", "TEST ED\u0130L\u0130YOR"],
                "Gizli Not": ["TEST OK", "VER\u0130 YEDEKLEND\u0130", "SIVI TEMASI \u015e\u00dcPHEL\u0130", "AC\u0130L TESL\u0130M"]
            }
            
            # Recompute saved_items if needed in case try-block failed before defining it
            saved_items = []
            if target_widget is not None:
                current_text = target_widget.toPlainText() if hasattr(target_widget, "toPlainText") else target_widget.text()
                saved_items = [s.strip().upper() for s in str(current_text or "").split(',') if s.strip()]

            if self._is_automotive():
                defaults.update(AUTOMOTIVE_PRESET)
            if category in defaults:
                row, col = 0, 0
                for label_text in defaults[category]:
                    is_checked = label_text.upper() in saved_items
                    toggle_widget = self.create_toggle_item(label_text, is_checked)
                    grid_layout.addWidget(toggle_widget, row, col)
                    toggle = toggle_widget.findChild(AnimatedToggle)
                    storage_list.append((label_text, toggle))
                    if target_widget is not None and toggle is not None:
                        toggle.toggled.connect(lambda c, t=label_text, w=target_widget: self._sync_text_with_toggle(w, t, c))
                    if toggle is not None:
                        toggle.toggled.connect(self._handle_toggle_state_change)
                    
                    col += 1
                    if col >= 2:
                        col = 0
                        row += 1
    def create_toggle_item(self, text, checked=False):
        """Create a single toggle switch item"""
        container = QWidget()
        container.setObjectName("ClassicQuickToggleItem")
        container.setFixedHeight(38)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        container.setStyleSheet(
            self._classic_toggle_item_qss()
            if self._is_classic_appearance()
            else theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 8px;")
        )
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(8, 4, 8, 4)
        h_layout.setSpacing(8)
        
        # Toggle switch
        toggle = AnimatedToggle()
        toggle.setFixedSize(46, 24)
        toggle.setChecked(checked)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setAccessibleName(f"toggle_{text.lower().replace(' ', '_')}")
        
        # Label
        label = QLabel(text)
        label.setFont(QFont(DesignTokens.FONT_FAMILY, 10))
        label.setStyleSheet(
            "color: #111827; background: transparent; border: none; margin-left: 4px;"
            if self._is_classic_appearance()
            else theme_qss(f"color: {DesignTokens.FOREGROUND}; background: transparent; border: none; margin-left: 8px;")
        )
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        label.mousePressEvent = lambda event, t=toggle: t.toggle()
        label.setAccessibleName(f"etiket_{text.lower().replace(' ', '_')}")
        
        h_layout.addWidget(toggle)
        h_layout.addWidget(label)
        h_layout.addStretch()
        
        return container

    def _handle_toggle_state_change(self, checked):
        self._update_checklist_status()
    def apply_classic_styles(self):
        if not self._is_classic_appearance():
            return
        self.setProperty("skipThemeTransform", False)
        self.setStyleSheet("QWidget { background: #F3F4F6; color: #111827; } QLabel { background: transparent; color: #111827; border: none; }")
        for group in self.findChildren(QGroupBox):
            group.setProperty("skipThemeTransform", False)
            group.setStyleSheet(self._classic_group_qss())
        for editor in self.findChildren(QPlainTextEdit):
            editor.setProperty("skipThemeTransform", False)
            editor.setStyleSheet(self._classic_input_qss())
            editor.viewport().setProperty("skipThemeTransform", False)
            editor.viewport().setStyleSheet("background: #FFFFFF; color: #111827; border: none;")
        for editor in self.findChildren(QLineEdit):
            editor.setProperty("skipThemeTransform", False)
            editor.setStyleSheet(self._classic_input_qss())
        for item in self.findChildren(QWidget, "ClassicQuickToggleItem"):
            item.setProperty("skipThemeTransform", False)
            item.setStyleSheet(self._classic_toggle_item_qss())
        for frame in self.findChildren(QFrame):
            frame.setProperty("skipThemeTransform", False)
            frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #B8C0CC; border-radius: 0px; }")
        for label in self.findChildren(QLabel):
            label.setProperty("skipThemeTransform", False)
            label.setStyleSheet("color: #111827; background: transparent; border: none;")
        for button in self.findChildren(QPushButton):
            button.setProperty("skipThemeTransform", False)
            button.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF;
                    color: #111827;
                    border: 1px solid #AEB4BD;
                    border-radius: 2px;
                    padding: 5px 10px;
                    font-weight: 700;
                }
                QPushButton:hover { background: #F3F4F6; border-color: #1F4E79; }
            """)

    def _update_checklist_status(self):
        items = []
        for toggle_list in (self.fault_toggles, self.process_toggles, self.private_toggles):
            for text, toggle in toggle_list:
                if toggle is not None and toggle.isChecked():
                    items.append(text)
        self.checklist_status = ", ".join(items)
        if self.parent_dialog and hasattr(self.parent_dialog, "_persist_toggle_state"):
            self.parent_dialog._persist_toggle_state(self.checklist_status)

    def open_quick_notes_editor(self):
        """Open quick notes editor"""
        from src.ui.dialogs.quick_notes_editor import QuickNotesEditor
        try:
            editor = QuickNotesEditor(
                self.db,
                self.parent_dialog,
                initial_category=self.fault_quick_category,
                sector_manager=getattr(self, "sector_manager", None),
                profile_name=None if self._is_automotive() else self._technical_service_profile(),
            )
        except TypeError:
            editor = QuickNotesEditor(self.db, self.parent_dialog, initial_category=self.fault_quick_category)
        try:
            editor.exec()
        finally:
            try:
                self.reload_toggles()
            except Exception:
                pass

    def _toggle_private_notes_visibility(self, visible):
        try:
            if visible:
                self.txt_private_notes.setEchoMode(QLineEdit.EchoMode.Normal)
            else:
                self.txt_private_notes.setEchoMode(QLineEdit.EchoMode.Password)
        except Exception:
            pass

    def _sync_text_with_toggle(self, widget, text, checked):
        try:
            is_plain_edit = hasattr(widget, "toPlainText")
            current_val = widget.toPlainText() if is_plain_edit else widget.text()
            current_val = str(current_val or "").strip()
            
            existing_items = [x.strip() for x in current_val.split(",") if x.strip()]
            
            target_upper = text.strip().upper()
            match_index = -1
            for idx, item in enumerate(existing_items):
                if item.upper() == target_upper:
                    match_index = idx
                    break
            
            if checked:
                if match_index == -1:
                    existing_items.append(text.strip())
            else:
                if match_index != -1:
                    existing_items.pop(match_index)
            
            new_val = ", ".join(existing_items)
            
            if is_plain_edit:
                widget.setPlainText(new_val)
            else:
                widget.setText(new_val)
        except Exception as e:
            logger.error(f"Error in _sync_text_with_toggle: {e}")
    
    def reload_toggles(self):
        """Reload all toggles from database"""
        self.fault_quick_category = self._fault_category()
        self._refresh_checklist_from_toggles()
        self._clear_layout(self.fault_grid)
        self._clear_layout(self.process_grid)
        self._clear_layout(self.private_grid)
        
        self.fault_toggles.clear()
        self.process_toggles.clear()
        self.private_toggles.clear()
        
        if self.fault_grid is not None:
            self.load_category_toggles(self.fault_quick_category, self.fault_grid, self.fault_toggles, target_widget=self.txt_fault)
            fault_parent = self.fault_grid.parentWidget()
            if fault_parent:
                fault_parent.setMinimumHeight(self._toggle_frame_height(len(self.fault_toggles)))
                fault_parent.update()
                fault_parent.adjustSize()
        if self.process_grid is not None:
            process_category = self._process_category()
            if not self._is_automotive():
                process_category = build_profile_category(self._technical_service_profile(), "\u0130\u015flem Detay\u0131")
            self.load_category_toggles(process_category, self.process_grid, self.process_toggles, target_widget=self.txt_public_notes)
            process_parent = self.process_grid.parentWidget()
            if process_parent:
                process_parent.setMinimumHeight(self._toggle_frame_height(len(self.process_toggles)))
                process_parent.update()
                process_parent.adjustSize()
        if self.private_grid is not None:
            self.load_category_toggles(self._private_category(), self.private_grid, self.private_toggles, target_widget=self.txt_private_notes)
            private_parent = self.private_grid.parentWidget()
            if private_parent:
                private_parent.setMinimumHeight(self._toggle_frame_height(len(self.private_toggles)))
                private_parent.update()
                private_parent.adjustSize()
        
        self._update_checklist_status()
        self.toggles_updated.emit()
    
    def _refresh_checklist_from_toggles(self):
        items = []
        for toggle_list in (self.fault_toggles, self.process_toggles, self.private_toggles):
            for text, toggle in toggle_list:
                if toggle is not None and toggle.isChecked():
                    items.append(text)
        if items:
            self.checklist_status = ", ".join(items)

    def _clear_layout(self, layout):
        if not layout:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
    
    def get_data(self):
        """Collect data from this page"""
        # Collect all checked toggle items
        checklist_items = []
        
        for text, toggle in self.fault_toggles:
            if toggle.isChecked():
                checklist_items.append(text)
        
        for text, toggle in self.process_toggles:
            if toggle.isChecked():
                checklist_items.append(text)
        
        for text, toggle in self.private_toggles:
            if toggle.isChecked():
                checklist_items.append(text)
        
        return {
            'fault_description': self.txt_fault.toPlainText(),
            'repair_details': self.txt_public_notes.toPlainText(),
            'internal_notes': self.txt_private_notes.text(),
            'checklist_status': ','.join(checklist_items)
        }
