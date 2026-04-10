from PyQt6.QtWidgets import (QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTabWidget, QWidget, QScrollArea,
                             QGridLayout, QLineEdit, QDateEdit, QTableWidget,
                             QHeaderView, QListView, QTableWidgetItem, QTextEdit,
                             QPlainTextEdit, QGroupBox, QApplication, QSizePolicy)
from PyQt6.QtCore import Qt, QDate, QRect, QPropertyAnimation, QEasingCurve, QTimer, QPoint, pyqtSlot, QMetaObject, Q_ARG, QSettings
from PyQt6.QtGui import QFont, QColor, QBrush, QTextDocument, QPixmap, QAction, QPainter, QPainterPath
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.utils.validators import Validators
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.pattern_lock import PatternLockWidget
from src.utils.ai_service import AIService
from src.utils.audit_logger import get_audit_logger
from src.utils.logger import logger
from src.utils.voice_worker import VoiceWorker
from src.utils.toast_notification import show_success, show_error, show_warning, show_info, show_toast
from src.utils.currency_helper import CurrencyHelper
from src.ui.dialogs.device_history_dialog import DeviceHistoryDialog
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.dialogs.technician_panel_inventory_mixin import TechnicianPanelInventoryMixin
from src.ui.dialogs.technician_panel_components import add_field, ImageGalleryDialog, ModernManualProductDialog

import threading
import os
from datetime import datetime

