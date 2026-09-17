# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QComboBox,
    QGraphicsDropShadowEffect,
    QTabWidget,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QDateTime
from PyQt6.QtGui import QFont, QTextDocument, QColor, QDesktopServices
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
import urllib.parse
from datetime import datetime

from src.ui.widgets.kanban_board import KanbanBoard
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.toast_notification import (
    show_success,
    show_info,
    show_error,
    show_warning,
)
from src.utils.theme_colors import theme_qss
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.logger import logger
from src.utils.page_ids import PageIds
from src.utils.system_config import SystemConfig
from src.utils.status_utils import is_active_device_status, normalize_device_status
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens



class DeliveryPaymentDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, parent, context, db):
        super().__init__(
            title="Teslim ve Tahsilat Onayı",
            parent=parent,
            width=720,
            height=560,
        )
        self.set_footer_visible(False)
        self.context = context
        self.db = db
        self.result_data = None
        self._build_ui()
        self._wire_ui_signals()

    def _wire_ui_signals(self):
        self.radio_debt.toggled.connect(self._on_ui_widget_changed)
        self.method_combo.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _build_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        title = QLabel("Teslim ve Tahsilat Onayı")
        title.setStyleSheet(theme_qss("font-size: 20px; font-weight: 900; color: @text;"))
        layout.addWidget(title)

        subtitle = QLabel(
            "Cihaz teslim edilecek. Varsayılan işlem tahsilat alıp teslim etmektir; ödeme alınmayacaksa borç yaz seçeneğini kullanın."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        layout.addWidget(subtitle)

        summary = QFrame()
        summary.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 12px;
            }
            QLabel { color: @text; }
        """))
        grid = QGridLayout(summary)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        rows = [
            ("Servis No", self.context.get("tracking_no") or "-"),
            ("Müşteri", self.context.get("customer_name") or "-"),
            ("Cihaz", self.context.get("device_name") or "-"),
            ("İşçilik", self._fmt(self.context.get("labor"))),
            ("Parça", self._fmt(self.context.get("parts_total"))),
            ("Kargo", self._fmt(self.context.get("cargo"))),
            ("Genel Toplam", self._fmt(self.context.get("total"))),
            ("Ödenmiş", self._fmt(self.context.get("paid"))),
            ("Kalan", self._fmt(self.context.get("remaining"))),
        ]
        for idx, (label, value) in enumerate(rows):
            r = idx // 3
            c = (idx % 3) * 2
            lbl = QLabel(label)
            lbl.setStyleSheet(theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;"))
            val = QLabel(str(value))
            val.setStyleSheet(theme_qss("font-size: 13px; font-weight: 800; color: @text;"))
            grid.addWidget(lbl, r, c)
            grid.addWidget(val, r, c + 1)
        layout.addWidget(summary)

        self.mode_group = QButtonGroup(self)
        self.radio_collect = QRadioButton("Tahsilat Al ve Teslim Et")
        self.radio_debt = QRadioButton("Borç Yaz ve Teslim Et")
        self.radio_collect.setChecked(True)
        for radio in (self.radio_collect, self.radio_debt):
            radio.setStyleSheet(theme_qss("""
                QRadioButton {
                    color: @text;
                    font-size: 13px;
                    font-weight: 800;
                    padding: 8px;
                }
            """))
            layout.addWidget(radio)
        self.mode_group.addButton(self.radio_collect)
        self.mode_group.addButton(self.radio_debt)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.amount_input = QLineEdit()
        default_amount = self.context.get("remaining")
        if default_amount is None:
            default_amount = self.context.get("total") or 0
        self.amount_input.setText(f"{float(default_amount or 0):.2f}")
        self.amount_input.setFixedHeight(38)
        self.amount_input.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 14px;
                font-weight: 800;
            }
            QLineEdit:focus { border-color: @accent; }
        """))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Nakit", "Kredi Kartı", "Havale / EFT", "Çek / Senet"])
        self.method_combo.setFixedHeight(38)
        self.method_combo.setStyleSheet(theme_qss("""
            QComboBox {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QComboBox::drop-down { border: none; width: 26px; }
        """))
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("Teslim/tahsilat notu...")
        self.note_input.setFixedHeight(72)
        self.note_input.setStyleSheet(theme_qss("""
            QTextEdit {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 8px;
            }
        """))

        form.addWidget(QLabel("Tahsilat Tutarı"), 0, 0)
        form.addWidget(self.amount_input, 1, 0)
        form.addWidget(QLabel("Ödeme Yöntemi"), 0, 1)
        form.addWidget(self.method_combo, 1, 1)
        form.addWidget(QLabel("Not"), 2, 0, 1, 2)
        form.addWidget(self.note_input, 3, 0, 1, 2)
        layout.addLayout(form)

        self.radio_collect.toggled.connect(self._sync_mode_controls)
        self._sync_mode_controls()

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        btn_cancel = QPushButton("Vazgeç")
        btn_debt = QPushButton("Borç Yaz ve Teslim Et")
        btn_collect = QPushButton("Tahsilat Al ve Teslim Et")
        for btn in (btn_cancel, btn_debt, btn_collect):
            btn.setFixedHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; font-weight: 800; } QPushButton:hover { background: @border; }"))
        btn_debt.setStyleSheet(theme_qss("QPushButton { background: @warning; color: @selection_text; border: none; border-radius: 8px; font-weight: 900; } QPushButton:hover { background: @warning; }"))
        btn_collect.setStyleSheet(theme_qss("QPushButton { background: @success; color: @selection_text; border: none; border-radius: 8px; font-weight: 900; } QPushButton:hover { background: @accent; }"))
        btn_cancel.clicked.connect(self.reject)
        btn_debt.clicked.connect(self.accept_debt)
        btn_collect.clicked.connect(self.accept_collect)
        buttons.addWidget(btn_cancel, 1)
        buttons.addWidget(btn_debt, 1)
        buttons.addWidget(btn_collect, 2)
        layout.addLayout(buttons)

    def _sync_mode_controls(self):
        enabled = self.radio_collect.isChecked()
        self.amount_input.setEnabled(enabled)
        self.method_combo.setEnabled(enabled)

    def _fmt(self, value):
        return CurrencyHelper.format_amount(
            float(value or 0.0),
            currency_code=self.context.get("currency") or "TRY",
        )

    def _parse_amount(self):
        text = self.amount_input.text().strip()
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            return float(text or 0.0)
        except ValueError:
            return 0.0

    def accept_debt(self):
        self.radio_debt.setChecked(True)
        self.result_data = {
            "mode": "debt",
            "note": self.note_input.toPlainText().strip(),
        }
        self.accept()

    def accept_collect(self):
        self.radio_collect.setChecked(True)
        self.result_data = {
            "mode": "collect",
            "amount": self._parse_amount(),
            "method": self.method_combo.currentText(),
            "note": self.note_input.toPlainText().strip(),
        }
        self.accept()

    def get_data(self):
        return self.result_data or {"mode": "collect", "amount": self._parse_amount()}