class TechnicianPanel(TechnicianPanelInventoryMixin, ModernDialog):
    _session_toggle_cache = {}

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_try_for_display(
            amount,
            db=self.db,
            include_try_reference=include_try_reference,
        )

    def __init__(self, db, device_data, parent=None):
        self.db = db
        tracking_no = None
        if isinstance(device_data, dict):
            tracking_no = device_data.get("tracking_no")
        else:
            try:
                if hasattr(device_data, "keys") and "tracking_no" in device_data.keys():
                    tracking_no = device_data["tracking_no"]
            except Exception:
                pass
        if tracking_no is None:
            try:
                tracking_no = device_data[1]
            except Exception:
                tracking_no = ""
        self.tracking_no = tracking_no
        title = f"Teknisyen Paneli - {self.tracking_no}"
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        dialog_width = 1780
        dialog_height = 1080
        if available is not None:
            dialog_width = max(1320, min(dialog_width, available.width() - 60))
            dialog_height = max(860, min(dialog_height, available.height() - 40))
        super().__init__(title, parent, width=dialog_width, height=dialog_height)
        
        self.audit_logger = get_audit_logger(db)
        
        # Load EVERYTHING from database using sqlite3.Row
        self.device_dict = self.db.cursor.execute("SELECT * FROM devices WHERE tracking_no=?", (self.tracking_no,)).fetchone()
        if not self.device_dict:
            self.device_dict = {}
        else:
            # Convert sqlite3.Row to dict to use .get()
            self.device_dict = dict(self.device_dict)

        # Preset some common variables for easier access
        self.pattern_str = self.device_dict.get('pattern_lock', '')
        self.accessories_str = self.device_dict.get('accessories', '')
        self.photo_path_str = self.device_dict.get('photo_path', '')
        self.cargo_fee = self.device_dict.get('cargo_fee', 0.0)
        self.delivery_type = self.device_dict.get('delivery_type', 'Elden')
        self.payment_status = self.device_dict.get('payment_status', 'Ödenmedi')
        self.warranty_date = self.device_dict.get('warranty_end_date', '')
        self.repair_details = self.device_dict.get('repair_details', '')
        self.internal_notes = self.device_dict.get('internal_notes', '')
        self.fault_desc = self.device_dict.get('fault_description', '')
        self.checklist_status = self.device_dict.get('checklist_status')
        if not self.checklist_status:
            cached_status = self._load_cached_checklist_status()
            if cached_status:
                self.checklist_status = cached_status
                self.device_dict['checklist_status'] = cached_status
        
        self.ai_service = AIService(db)
        self.voice_thread = None
        self.setup_content()
        
        # Buyuk formlarda icerik tasmasin; dikey kaydirma acik kalsin.
        try:
            if hasattr(self, "scroll_area"):
                self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        except Exception:
            pass
        
    
    def closeEvent(self, event):
        """Auto-save on close to ensure switch states are persisted"""
        try:
            # We call save_update but in 'silent' mode ideally, or just call it.
            # But save_update shows success toast and closes dialog (self.accept).
            # We need a headless save or just accept the fact it saves.
            # Let's verify if we should auto-save.
            # Ideally we refactored save logic into a helper, but here we can just call it 
            # if the user hasn't explicitly cancelled (though close IS cancel usually).
            # The user Requested 'Auto-Save' mechanism.
            
            # Since closeEvent happens on 'X' click or reject()
            # We should probably only auto-save if it wasn't an explicit 'Cancel' button click
            # But the user asked for "her pencere kapandığında".
            
            # Let's perform a silent save.
            self._perform_silent_save()
        except Exception as e:
            logger.debug(f"Technician panel close auto-save skipped: {e}")
        super().closeEvent(event)

    def _toggle_cache_key(self):
        return f"technician_panel.checklist_status.{self.tracking_no}"

    def _load_cached_checklist_status(self):
        key = self._toggle_cache_key()
        if key in TechnicianPanel._session_toggle_cache:
            return TechnicianPanel._session_toggle_cache.get(key, "")
        settings = QSettings("AYEC", "AYECPro")
        value = settings.value(key, "")
        if value is None:
            return ""
        return str(value)

    def _save_cached_checklist_status(self, value):
        key = self._toggle_cache_key()
        TechnicianPanel._session_toggle_cache[key] = value or ""
        settings = QSettings("AYEC", "AYECPro")
        settings.setValue(key, value or "")

    def get_cached_checklist_status(self):
        return self._load_cached_checklist_status()

    def _normalize_checklist_items(self, items):
        seen = set()
        normalized = []
        for item in items:
            text = str(item).strip()
            if not text:
                continue
            key = text.upper()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
        return normalized

    def _persist_toggle_state(self, checklist_status, accessories=None):
        value = checklist_status or ""
        self.checklist_status = value
        self.device_dict['checklist_status'] = value
        self._save_cached_checklist_status(value)
        try:
            if accessories is None:
                self.db.cursor.execute("UPDATE devices SET checklist_status=? WHERE tracking_no=?", (value, self.tracking_no))
            else:
                self.db.cursor.execute("UPDATE devices SET checklist_status=?, accessories=? WHERE tracking_no=?", (value, accessories, self.tracking_no))
            self.db.conn.commit()
        except Exception:
            pass

    def _perform_silent_save(self):
        try:
            if not (
                hasattr(self, "wizard_page1")
                and hasattr(self, "wizard_page2")
                and hasattr(self, "wizard_page3")
            ):
                return

            data_page1 = self.wizard_page1.get_data()
            data_page2 = self.wizard_page2.get_data()
            data_page3 = self.wizard_page3.get_data()

            checklist_items = []
            base_list = data_page2.get("checklist_status", "")
            if base_list:
                checklist_items.extend([s.strip() for s in base_list.split(",") if s.strip()])
            if hasattr(self, "test_toggles"):
                for name, toggle in self.test_toggles:
                    if toggle.isChecked():
                        checklist_items.append(name)
            if hasattr(self, "dynamic_toggles"):
                for txt, tgl in self.dynamic_toggles:
                    if tgl.isChecked():
                        checklist_items.append(txt)

            existing_status = self.checklist_status or self.device_dict.get("checklist_status", "")
            checklist_str = (
                ",".join(self._normalize_checklist_items(checklist_items))
                if checklist_items
                else (existing_status or "")
            )
            merged_data = {**data_page1, **data_page2, **data_page3}
            merged_data["checklist_status"] = checklist_str
            self._save_cached_checklist_status(checklist_str)

            exit_date = self.device_dict.get("exit_date")
            delivered_at = self.device_dict.get("delivered_at")
            if merged_data.get("status") == "Teslim Edildi" and not exit_date:
                now = datetime.now()
                exit_date = now.strftime("%Y-%m-%d")
                delivered_at = now.strftime("%Y-%m-%d %H:%M:%S")
            elif merged_data.get("status") != "Teslim Edildi":
                exit_date = None
                delivered_at = None

            self.db.cursor.execute(
                """
                UPDATE devices
                SET status=?, labor_cost=?, fault_description=?, repair_details=?,
                    internal_notes=?, warranty_end_date=?, warranty_status=?, accessories=?,
                    cargo_fee=?, delivery_type=?, payment_status=?, checklist_status=?, exit_date=?, delivered_at=?
                WHERE tracking_no=?
                """,
                (
                    merged_data.get("status"),
                    merged_data.get("labor_cost"),
                    merged_data.get("fault_description"),
                    merged_data.get("repair_details"),
                    merged_data.get("internal_notes"),
                    merged_data.get("warranty_end_date"),
                    merged_data.get("warranty_status"),
                    merged_data.get("accessories"),
                    merged_data.get("cargo_fee"),
                    merged_data.get("delivery_type"),
                    merged_data.get("payment_status"),
                    merged_data.get("checklist_status"),
                    exit_date,
                    delivered_at,
                    self.tracking_no,
                ),
            )
            self.db.conn.commit()
            self.device_dict.update(merged_data)
            self.device_dict["exit_date"] = exit_date
            self.device_dict["delivered_at"] = delivered_at
        except Exception as e:
            logger.error(f"Technician panel auto-save failed: {e}")

    def _handle_toggle_changed(self, state):
        self._perform_silent_save()

    def setup_content(self):
        # --- Common Styles ---
        self.setStyleSheet(theme_qss(f"""
            QLabel {{ 
                font-family: {DesignTokens.FONT_FAMILY}; 
                color: {DesignTokens.FOREGROUND}; 
            }}
            
            QScrollBar:vertical {{
                border: none;
                background: {DesignTokens.SECONDARY};
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {DesignTokens.BORDER};
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {DesignTokens.ACCENT}; }}
            
            QLineEdit, QTextEdit, QPlainTextEdit {{
                color: @text;
            }}
        """))
        
        # Content body - remove extra wrapper for single child (tabs)
        self.general_layout = None  # Not needed
        # Zero out outer margin so tabs fill the whole content area
        try:
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_layout.setSpacing(0)
        except Exception:
            pass

        # --- TABS (directly below ModernDialog header) ---
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(theme_qss(f"""
            QTabWidget::pane {{ 
                border: 1px solid {DesignTokens.BORDER};
                border-radius: {DesignTokens.RADIUS_LG};
                background: white;
                top: -1px;
            }}
            QTabBar::tab {{
                background: @surface_alt;
                color: @text_muted;
                padding: 8px 18px;
                margin-right: 6px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-weight: 700;
                font-size: 12px;
                border: 1px solid @border;
                border-bottom: none;
                min-width: 120px;
            }}
            QTabBar::tab:selected {{
                background: white;
                color: @accent;
                border-bottom: 3px solid @accent;
                padding-bottom: 12px;
            }}
            QTabBar::tab:hover:!selected {{
                background: @surface_alt;
            }}
        """))
        
        self.create_general_tab()
        self.create_test_tab()
        self.create_logs_tab()
        
        self.tabs.addTab(self.general_widget, "Genel İşlemler")
        self.tabs.addTab(self.test_widget, "Cihaz Test Formu")
        self.tabs.addTab(self.log_widget, "İşlem Geçmişi")
        
        self.add_widget(self.tabs)
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content_layout.setStretchFactor(self.tabs, 1)
        self.tabs.currentChanged.connect(self._update_wizard_footer_visibility)
        self._update_wizard_footer_visibility(self.tabs.currentIndex())
        self.clear_footer()
        self.set_footer_visible(False, 0)
        
    def print_label(self):
        """Servis fişi / etiketi yazdırır"""
        try:
            # Önce verileri bir metin belgesine hazırla
            doc = QTextDocument()
            from src.utils.date_utils import format_datetime_turkish
            html = f"""
            <div style="font-family: 'Segoe UI', sans-serif; padding: 20px; background-color: white; color: black;">
                <h2 style="color: @accent; border-bottom: 2px solid @accent; padding-bottom: 10px;">SERVIS KAYIT FISI</h2>
                <table style="width: 100%; margin-top: 20px; color: black;">
                    <tr><td style="padding: 5px;"><b>Takip No:</b></td><td>{self.tracking_no}</td></tr>
                    <tr><td style="padding: 5px;"><b>Müşteri:</b></td><td>{self.device_dict.get('customer_name', '-')}</td></tr>
                    <tr><td style="padding: 5px;"><b>Cihaz:</b></td><td>{self.device_dict.get('device_brand', '')} {self.device_dict.get('device_model', '')}</td></tr>
                    <tr><td style="padding: 5px;"><b>Seri No:</b></td><td>{self.device_dict.get('serial_no', '-')}</td></tr>
                    <tr><td style="padding: 5px;"><b>Arıza:</b></td><td>{self.device_dict.get('fault_description', '-')}</td></tr>
                    <tr><td style="padding: 5px;"><b>Tarih:</b></td><td>{format_datetime_turkish(datetime.now())}</td></tr>
                </table>
                <div style="margin-top: 40px; text-align: center; border-top: 1px dashed lightgray; padding-top: 20px; color: black;">
                    <p>Güveniniz için teşekkür ederiz.</p>
                </div>
            </div>
            """
            doc.setHtml(html)
            
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            
            if dialog.exec():
                doc.print(printer)
                show_success(self, "Yazdırma işlemi başlatıldı.")
        except Exception as e:
            show_error(self, f"Yazdırma hatası: {e}")

    def add_footer_actions(self):
        # Footer Actions
        self.add_cancel_button("İptal / Kapat")
        self.add_button("Servis Fişi Yazdır", "secondary", self.print_label)
        self.add_button("Cihaz Geçmişi", "secondary", self.open_history)
        self.add_button("Güncellemeleri Kaydet", "primary", self.save_update)


        
    def create_general_tab(self):
        self.general_widget = QWidget()
        main_layout = QVBoxLayout(self.general_widget)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(6)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        top_action_row = QHBoxLayout()
        top_action_row.setContentsMargins(0, 0, 0, 2)
        top_action_row.addStretch(1)
        self.btn_save_general = QPushButton("Kaydet")
        self.btn_save_general.setFixedSize(132, 34)
        self.btn_save_general.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        self.btn_save_general.clicked.connect(self.save_update)
        top_action_row.addWidget(self.btn_save_general)
        main_layout.addLayout(top_action_row)
        from src.ui.dialogs.technician_wizard_page1 import TechnicianWizardPage1
        from src.ui.dialogs.technician_wizard_page2 import TechnicianWizardPage2
        from src.ui.dialogs.technician_wizard_page3 import TechnicianWizardPage3
        self.wizard_page1 = TechnicianWizardPage1(self.db, self.tracking_no, self.device_dict, self)
        self.wizard_page2 = TechnicianWizardPage2(self.db, self.tracking_no, self.device_dict, self)
        self.wizard_page3 = TechnicianWizardPage3(self.db, self.tracking_no, self.device_dict, self)
        self.wizard_page1.hide()
        self.wizard_page2.hide()
        self.wizard_page3.hide()
        self.wizard_page1.accessories_group.setTitle("Cihaz Yan\u0131nda Gelen Aksesuarlar")
        self.wizard_page1.pattern_group.setTitle("G\u00fcvenlik Deseni")
        self.wizard_page1.photo_group.setTitle("Cihaz G\u00f6rselleri")
        for gallery_button in self.wizard_page1.photo_group.findChildren(QPushButton):
            gallery_button.setText("Galeriyi A\u00e7")

        private_layout = self.wizard_page2.private_group.layout()
        process_quick_label_item = private_layout.takeAt(4)
        process_quick_frame_item = private_layout.takeAt(4)
        self.process_quick_group = QGroupBox("İşlem Detayı Hızlı Seçim")
        self.process_quick_group.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        self.process_quick_group.setStyleSheet(theme_qss("""
            QGroupBox {
                background: transparent;
                border: none;
                border-top: 1px solid @accent;
                border-radius: 0;
                padding: 4px 0 0 0;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 0px;
                padding: 0 8px 4px 0;
                color: @accent;
            }
        """))
        process_quick_layout = QVBoxLayout(self.process_quick_group)
        process_quick_layout.setContentsMargins(0, 6, 0, 0)
        process_quick_layout.setSpacing(6)
        if process_quick_label_item and process_quick_label_item.widget():
            process_quick_layout.addWidget(process_quick_label_item.widget())
        if process_quick_frame_item and process_quick_frame_item.widget():
            process_quick_layout.addWidget(process_quick_frame_item.widget())

        self.wizard_page1.accessories_group.setMaximumHeight(104)
        self.wizard_page2.fault_group.setMaximumHeight(96)
        self.wizard_page2.process_group.setMaximumHeight(96)
        self.wizard_page1.pattern_group.setMaximumHeight(230)
        self.wizard_page1.photo_group.setMaximumHeight(132)

        left_top_card = self._make_general_card("Cihaz Kimliği & Görseller")
        left_top_layout = left_top_card.layout()
        left_visual_row = QHBoxLayout()
        left_visual_row.setContentsMargins(0, 0, 0, 0)
        left_visual_row.setSpacing(8)
        left_visual_row.addWidget(self.wizard_page1.pattern_group, 50)
        left_visual_row.addWidget(self.wizard_page1.photo_group, 50)
        left_top_layout.addLayout(left_visual_row)

        right_stack = QWidget()
        quick_actions_layout = QVBoxLayout(right_stack)
        quick_actions_layout.setContentsMargins(0, 0, 0, 0)
        quick_actions_layout.setSpacing(8)
        self.btn_toggle_editor = QPushButton("Taslak Düzenle")
        self.btn_toggle_editor.setFixedWidth(148)
        self.btn_toggle_editor.setFixedHeight(30)
        self.btn_toggle_editor.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        self.btn_toggle_editor.clicked.connect(self.wizard_page2.open_quick_notes_editor)
        quick_actions_layout.addWidget(self.wizard_page1.accessories_group)
        quick_actions_layout.addWidget(self.wizard_page2.fault_quick_group)
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_toggle_editor)
        button_row.setAlignment(self.btn_toggle_editor, Qt.AlignmentFlag.AlignRight)
        quick_actions_layout.addLayout(button_row)
        quick_actions_layout.addWidget(self.process_quick_group)

        content_row = QHBoxLayout()
        content_row.setSpacing(8)
        content_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(6)
        left_column.addWidget(left_top_card)
        left_column.addWidget(self.wizard_page2.fault_group)
        left_column.addWidget(self.wizard_page2.process_group)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(6)
        right_column.addWidget(right_stack)

        left_container = QWidget()
        left_container.setLayout(left_column)
        right_container = QWidget()
        right_container.setLayout(right_column)

        content_row.addWidget(left_container, 58)
        content_row.addWidget(right_container, 42)
        main_layout.addLayout(content_row)

        main_layout.addWidget(self.wizard_page2.private_group)

        bottom_card = self._make_general_card("Parça Kullanımı ve Durum Güncelleme")
        bottom_layout = bottom_card.layout()
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        bottom_row.setAlignment(Qt.AlignmentFlag.AlignTop)
        bottom_row.addWidget(self.wizard_page3.status_group, 26)
        bottom_row.addWidget(self.wizard_page3.finance_group, 24)
        bottom_row.addWidget(self.wizard_page3.parts_group, 50)
        bottom_layout.addLayout(bottom_row)
        main_layout.addWidget(bottom_card)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 4, 0, 0)
        action_row.addStretch(1)
        bottom_save = QPushButton("Kaydet")
        bottom_save.setFixedSize(132, 34)
        bottom_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        bottom_save.clicked.connect(self.save_update)
        action_row.addWidget(bottom_save)
        main_layout.addLayout(action_row)

    def _make_general_card(self, title):
        card = QFrame()
        card.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface;
                border: 1px solid @border;
                border-radius: 12px;
            }
        """))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        title_label.setStyleSheet(theme_qss("color: @warning; background: transparent; border: none; letter-spacing: 0.2px;"))
        layout.addWidget(title_label)
        return card

    def _setup_wizard_footer(self):
        return

    def _update_wizard_footer_visibility(self, index):
        if hasattr(self, "footer"):
            self.clear_footer()
            self.set_footer_visible(False, 0)

    def wizard_go_back(self):
        return

    def wizard_go_next(self):
        self.save_update()

    def update_wizard_navigation(self):
        return

    def create_test_tab(self):
        """Create test results tab with functional checklist"""
        self.test_widget = QWidget()
        layout = QVBoxLayout(self.test_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        header_row = QHBoxLayout()
        header = QLabel("Cihaz Fonksiyon Testleri")
        header.setFont(QFont(DesignTokens.FONT_FAMILY, 16, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text;"))
        
        btn_edit = QPushButton("Toggle-Switch Düzenle")
        btn_edit.setFixedHeight(40)
        btn_edit.setFont(QFont(DesignTokens.FONT_FAMILY, 12, QFont.Weight.Bold))
        btn_edit.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: {DesignTokens.ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: @accent_hover;
            }}
            QPushButton:pressed {{
                background-color: @accent_pressed;
            }}
        """))
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.clicked.connect(self.open_test_toggle_editor)
        
        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addWidget(btn_edit)
        layout.addLayout(header_row)
        
        # Test Grid
        self.test_grid = QGridLayout()
        self.test_grid.setSpacing(15)
        layout.addLayout(self.test_grid)
        self.reload_test_toggles()
        layout.addStretch()
        
        # Info note
        note = QLabel("Not: İşaretlenen testler 'İşlem Geçmişi'ne ve cihaz kartına 'Test OK' olarak işlenecektir.")
        note.setStyleSheet(theme_qss("color: @text_muted; font-style: italic; margin-top: 10px;"))
        layout.addWidget(note)

    def open_test_toggle_editor(self):
        from src.ui.dialogs.quick_notes_editor import QuickNotesEditor
        editor = QuickNotesEditor(self.db, self, initial_category="Cihaz Testi")
        try:
            editor.exec()
        finally:
            try:
                self.reload_test_toggles()
            except Exception:
                pass

    def _get_test_items(self):
        tests = []
        try:
            rows = self.db.get_fast_notes("Cihaz Testi")
            for r in rows:
                label = ""
                active_val = 1
                if isinstance(r, dict):
                    label = r.get("label", "")
                    active_val = r.get("is_active", 1)
                else:
                    try:
                        if hasattr(r, "keys") and "label" in r.keys():
                            label = r["label"]
                            active_val = r["is_active"]
                        else:
                            label = r[2] if len(r) > 2 else ""
                            active_val = r[3] if len(r) > 3 else 1
                    except Exception:
                        label = ""
                        active_val = 1
                label = str(label or "").strip()
                if not label:
                    continue
                try:
                    is_active = int(active_val) == 1
                except Exception:
                    is_active = bool(active_val)
                tests.append((label, is_active))
        except Exception:
            tests = []
        if not tests:
            tests = [(t, True) for t in [
                "Dokunmatik Ekran", "LCD Görüntü", "Ön Kamera", "Arka Kamera",
                "Ahize (İç Ses)", "Hoparlör (Dış Ses)", "Mikrofon", "Şarj Soketi",
                "WIFI Bağlantısı", "Bluetooth", "FaceID / Parmak İzi", "Yakınlık Sensörü",
                "Sim Kart / Şebeke", "Titreşim", "Fiziksel Tuşlar", "Kasa Durumu"
            ]]
        return tests

    def reload_test_toggles(self):
        if not hasattr(self, "test_grid"):
            return
        self._clear_layout(self.test_grid)
        self.test_toggles = []
        tests = self._get_test_items()
        existing_checks = (self.checklist_status or "").upper().split(',')
        
        row, col = 0, 0
        for test_name, is_active in tests:
            container = QFrame()
            container.setStyleSheet(theme_qss("""
                QFrame {
                    background-color: @surface_alt;
                    border: 1px solid @border;
                    border-radius: 8px;
                }
            """))
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(10, 10, 10, 10)
            
            lbl = QLabel(test_name)
            lbl.setFont(QFont(DesignTokens.FONT_FAMILY, 11, QFont.Weight.DemiBold))
            lbl.setStyleSheet(theme_qss("border: none; color: @text;"))
            
            toggle = AnimatedToggle()
            toggle.setFixedSize(50, 26)
            toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            
            if test_name.upper() in existing_checks:
                toggle.setChecked(True)
            toggle.toggled.connect(self._handle_toggle_changed)
            if not is_active:
                toggle.setEnabled(False)
                lbl.setStyleSheet(theme_qss("border: none; color: @disabled_text;"))
            
            h_layout.addWidget(lbl)
            h_layout.addStretch()
            h_layout.addWidget(toggle)
            
            self.test_grid.addWidget(container, row, col)
            self.test_toggles.append((test_name, toggle))
            
            col += 1
            if col >= 3:
                col = 0
                row += 1
        try:
            self.test_grid.invalidate()
        except Exception:
            pass
        if hasattr(self, "test_widget"):
            try:
                layout = self.test_widget.layout()
                if layout:
                    layout.invalidate()
            except Exception:
                pass
            self.test_widget.update()
            self.test_widget.adjustSize()

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
    
    def create_logs_tab(self):
        self.log_widget = QWidget()
        layout = QVBoxLayout(self.log_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        header = QLabel("İşlem Geçmişi")
        header.setFont(QFont(DesignTokens.FONT_FAMILY, 16, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(header)
        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(3)
        self.table_logs.setHorizontalHeaderLabels(["Tarih", "Tür", "Mesaj"])
        self.table_logs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_logs.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table_logs.setAlternatingRowColors(True)
        self.table_logs.setShowGrid(False)
        self.table_logs.setStyleSheet(theme_qss(f"""
            QTableWidget {{
                border: 1px solid {DesignTokens.BORDER};
                border-radius: {DesignTokens.RADIUS_LG};
                background: white;
                alternate-background-color: @surface_alt;
            }}
            QTableWidget::item {{
                padding: 12px;
                color: {DesignTokens.FOREGROUND};
                border-bottom: 1px solid @border;
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
        self.refresh_logs()


    def save_update(self):
        """Save wizard data to database"""
        try:
            # Collect data from all wizard pages (if they exist)
            if hasattr(self, 'wizard_page1') and hasattr(self, 'wizard_page2') and hasattr(self, 'wizard_page3'):
                data_page1 = self.wizard_page1.get_data()
                data_page2 = self.wizard_page2.get_data()
                data_page3 = self.wizard_page3.get_data()
                
                # Collect Test Data
                test_items = []
                if hasattr(self, 'test_toggles'):
                    for name, toggle in self.test_toggles:
                        if toggle.isChecked():
                            test_items.append(name)
                            
                # Merge all data
                merged_data = {**data_page1, **data_page2, **data_page3}
                
                # Append test items to checklist_status
                base_checklist = merged_data.get('checklist_status', '')
                if base_checklist:
                    final_checklist = base_checklist + "," + ",".join(test_items)
                else:
                    final_checklist = ",".join(test_items)
                
                final_checklist = ",".join(self._normalize_checklist_items([x for x in final_checklist.split(',')]))
                
                merged_data['checklist_status'] = final_checklist
                self._save_cached_checklist_status(final_checklist)
                old_status = self.device_dict.get('status', '')
                
                exit_date = self.device_dict.get('exit_date')
                delivered_at = self.device_dict.get('delivered_at')
                if merged_data.get('status') == 'Teslim Edildi' and not exit_date:
                    now = datetime.now()
                    exit_date = now.strftime("%Y-%m-%d")
                    delivered_at = now.strftime("%Y-%m-%d %H:%M:%S")
                elif merged_data.get('status') != 'Teslim Edildi':
                    exit_date = None
                    delivered_at = None

                # Update database
                self.db.cursor.execute("""
                    UPDATE devices 
                    SET status=?, labor_cost=?, fault_description=?, repair_details=?,
                        internal_notes=?, warranty_end_date=?, warranty_status=?, accessories=?,
                        cargo_fee=?, delivery_type=?, payment_status=?, checklist_status=?, exit_date=?, delivered_at=?
                    WHERE tracking_no=?
                """, (
                    merged_data.get('status'),
                    merged_data.get('labor_cost'),
                    merged_data.get('fault_description'),
                    merged_data.get('repair_details'),
                    merged_data.get('internal_notes'),
                    merged_data.get('warranty_end_date'),
                    merged_data.get('warranty_status'),
                    merged_data.get('accessories'),
                    merged_data.get('cargo_fee'),
                    merged_data.get('delivery_type'),
                    merged_data.get('payment_status'),
                    merged_data.get('checklist_status'),
                    exit_date,
                    delivered_at,
                    self.tracking_no
                ))
                self.db.conn.commit()
                
                # Log action
                self.audit_logger.log_action(
                    'devices', 'UPDATE', 
                    f"Teknisyen güncellemesi: {self.tracking_no} - Durum: {merged_data.get('status')}, " +
                    f"Tutar: {merged_data.get('labor_cost', 0) + merged_data.get('cargo_fee', 0)}"
                )

                # --- VOICE CONFIRMATION FOR ARCHIVING (Teslim Edildi) ---
                new_status = merged_data.get('status', '')
                
                if new_status == 'Teslim Edildi' and old_status != 'Teslim Edildi':
                    try:
                        # Calculate total amount
                        labor = float(merged_data.get('labor_cost', 0) or 0)
                        cargo = float(merged_data.get('cargo_fee', 0) or 0)

                        # Get parts cost (sell price)
                        parts_cost = 0.0
                        try:
                            query = "SELECT price, quantity FROM used_parts WHERE tracking_no=?"
                            try:
                                self.db.cursor.execute("PRAGMA table_info(used_parts)")
                                cols = [row[1] for row in self.db.cursor.fetchall()]
                                deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                                has_qty = "quantity" in cols
                                if deleted_col:
                                    query = query.replace("WHERE tracking_no=?", f"WHERE tracking_no=? AND ({deleted_col}=0 OR {deleted_col} IS NULL)")
                            except Exception:
                                has_qty = False
                            parts_rows = self.db.cursor.execute(query, (self.tracking_no,)).fetchall()
                            for pr in parts_rows:
                                price = float(pr[0] or 0)
                                qty = int(pr[1] or 1) if has_qty and len(pr) > 1 else 1
                                parts_cost += price * qty
                        except Exception:
                            parts_cost = 0.0

                        total_amount = labor + cargo + parts_cost
                        customer_name = self.device_dict.get('customer_name', '')

                        # Gelir kaydı: Tutar > 0 ise ödeme/kasa diyaloğu göster
                        if total_amount > 0:
                            from src.utils.asistan_motoru import sesli_cevap_ver_async
                            sesli_cevap_ver_async(
                                f"Cihaz teslim ediliyor. Toplam {total_amount:.0f} lira. Ödemeyi kasaya işleyelim mi?"
                            )

                            confirm_voice = False
                            def on_voice_response(text):
                                nonlocal confirm_voice
                                t = text.lower()
                                if "evet" in t or "onay" in t or "işle" in t:
                                    confirm_voice = True
                                    if hasattr(self, '_confirm_dlg') and self._confirm_dlg:
                                        self._confirm_dlg.accept()

                            listener = VoiceWorker(self.ai_service)
                            listener.text_received.connect(on_voice_response)
                            listener.start()

                            from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton

                            class PaymentConfirmDialog(ModernDialog):
                                def __init__(self, parent=None):
                                    super().__init__(title="Odeme Onayi ve Kasa Secimi", parent=parent, width=450, height=280)
                                    self.set_footer_visible(False)
                                    self.setStyleSheet(theme_qss("background-color: @surface; border-radius: 8px;"))
                                    self.selected_bank_id = None
                                    self.payment_method = "Nakit"

                                    l = self.content_layout
                                    l.setSpacing(12)
                                    l.setContentsMargins(20, 20, 20, 20)

                                    # Tutar özeti
                                    summary = f"Cihaz: {parent.tracking_no if parent else ''}\n"
                                    summary += f"Müşteri: {customer_name}\n\n"
                                    if labor > 0:
                                        summary += f"İşçilik: {self._fmt_try(labor)}\n"
                                    if parts_cost > 0:
                                        summary += f"Parça/Malzeme: {self._fmt_try(parts_cost)}\n"
                                    if cargo > 0:
                                        summary += f"Kargo: {self._fmt_try(cargo)}\n"
                                    summary += f"\nTOPLAM: {self._fmt_try(total_amount)}"

                                    lbl_info = QLabel(summary)
                                    lbl_info.setStyleSheet(theme_qss("color: @text; font-size: 12px;"))
                                    l.addWidget(lbl_info)

                                    l.addWidget(QLabel("Ödeme Yöntemi:"))
                                    self.cmb_method = QComboBox()
                                    self.cmb_method.addItems(["Nakit", "Kredi Kartı", "Havale/EFT"])
                                    self.cmb_method.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px; color: @text; background: @surface;"))
                                    l.addWidget(self.cmb_method)

                                    l.addWidget(QLabel("Kasa/Banka Seçimi:"))
                                    self.cmb_bank = QComboBox()
                                    self.cmb_bank.addItem("Ana Kasa (Varsayılan)", -1)
                                    self.cmb_bank.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px; color: @text; background: @surface;"))
                                    try:
                                        db_obj = parent.db if parent else None
                                        if db_obj and hasattr(db_obj, 'get_bank_accounts'):
                                            for b in db_obj.get_bank_accounts():
                                                b_name = b.get('bank_name') if isinstance(b, dict) else b[1]
                                                b_id = b.get('id') if isinstance(b, dict) else b[0]
                                                self.cmb_bank.addItem(b_name, b_id)
                                    except Exception:
                                        pass
                                    l.addWidget(self.cmb_bank)

                                    btn_lay = QHBoxLayout()
                                    btn_lay.setSpacing(10)
                                    btn_no = QPushButton("Ödeme Almadan Teslim Et")
                                    btn_no.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
                                    btn_no.setFixedHeight(42)
                                    btn_no.clicked.connect(self.reject)

                                    btn_yes = QPushButton("Ödeme Al ve Kasaya İşle")
                                    btn_yes.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
                                    btn_yes.setFixedHeight(42)
                                    btn_yes.clicked.connect(self.accept_data)

                                    btn_lay.addWidget(btn_no)
                                    btn_lay.addWidget(btn_yes)
                                    l.addLayout(btn_lay)

                                def accept_data(self):
                                    val = self.cmb_bank.currentData()
                                    self.selected_bank_id = val if val != -1 else None
                                    self.payment_method = self.cmb_method.currentText()
                                    self.accept()

                            self._confirm_dlg = PaymentConfirmDialog(self)
                            result = self._confirm_dlg.exec()
                            listener.stop()

                            # Detaylı açıklama
                            desc_parts = [f"Servis Geliri: {self.tracking_no}"]
                            if customer_name:
                                desc_parts.append(f"({customer_name})")
                            detail_parts = []
                            if labor > 0:
                                detail_parts.append(f"İşçilik: {self._fmt_try(labor)}")
                            if parts_cost > 0:
                                detail_parts.append(f"Parça: {self._fmt_try(parts_cost)}")
                            if cargo > 0:
                                detail_parts.append(f"Kargo: {self._fmt_try(cargo)}")
                            if detail_parts:
                                desc_parts.append(f"[{' + '.join(detail_parts)}]")
                            desc = " ".join(desc_parts)

                            if result or confirm_voice:
                                pm = getattr(self._confirm_dlg, 'payment_method', 'Nakit')
                                b_id = getattr(self._confirm_dlg, 'selected_bank_id', None)
                                merged_data['payment_status'] = pm

                                try:
                                    self.db.add_transaction_extended(
                                        type="Gelir",
                                        category="Servis Hizmeti",
                                        amount=total_amount,
                                        description=desc,
                                        date=datetime.now().strftime("%Y-%m-%d"),
                                        payment_method=pm,
                                        bank_account_id=b_id,
                                        tracking_no=self.tracking_no,
                                        ref_no=self.tracking_no,
                                        selected_services=[self.tracking_no],
                                    )
                                except Exception:
                                    self.db.add_transaction(
                                        t_type="Gelir",
                                        category="Servis Hizmeti",
                                        amount=total_amount,
                                        description=desc,
                                        payment_method=pm,
                                        tracking_no=self.tracking_no,
                                        ref_no=self.tracking_no,
                                        selected_services=[self.tracking_no],
                                    )
                                show_success(self, f"Ödeme kasaya işlendi: {self._fmt_try(total_amount)}")
                                sesli_cevap_ver_async("Ödeme girişi yapıldı.")
                            else:
                                merged_data['payment_status'] = "Ödenmedi"
                                # Kullanıcı ödeme almadan teslim ediyor; geliri yine de kaydet (ödeme bekliyor)
                                try:
                                    self.db.add_transaction_extended(
                                        type="Gelir",
                                        category="Servis Hizmeti",
                                        amount=total_amount,
                                        description=desc + " [Ödeme Bekliyor]",
                                        date=datetime.now().strftime("%Y-%m-%d"),
                                        payment_method="Ödenmedi",
                                        tracking_no=self.tracking_no,
                                        ref_no=self.tracking_no,
                                        selected_services=[self.tracking_no],
                                    )
                                except Exception:
                                    self.db.add_transaction(
                                        t_type="Gelir",
                                        category="Servis Hizmeti",
                                        amount=total_amount,
                                        description=desc + " [Ödeme Bekliyor]",
                                        payment_method="Ödenmedi",
                                        tracking_no=self.tracking_no,
                                        ref_no=self.tracking_no,
                                        selected_services=[self.tracking_no],
                                    )
                                show_info(self, f"Gelir kaydı oluşturuldu (Ödeme Bekliyor): {self._fmt_try(total_amount)}")
                                sesli_cevap_ver_async("Gelir kaydı oluşturuldu. Ödeme henüz alınmadı.")

                            # --- GİDER KAYDI: Malzeme Maliyeti ---
                            try:
                                # used_parts tablosundaki is_deleted kolonunu kontrol et
                                try:
                                    self.db.cursor.execute("PRAGMA table_info(used_parts)")
                                    up_cols = [r[1] for r in self.db.cursor.fetchall()]
                                    del_col = "is_deleted" if "is_deleted" in up_cols else ("is_archived" if "is_archived" in up_cols else None)
                                    has_pps = "purchase_price_snapshot" in up_cols
                                except Exception:
                                    del_col = None
                                    has_pps = False

                                if has_pps:
                                    cost_query = "SELECT part_name, purchase_price_snapshot, quantity FROM used_parts WHERE tracking_no=?"
                                    if del_col:
                                        cost_query += f" AND ({del_col}=0 OR {del_col} IS NULL)"
                                    cost_rows = self.db.cursor.execute(cost_query, (self.tracking_no,)).fetchall()
                                    total_material_cost = sum(float(r[1] or 0) * int(r[2] or 1) for r in cost_rows)

                                    if total_material_cost > 0:
                                        part_names = [f"{r[0]}x{r[2]}" for r in cost_rows if r[0]]
                                        cost_desc = f"Servis Malzeme Maliyeti: {self.tracking_no}"
                                        if customer_name:
                                            cost_desc += f" ({customer_name})"
                                        cost_desc += f" [{', '.join(part_names)}]"

                                        try:
                                            self.db.add_transaction_extended(
                                                type="Gider",
                                                category="Malzeme Maliyeti",
                                                amount=total_material_cost,
                                                description=cost_desc,
                                                date=datetime.now().strftime("%Y-%m-%d"),
                                                tracking_no=self.tracking_no,
                                                ref_no=self.tracking_no,
                                            )
                                        except Exception:
                                            self.db.add_transaction(
                                                t_type="Gider",
                                                category="Malzeme Maliyeti",
                                                amount=total_material_cost,
                                                description=cost_desc,
                                                tracking_no=self.tracking_no,
                                                ref_no=self.tracking_no,
                                            )
                            except Exception as e:
                                logger.error(f"Technician panel material cost recording error: {e}")
                        else:
                            # total_amount == 0; sadece sesli bilgi
                            from src.utils.asistan_motoru import sesli_cevap_ver_async
                            sesli_cevap_ver_async("Cihaz teslim edildi.")

                    except Exception as e:
                        logger.error(f"Technician panel archive confirmation error: {e}", exc_info=True)

                self.device_dict.update(merged_data)
                self.device_dict['exit_date'] = exit_date
                self.device_dict['delivered_at'] = delivered_at
                self.device_dict['payment_status'] = merged_data.get('payment_status')
                self.db.cursor.execute(
                    "UPDATE devices SET payment_status=?, exit_date=?, delivered_at=? WHERE tracking_no=?",
                    (merged_data.get('payment_status'), exit_date, delivered_at, self.tracking_no)
                )
                self.db.conn.commit()
                if hasattr(self.wizard_page3, 'combo_payment') and merged_data.get('payment_status'):
                    self.wizard_page3.combo_payment.setCurrentText(str(merged_data.get('payment_status')))
                
                show_success(self, "Kayıt başarıyla güncellendi!")
                self.accept()
            else:
                show_error(self, "Wizard sayfalari yuklenemedi!")
                
        except Exception as e:
            logger.error(f"Technician panel save_update error: {e}", exc_info=True)
            show_error(self, f"Güncelleme hatası: {e}")