class ServiceBoardPage(QWidget):
    """
    Operasyonel Servis Panosu (Kanban)
    'Servis Talepleri' bölümünün yeni modern yüzü.
    """

    def _emit_financial_data_changed(self):
        main_window = getattr(self, "main_window", None) or self.window()
        if main_window and hasattr(main_window, "financial_data_changed"):
            try:
                main_window.financial_data_changed.emit()
            except Exception:
                pass

    def _refresh_navigation_badges(self):
        main_window = getattr(self, "main_window", None) or self.window()
        sidebar = getattr(main_window, "app_sidebar", None)
        side_menu = getattr(sidebar, "side_menu", None)
        if side_menu and hasattr(side_menu, "refresh_badges"):
            side_menu.refresh_badges()

    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.sector_manager = getattr(main_window, "sector_manager", None)
        self._last_refresh_msec = 0
        self._refresh_pending = False
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.setup_ui()

    def setup_ui(self):
        # 1. Main Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ServiceBoardTabs")
        self.tabs.setStyleSheet(self._tabs_qss())
        self.tab_main = QWidget()
        self.setup_main_tab()
        self.tabs.addTab(self.tab_main, "Operasyon Panosu")

        # 2. How to Use? Tab
        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "Nasıl Kullanılır?")

        self.layout.addWidget(self.tabs)

    def _is_classic_appearance(self):
        return AppearanceModeManager.current(self.db) == AppearanceModeManager.CLASSIC

    def _tabs_qss(self):
        if self._is_classic_appearance():
            return AppearanceModeManager.classic_tab_qss()
        return theme_qss("""
            QTabWidget::pane {
                background: @window;
                border: none;
            }
            QTabBar::tab {
                background: @surface_alt;
                color: @text;
                padding: 10px 16px;
                border: 1px solid @border;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 4px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: @surface;
                color: @accent;
            }
        """)

    def _button_qss(self, primary=False):
        if self._is_classic_appearance():
            bg = "#E9F7E9" if primary else "#FFFFFF"
            border = "#7AA77A" if primary else "#AEB4BD"
            return f"""
                QPushButton {{ background: {bg}; color: #111827; border: 1px solid {border}; border-radius: 0px; padding: 0 12px; font-weight: 700; }}
                QPushButton:hover {{ background: #F3F4F6; border-color: #1F4E79; }}
            """
        if primary:
            return theme_qss("QPushButton { background-color: @accent; color: @selection_text; border-radius: 10px; font-weight: bold; padding: 0 15px; } QPushButton:hover { background-color: @accent_hover; }")
        return theme_qss("QPushButton { background-color: @surface_alt; color: @text; border: 1px solid @border; border-radius: 10px; padding: 0 15px; } QPushButton:hover { background-color: @surface; border-color: @accent; }")

    def _header_qss(self):
        if self._is_classic_appearance():
            return "#PageHeader { background-color: #FFFFFF; border: 1px solid #B8C0CC; border-radius: 0px; }"
        return theme_qss("""
            #PageHeader {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 16px;
            }
        """)
    def showEvent(self, event):
        super().showEvent(event)
        try:
            from PyQt6.QtCore import QDateTime

            now = QDateTime.currentMSecsSinceEpoch()
            if now - getattr(self, "_last_refresh_msec", 0) > 3000 and not self._refresh_pending:
                self._refresh_pending = True
                QTimer.singleShot(0, self._refresh_data_once_visible)
        except Exception as e:
            logger.debug("Service board show refresh skipped: %s", e)

    def _refresh_data_once_visible(self):
        self._refresh_pending = False
        if not self.isVisible():
            return
        self.refresh_data()

    def setup_main_tab(self):
        layout = QVBoxLayout(self.tab_main)
        classic = self._is_classic_appearance()
        layout.setContentsMargins(10 if classic else 18, 10 if classic else 18, 10 if classic else 18, 10 if classic else 18)
        layout.setSpacing(8 if classic else 14)
        self.tab_main.setStyleSheet("background: #F3F4F6;" if classic else theme_qss("background: @window;"))

        # 1. Header & Filters
        self.header_widget = QFrame()
        self.header_widget.setObjectName("PageHeader")
        self.header_widget.setStyleSheet(self._header_qss())
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 4)
        self.header_widget.setGraphicsEffect(shadow)
        if self._is_classic_appearance():
            shadow.setEnabled(False)

        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(10 if classic else 24, 8 if classic else 18, 10 if classic else 24, 8 if classic else 18)
        header_layout.setSpacing(8 if classic else 16)

        # Title Section
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title = QLabel(
            "Araç Servis Operasyon Panosu"
            if self._is_automotive()
            else "Servis Operasyon Panosu"
        )
        title.setFont(QFont("Segoe UI", 25, QFont.Weight.Light))  # Fixed QFont.Light
        title.setStyleSheet("color: #111827; font-size: 12px; font-weight: 700; border: none; background: transparent;" if classic else theme_qss("color: @text;"))

        subtitle = QLabel(
            "İş emri, DVI, parça ve teslim akışlarını tek panodan yönetin"
            if self._is_automotive()
            else "Teknik servis iş emri takibi ve durum yönetimi"
        )
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: #4B5563; font-size: 11px; border: none; background: transparent;" if classic else theme_qss("color: @text_muted;"))

        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        title_vbox.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        # Action Buttons Container
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        def _sbtn(icon, tooltip, primary=False):
            b = QPushButton(icon)
            b.setToolTip(tooltip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedSize(40, 40)
            b.setStyleSheet(theme_qss(DesignTokens.get_icon_btn_qss()))
            return b

        btn_add = _sbtn("\U0001f4cb", "Yeni Kay\u0131t A\u00e7", primary=True)
        btn_add.clicked.connect(self.open_new_service_dialog)

        btn_refresh = _sbtn("\U0001f504", "Panoyu Yenile", primary=False)
        btn_refresh.clicked.connect(self.refresh_data)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_refresh)

        btn_archive = _sbtn("\U0001f4da", "T\u00fcm \u0130\u015flemler / Ar\u015fiv", primary=False)
        btn_archive.clicked.connect(
            lambda: (
                self.main_window.switch_page(PageIds.JOB_TRACKING)
                if hasattr(self.main_window, "switch_page")
                else None
            )
        )
        btn_layout.addWidget(btn_archive)

        btn_bulk = _sbtn("\u2699\ufe0f", "Toplu \u0130\u015flem", primary=False)
        btn_bulk.clicked.connect(self.open_bulk_action_dialog)
        btn_layout.addWidget(btn_bulk)

        if self._is_automotive():
            btn_appt = _sbtn("\U0001f4c5", "Randevu Ekle", primary=True)
            btn_appt.clicked.connect(self.open_add_appointment_dialog)
            btn_layout.addWidget(btn_appt)

        header_layout.addLayout(btn_layout)

        layout.addWidget(self.header_widget)

        # 2. The Kanban Board
        self.board = KanbanBoard()
        self.board.setStyleSheet("#KanbanBoard { background: #F3F4F6; border: none; }" if self._is_classic_appearance() else theme_qss("background: @window; border: none;"))
        self.board.card_clicked.connect(self.open_device_detail)
        self.board.action_triggered.connect(self.on_board_action)
        layout.addWidget(self.board)

    def refresh_data(self):
        try:
            from PyQt6.QtCore import QDateTime

            self._last_refresh_msec = QDateTime.currentMSecsSinceEpoch()
        except Exception:
            pass
        # Fetch active devices directly to avoid legacy tuple/index mismatches.
        cur = self.db.conn.cursor()
        try:
            available_columns = {
                row[1] for row in cur.execute("PRAGMA table_info(devices)").fetchall()
            }
        except Exception:
            available_columns = set()
        wanted_columns = [
            "id", "tracking_no", "customer_id", "customer_name", "customer_contact",
            "customer_email", "device_type", "fault_category", "device_brand",
            "device_model", "serial_no", "status", "urgency", "entry_date",
            "exit_date", "estimated_date", "created_at", "price", "labor_cost",
            "cargo_fee", "payment_status", "service_source", "delivery_type",
            "photo_path", "photo_paths", "accessories", "pattern_lock",
            "repair_details", "internal_notes", "fault_description",
            "checklist_status", "warranty_end_date", "approval_status",
            "technician", "vehicle_plate", "vehicle_vin", "vehicle_brand",
            "vehicle_model", "vehicle_year",
        ]
        selected_columns = [col for col in wanted_columns if col in available_columns]
        select_clause = ", ".join(selected_columns) if selected_columns else "*"
        cur.execute(
            f"""
            SELECT {select_clause}
            FROM devices
            WHERE COALESCE(is_deleted, 0)=0 AND COALESCE(is_archived, 0)=0
              AND (
                  COALESCE(status, '') = ''
                  OR (
                      status NOT LIKE '%Teslim%'
                      AND status NOT LIKE '%Kapan%'
                      AND status NOT LIKE '%Kapali%'
                      AND status NOT LIKE '%Kapalı%'
                      AND status NOT LIKE '%Tamamland%'
                      AND status NOT LIKE '%Bitti%'
                      AND status NOT LIKE '%Tamir Edildi%'
                      AND status NOT LIKE '%Hazir%'
                      AND status NOT LIKE '%Hazır%'
                      AND status NOT LIKE '%İptal%'
                      AND status NOT LIKE '%Iptal%'
                      AND status NOT LIKE '%İade%'
                      AND status NOT LIKE '%Iade%'
                  )
              )
            ORDER BY COALESCE(entry_date, created_at, datetime('now')) DESC
            LIMIT 200
            """
        )
        rows = cur.fetchall() or []
        columns = [col[0] for col in (cur.description or [])]
        normalized_devices = []
        for device in rows:
            try:
                row = dict(device)
            except Exception:
                row = dict(zip(columns, device)) if columns else device

            if isinstance(row, dict):
                if self._is_automotive() and hasattr(
                    self.db, "get_device_with_extensions"
                ):
                    try:
                        ext_row = self.db.get_device_with_extensions(
                            tracking_no=row.get("tracking_no"), sector_id="otomotiv"
                        )
                        if ext_row:
                            for field in (
                                "vehicle_plate",
                                "vehicle_vin",
                                "vehicle_brand",
                                "vehicle_model",
                                "vehicle_year",
                            ):
                                if ext_row.get(field) and not row.get(field):
                                    row[field] = ext_row.get(field)
                            if not row.get("device_brand") and ext_row.get(
                                "vehicle_brand"
                            ):
                                row["device_brand"] = ext_row.get("vehicle_brand")
                            if not row.get("device_model") and ext_row.get(
                                "vehicle_model"
                            ):
                                row["device_model"] = ext_row.get("vehicle_model")
                    except Exception as ext_err:
                        logger.debug("Automotive extension merge skipped: %s", ext_err)
                # Normalize status for Kanban column display only — don't re-filter
                row["status"] = normalize_device_status(row.get("status"))
                normalized_devices.append(row)
            else:
                normalized_devices.append(device)
        self._attach_kanban_quick_info(normalized_devices)
        self.board.refresh(normalized_devices)
        self._refresh_navigation_badges()

    def _attach_kanban_quick_info(self, devices):
        """Preload card side-info in bulk to avoid per-card DB queries."""
        dict_devices = [dev for dev in devices if isinstance(dev, dict)]
        tracking_numbers = [
            str(dev.get("tracking_no") or "").strip()
            for dev in dict_devices
            if str(dev.get("tracking_no") or "").strip()
        ]
        if not tracking_numbers:
            return

        quick_info = {tracking_no: [] for tracking_no in tracking_numbers}
        placeholders = ",".join("?" for _ in tracking_numbers)
        cur = self.db.conn.cursor()

        try:
            rows = cur.execute(
                f"""
                SELECT tracking_no, part_name, price
                FROM used_parts
                WHERE tracking_no IN ({placeholders})
                ORDER BY created_at DESC
                """,
                tracking_numbers,
            ).fetchall()
            part_seen = {tracking_no: [] for tracking_no in tracking_numbers}
            for row in rows:
                tracking_no = str(row[0] or "")
                if tracking_no not in part_seen or len(part_seen[tracking_no]) >= 2:
                    continue
                name = str(row[1] or "").strip()
                if name:
                    part_seen[tracking_no].append(name)
            for tracking_no, parts in part_seen.items():
                if parts:
                    quick_info[tracking_no].append("Parçalar: " + ", ".join(parts))
        except Exception as exc:
            logger.debug("Kanban used-parts quick-info preload skipped: %s", exc)

        try:
            rows = cur.execute(
                f"""
                SELECT device_tracking_no, message
                FROM service_logs
                WHERE device_tracking_no IN ({placeholders})
                ORDER BY created_at DESC
                """,
                tracking_numbers,
            ).fetchall()
            seen_logs = set()
            for row in rows:
                tracking_no = str(row[0] or "")
                if tracking_no in seen_logs:
                    continue
                message = str(row[1] or "").strip()
                if tracking_no in quick_info and message:
                    quick_info[tracking_no].append("Son işlem: " + message[:60])
                    seen_logs.add(tracking_no)
        except Exception as exc:
            logger.debug("Kanban service-log quick-info preload skipped: %s", exc)

        for dev in dict_devices:
            tracking_no = str(dev.get("tracking_no") or "").strip()
            dev["_kanban_quick_info"] = quick_info.get(tracking_no, [])

    def _is_automotive(self):
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def open_new_service_dialog(self):
        if self._is_automotive():
            from src.ui.dialogs.vehicle_maintenance_dialog import (
                VehicleMaintenanceDialog,
            )

            dialog = VehicleMaintenanceDialog(
                self.db,
                self.window(),
                sector_manager=self.sector_manager,
            )
        else:
            from src.ui.dialogs.add_device_dialog import AddDeviceDialog
            dialog = AddDeviceDialog(self.db, self)
        if dialog.exec():
            self.refresh_data()

    def open_add_appointment_dialog(self):
        from src.ui.pages.appointments_page import AddAppointmentDialog

        dialog = AddAppointmentDialog(self.db, self)
        if dialog.exec():
            if hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification(
                    "Randevu başarıyla eklendi.", "success"
                )

    def open_device_detail(self, tracking_no):
        tracking_no = str(tracking_no or "").strip()
        now = QDateTime.currentMSecsSinceEpoch()
        last_tracking = str(getattr(self, "_last_opened_tracking_no", "") or "")
        last_time = int(getattr(self, "_last_opened_tracking_msec", 0) or 0)
        if tracking_no and tracking_no == last_tracking and now - last_time < 900:
            return
        self._last_opened_tracking_no = tracking_no
        self._last_opened_tracking_msec = now
        if hasattr(self.db, "get_device_by_tracking_no"):
            row = self.db.get_device_by_tracking_no(tracking_no)
        else:
            row = self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            ).fetchone()
        if row:
            if self._is_automotive():
                from src.ui.dialogs.automotive_technician_panel import (
                    AutomotiveTechnicianPanel as panel_cls,
                )
            else:
                from src.ui.dialogs.technical_service_technician_panel import (
                    TechnicalServiceTechnicianPanel as panel_cls,
                )
            panel = panel_cls(
                self.db, row, self, sector_manager=self.sector_manager
            )
            panel.exec()
            self.refresh_data()

    def _handle_delivery_status_change(self, tracking_no):
        context = self._build_delivery_context(tracking_no)
        if not context:
            show_error(self.main_window or self, "Teslim edilecek servis kaydı bulunamadı.")
            return

        dlg = DeliveryPaymentDialog(self, context, self.db)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        data = dlg.get_data()
        mode = data.get("mode")
        try:
            if not self.db.update_status(tracking_no, "Teslim Edildi"):
                show_error(self.main_window or self, "Teslim durumu kaydedilemedi.")
                return

            if mode == "collect":
                if self._safe_float(data.get("amount")) <= 0:
                    show_success(self.main_window or self, "Cihaz teslim edildi. Kalan tahsilat bulunmuyor.")
                elif not self._save_delivery_payment(context, data):
                    return
                else:
                    show_success(self.main_window or self, "Tahsilat alındı ve cihaz teslim edildi.")
            elif mode == "debt":
                self._ensure_delivery_debt(tracking_no)
                show_info(self.main_window or self, "Cihaz teslim edildi. Tutar cari borç olarak bırakıldı.")
            else:
                show_success(self.main_window or self, "Cihaz teslim edildi.")

            # Müşteriye teslim bildirim maili gönder
            try:
                from src.utils.email_manager import EmailManager
                em = EmailManager(self.db)
                c_email = context.get("customer_email") or context.get("email")
                if not c_email and context.get("customer_id"):
                    try:
                        cust = self.db.get_customer(context["customer_id"])
                        if cust:
                            c_email = cust.get("email")
                    except Exception:
                        pass
                if c_email:
                    em.send_delivery_email(
                        to_email=c_email,
                        customer_name=context.get("customer_name") or "Müşteri",
                        tracking_no=tracking_no,
                        device_name=context.get("device_name") or "Cihaz",
                        total_amount=f"{context.get('total', 0):.2f} {context.get('currency', 'TRY')}"
                    )
            except Exception as mail_err:
                logger.warning("Delivery email sending failed: %s", mail_err)

            self._emit_financial_data_changed()
            self.refresh_data()

        except Exception as exc:
            logger.exception("Delivery payment flow failed")
            show_error(self.main_window or self, f"Teslim/tahsilat işlemi tamamlanamadı: {exc}")

    def _build_delivery_context(self, tracking_no):
        if hasattr(self.db, "get_device_by_tracking_no"):
            row = self.db.get_device_by_tracking_no(tracking_no)
        else:
            row = self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            ).fetchone()
        if not row:
            return None

        device = {key: row[key] for key in row.keys()} if hasattr(row, "keys") else {}
        customer_id = device.get("customer_id")
        customer_name = device.get("customer_name") or ""
        if not customer_id and customer_name and hasattr(self.db, "_resolve_customer_id_by_name"):
            customer_id = self.db._resolve_customer_id_by_name(customer_name)

        labor = self._safe_float(device.get("labor_cost") or device.get("price"))
        cargo = self._safe_float(device.get("cargo_fee"))
        parts_total = self._get_parts_total(tracking_no)
        total = round(max(0.0, labor + cargo + parts_total), 2)

        currency = str(CurrencyHelper.get_code(self.db) or "TRY").upper()
        paid = self._get_paid_for_tracking(customer_id, tracking_no, currency)
        remaining = round(max(0.0, total - paid), 2)

        return {
            "tracking_no": tracking_no,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "phone": device.get("phone_number") or "",
            "device_name": f"{device.get('device_brand') or ''} {device.get('device_model') or ''}".strip(),
            "labor": labor,
            "cargo": cargo,
            "parts_total": parts_total,
            "total": total,
            "paid": paid,
            "remaining": remaining,
            "currency": currency,
        }

    def _safe_float(self, value):
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    def _get_parts_total(self, tracking_no):
        try:
            if hasattr(self.db, "_get_used_parts_total_try"):
                return self._safe_float(
                    self.db._get_used_parts_total_try(tracking_no)
                )
            return 0.0
        except Exception:
            return 0.0

    def _get_paid_for_tracking(self, customer_id, tracking_no, currency):
        if not customer_id:
            return 0.0
        try:
            self.db.cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM currency_transactions
                WHERE customer_id=?
                  AND tracking_no=?
                  AND transaction_type='CREDIT'
                  AND currency=?
                """,
                (customer_id, tracking_no, currency),
            )
            return self._safe_float((self.db.cursor.fetchone() or [0])[0])
        except Exception:
            return 0.0

    def _ensure_delivery_debt(self, tracking_no):
        if hasattr(self.db, "_sync_service_debt_from_tracking"):
            try:
                self.db._sync_service_debt_from_tracking(
                    tracking_no,
                    create_if_missing=True,
                    reason="delivery",
                )
            except Exception as exc:
                logger.warning("Delivery debt sync skipped: %s", exc)

    def _save_delivery_payment(self, context, data):
        customer_id = context.get("customer_id")
        if not customer_id:
            show_error(self.main_window or self, "Tahsilat için müşterinin cari kaydı bulunamadı.")
            return False

        amount = self._safe_float(data.get("amount"))
        if amount <= 0:
            show_warning(self.main_window or self, "Tahsilat tutarı geçersiz.")
            return False

        tracking_no = context.get("tracking_no")
        currency = context.get("currency") or "TRY"
        method = data.get("method") or "Nakit"
        note = data.get("note") or "Teslim anı tahsilatı"
        desc = f"Teslim Tahsilatı: {tracking_no} | {context.get('customer_name') or ''}"
        if note:
            desc = f"{desc} | {note}"

        self._ensure_delivery_debt(tracking_no)

        try:
            exchange_rate = CurrencyHelper.require_rate(self.db, currency)
        except Exception as exc:
            logger.exception("Delivery payment rate lookup failed")
            show_error(
                self.main_window or self,
                f"Kur hatas\u0131: Tahsilat kaydedilemedi: {exc}",
            )
            return False

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        saved = self.db.add_currency_transaction(
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            transaction_type="CREDIT",
            exchange_rate=exchange_rate,
            description=desc,
            tracking_no=tracking_no,
            created_at=created_at,
        )
        if not saved:
            show_error(self.main_window or self, "Tahsilat cari harekete kaydedilemedi.")
            return False

        payment_txn_id = None
        try:
            payment_txn_id = self.db.get_last_currency_transaction_id()
        except Exception:
            payment_txn_id = None

        selected_debt_ids = self._get_tracking_debt_ids(customer_id, tracking_no, currency)
        if payment_txn_id:
            try:
                self.db.apply_payment_to_debts(
                    customer_id=customer_id,
                    payment_amount=amount,
                    currency=currency,
                    payment_transaction_id=payment_txn_id,
                    selected_debt_ids=selected_debt_ids or None,
                )
            except Exception as exc:
                logger.warning("Delivery payment allocation skipped: %s", exc)

        try_amount = amount * exchange_rate
        try:
            self.db.add_transaction(
                t_type="Gelir",
                category="Tahsilat",
                amount=try_amount,
                description=desc,
                customer_name=context.get("customer_name"),
                customer_id=customer_id,
                date=datetime.now().strftime("%Y-%m-%d"),
                payment_method=method,
                tracking_no=tracking_no,
                ref_no=tracking_no,
                currency=currency,
                original_amount=amount,
            )
        except Exception as exc:
            logger.warning("Delivery payment accounting mirror skipped: %s", exc)

        return True

    def _get_tracking_debt_ids(self, customer_id, tracking_no, currency):
        try:
            self.db.cursor.execute(
                """
                SELECT id
                FROM currency_transactions
                WHERE customer_id=?
                  AND tracking_no=?
                  AND transaction_type='DEBIT'
                  AND currency=?
                ORDER BY id DESC
                """,
                (customer_id, tracking_no, currency),
            )
            return [row[0] for row in (self.db.cursor.fetchall() or [])]
        except Exception:
            return []

    def on_board_action(self, action, tracking_no):
        """Handle actions from Kanban Card context menu"""
        logger.debug("Kanban action: %s on %s", action, tracking_no)

        try:
            if action in ("open_technician_panel", "open_detail", "detail", "technician"):
                self.open_device_detail(tracking_no)
                return

            if action == "print_barcode":
                try:
                    if hasattr(self.db, "get_device_by_tracking_no"):
                        dev = self.db.get_device_by_tracking_no(
                            tracking_no,
                            columns=[
                                "tracking_no",
                                "customer_name",
                                "device_brand",
                                "device_model",
                            ],
                        )
                    else:
                        dev = self.db.cursor.execute(
                            "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                            (tracking_no,),
                        ).fetchone()
                    if dev:
                        # Using column names for robustness
                        brand = dev["device_brand"] or ""
                        model_name = dev["device_model"] or ""
                        model = f"{brand} {model_name}".strip()
                        customer = dev["customer_name"] or ""
                        html = f"""
                            <html>
                            <head><meta charset="UTF-8"></head>
                            <body style="text-align: center; font-family: Arial; margin:0;">
                                <div style="width: 200px; height: 100px; border: 1px solid black; margin: 10px auto; padding: 5px;">
                                    <div style="font-size: 10px; font-weight: bold;">{model}</div>
                                    <div style="font-size: 20px; font-family: monospace; letter-spacing: 2px; margin: 5px 0;">{tracking_no}</div>
                                    <div style="font-size: 9px;">{customer}</div>
                                </div>
                            </body>
                            </html>
                         """
                        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                        dialog = QPrintDialog(printer, self)
                        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                            doc = QTextDocument()
                            doc.setHtml(html)
                            doc.print(printer)
                            show_success(self.main_window, "Barkod etiketi yazdırıldı.")
                except Exception as e:
                    logger.error(f"Service board print error: {e}")
                    show_info(self.main_window, f"Yazdırma hatası: {e}")

            elif action.startswith("update_status:"):
                new_status = action.split(":")[1]
                if new_status == "Teslim Edildi":
                    self._handle_delivery_status_change(tracking_no)
                    return
                try:
                    self.db.update_status(tracking_no, new_status)
                    self.refresh_data()
                    show_success(
                        self.main_window, f"Durum Güncellendi: {new_status}"
                    )
                except Exception as e:
                    logger.error(f"Service board status update error: {e}")

            elif action == "cancel":
                reply = (
                    self.main_window.reply_question(
                        "İptal Onayı",
                        "Bu servisi iptal etmek istediğinize emin misiniz",
                    )
                    if hasattr(self.main_window, "reply_question")
                    else None
                )
                if reply is False:
                    return
                try:
                    self.db.update_status(tracking_no, "İptal")
                    self.refresh_data()
                except Exception as e:
                    logger.error(f"Service board cancel error: {e}")

            elif action == "whatsapp":
                try:
                    dev = self.db.cursor.execute(
                        """
                        SELECT customer_name, phone_number, device_brand, device_model, status
                        FROM devices
                        WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0
                        """,
                        (tracking_no,),
                    ).fetchone()
                    if not dev:
                        show_error(self.main_window or self, "Servis kaydı bulunamadı.")
                        return

                    customer_name = dev["customer_name"] or "Müşteri"
                    phone = "".join(filter(str.isdigit, str(dev["phone_number"] or "")))
                    if not phone:
                        show_error(
                            self.main_window or self,
                            "Müşteri telefon numarası kayıtlı değil.",
                        )
                        return
                    if phone.startswith("0") and len(phone) == 11:
                        phone = "9" + phone
                    elif len(phone) == 10:
                        phone = "90" + phone

                    model = f"{dev['device_brand'] or ''} {dev['device_model'] or ''}".strip()
                    message = (
                        f"Sayın {customer_name},\n\n"
                        f"{tracking_no} takip numaralı {model or 'cihazınız'} için güncel durum: {dev['status'] or '-'}.\n\n"
                        "AYEC Pro"
                    )
                    encoded = urllib.parse.quote(message)
                    QDesktopServices.openUrl(
                        QUrl(f"https://wa.me/{phone}?text={encoded}")
                    )
                except Exception as e:
                    show_error(
                        self.main_window or self, f"WhatsApp bağlantısı açılamadı: {e}"
                    )
        except Exception as e:
            if hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification(f"İşlem hatası: {e}", "error")
            else:
                logger.error(f"Service board critical action error: {e}")

    def setup_usage_guide_tab(self):
        ly = QVBoxLayout(self.tab_guide)
        ly.setContentsMargins(0, 10, 0, 0)

        from PyQt6.QtWidgets import QTextBrowser
        from src.utils.design_system import DesignTokens
        from src.utils.theme_colors import tc

        guide_text = QTextBrowser()
        guide_text.setStyleSheet(
            "border: none; background: transparent; padding: 20px;"
        )

        html_content = f"""
        <div style="font-family: {DesignTokens.FONT_FAMILY}; color: @text;">
            <h1 style="color: @accent;">🛠️ Servis Operasyon Panosu Kullanım Kılavuzu</h1>
            <p>
                Bu pano, otomotiv servis iş emirlerini bekleyen, tamirde, parça bekliyor,
                test/onay, teslim ve iptal akışında tek ekrandan yönetmeniz için tasarlanmıştır.
            </p>

            <h2 style="color: @primary;">1. Kolonlar ve İş Emri Akışı</h2>
            <ul>
                <li><b>Bekliyor:</b> Yeni açılan iş emirleri ve ilk kontrol bekleyen araçlar.</li>
                <li><b>Tamirde:</b> Teknisyenin aktif çalıştığı araçlar ve devam eden işlemler.</li>
                <li><b>Parça Bekliyor:</b> Siparişe düşen veya stoktan karşılanması gereken kalemler.</li>
                <li><b>Test / Onay:</b> Kontrol listesi, son test ve müşteri onayı aşaması.</li>
                <li><b>Teslim:</b> İşçiliği tamamlanan ve teslim hazırlığı yapılan araçlar.</li>
                <li><b>İptal:</b> Kapatılan veya iptal edilen kayıtlar.</li>
            </ul>

            <h2 style="color: @primary;">2. Teknisyen Paneli Kullanımı</h2>
            <ul>
                <li><b>Kontrol Listesi:</b> Periyodik bakım, fren veya ağır bakım şablonlarını işleyin.</li>
                <li><b>Teknisyen Notu:</b> Şikayet, tespit, yapılan işlem ve önerileri düzenli kaydedin.</li>
                <li><b>Parça ve Stok:</b> "Araca Takıldı" akışına göre maliyet ve stok hareketini eşleştirin.</li>
                <li><b>Fotoğraf Galerisi:</b> Öncesi/sonrası görselleri kanıt olarak iş emrine ekleyin.</li>
                <li><b>İşçilik Süresi:</b> İşçilik ve toplam maliyet kalemlerini kayıt altında tutun.</li>
            </ul>

            <h2 style="color: @primary;">3. Hızlı İşlemler</h2>
            <ul>
                <li><b>Yeni Kayıt Aç:</b> VIN/plaka ile araç kaydı oluşturup iş emrini başlatın.</li>
                <li><b>Çift Tıklama:</b> Kartı açarak teknisyen panelinde detaylı işlem yapın.</li>
                <li><b>Sağ Tık:</b> Durum güncelleme, barkod yazdırma ve WhatsApp bilgilendirmesini kullanın.</li>
                <li><b>Toplu İşlem:</b> Birden fazla kaydın durumunu aynı anda güncelleyin.</li>
            </ul>

            <h2 style="color: @primary;">4. Operasyon Notları</h2>
            <p>Stok düşümü, parça hareketi ve kritik adımlarda kayıt bırakmak hataları azaltır.</p>
            <p>Otomotiv sektörü seçili değilse bu akış menü ve iş kurallarında pasif kalmalıdır.</p>

            <hr style="border: 0; border-top: 1px solid @border; margin: 20px 0;">
            <p style="color: @text_muted; font-style: italic;">AYEC Pro Otomotiv Servis Yönetimi - Hızlı, izlenebilir ve kanıt odaklı iş akışı</p>
        </div>
        """
        final_html = (
            html_content.replace("@text_muted", tc("text_muted"))
            .replace("@text", tc("text"))
            .replace("@accent", tc("accent"))
            .replace("@primary", tc("primary"))
            .replace("@border", tc("border"))
        )

        guide_text.setHtml(final_html)
        ly.addWidget(guide_text)

    def open_bulk_action_dialog(self):
        """Toplu durum değiştirme diyaloğu — birden fazla servis seçilip status uygulanır."""
        try:
            devices = self.db.get_all_devices(
                columns=[
                    "tracking_no",
                    "device_brand",
                    "device_model",
                    "device_type",
                    "status",
                ],
                limit=300,
            ) or []
            active = [d for d in devices if is_active_device_status(d.get("status"))]
        except Exception as e:
            logger.error("Bulk action device load error: %s", e)
            active = []

        dlg = QDialog(self)
        dlg.setWindowTitle("Toplu İşlem")
        dlg.resize(820, 560)
        dlg.setStyleSheet(
            theme_qss("QDialog { background: @surface; } QLabel { color: @text; }")
        )
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(12)

        top = QHBoxLayout()
        lbl = QLabel("Durum değiştirmek istediğiniz servisleri seçin:")
        lbl.setStyleSheet(
            theme_qss("font-weight: bold; font-size: 13px; color: @text;")
        )
        top.addWidget(lbl)
        top.addStretch()
        btn_all = QPushButton("Tümünü Seç")
        btn_all.setFixedHeight(32)
        btn_all.setStyleSheet(
            theme_qss(
                "background: @surface_alt; border: 1px solid @border; border-radius: 6px; color: @text; padding: 0 10px;"
            )
        )
        btn_none = QPushButton("Hiçbirini Seçme")
        btn_none.setFixedHeight(32)
        btn_none.setStyleSheet(
            theme_qss(
                "background: @surface_alt; border: 1px solid @border; border-radius: 6px; color: @text; padding: 0 10px;"
            )
        )
        top.addWidget(btn_all)
        top.addWidget(btn_none)
        vl.addLayout(top)

        tbl = QTableWidget(len(active), 4)
        tbl.setHorizontalHeaderLabels(["", "Takip No", "Cihaz", "Durum"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        tbl.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        tbl.setColumnWidth(0, 38)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setStyleSheet(
            theme_qss(
                "QTableWidget { background: @surface; color: @text; border: 1px solid @border; } QTableWidget::item:selected { background: @selection_bg; color: @selection_text; }"
            )
        )

        checks = []
        for i, d in enumerate(active):
            cb = QCheckBox()
            cb_w = QWidget()
            cb_l = QHBoxLayout(cb_w)
            cb_l.setContentsMargins(6, 0, 0, 0)
            cb_l.addWidget(cb)
            tbl.setCellWidget(i, 0, cb_w)
            tbl.setItem(i, 1, QTableWidgetItem(str(d.get("tracking_no", ""))))
            tbl.setItem(
                i,
                2,
                QTableWidgetItem(
                    f"{d.get('device_brand', '')} {d.get('device_model', '')}"
                ),
            )
            tbl.setItem(i, 3, QTableWidgetItem(str(d.get("status", ""))))
            tbl.setRowHeight(i, 40)
            checks.append((cb, d.get("tracking_no")))

        btn_all.clicked.connect(lambda: [c.setChecked(True) for c, _ in checks])
        btn_none.clicked.connect(lambda: [c.setChecked(False) for c, _ in checks])
        vl.addWidget(tbl)

        # Status selector + apply
        bot = QHBoxLayout()
        bot.addWidget(QLabel("Yeni Durum:"))
        cmb_status = QComboBox()
        cmb_status.addItems(
            [
                "Beklemede",
                "İşlemde",
                "Parça Bekliyor",
                "Teslime Hazır",
                "Teslim Edildi",
                "İptal",
            ]
        )
        cmb_status.setFixedHeight(36)
        cmb_status.setStyleSheet(
            theme_qss(
                "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 6px; padding: 0 8px; }"
            )
        )
        bot.addWidget(cmb_status)
        bot.addStretch()
        btn_apply = QPushButton("✅ Uygula")
        btn_apply.setFixedHeight(38)
        btn_apply.setStyleSheet(
            theme_qss(
                "QPushButton { background: @accent; color: @selection_text; border: none; border-radius: 8px; font-weight: bold; padding: 0 20px; } QPushButton:hover { background: @accent_hover; }"
            )
        )
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setStyleSheet(
            theme_qss(
                "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; padding: 0 16px; }"
            )
        )
        btn_cancel.clicked.connect(dlg.reject)
        bot.addWidget(btn_cancel)
        bot.addWidget(btn_apply)
        vl.addLayout(bot)

        def apply_bulk():
            selected = [(cb, tno) for cb, tno in checks if cb.isChecked()]
            if not selected:
                show_info(self.main_window or self, "Lütfen en az bir servis seçin.")
                return
            new_status = cmb_status.currentText()
            updated = 0
            for _, tno in selected:
                try:
                    self.db.update_status(tno, new_status)
                    updated += 1
                except Exception as e:
                    logger.error("Bulk status update error for %s: %s", tno, e)
            dlg.accept()
            self.refresh_data()
            show_success(
                self.main_window or self,
                f"{updated} servisin durumu '{new_status}' olarak güncellendi.",
            )

        btn_apply.clicked.connect(apply_bulk)
        dlg.exec()

    def apply_theme_styles(self):
        """Dinamik tema renklerini güncelle."""
        self.tabs.setStyleSheet(self._tabs_qss())
        self.header_widget.setStyleSheet(self._header_qss())
        effect = self.header_widget.graphicsEffect()
        if effect is not None:
            effect.setEnabled(not self._is_classic_appearance())
        if hasattr(self, "board") and self.board:
            self.board.setStyleSheet("#KanbanBoard { background: #F3F4F6; border: none; }" if self._is_classic_appearance() else theme_qss("background: @window; border: none;"))
            self.board.apply_theme_styles()
