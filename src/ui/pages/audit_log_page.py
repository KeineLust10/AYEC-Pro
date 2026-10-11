# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QFrame, QHBoxLayout, QPushButton, QTabWidget, QScrollArea, QGridLayout, QLineEdit, QComboBox, QFileDialog, QButtonGroup, QStyledItemDelegate)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QAction, QPalette
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.design_system import DesignTokens
from src.utils.audit_logger import AuditLogger
from src.utils.logger import logger
from src.ui.widgets.empty_state import EmptyState
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel
from src.ui.widgets.toast_notification import show_toast
from src.utils.audit_export import export_audit_csv, export_audit_event_pdf
from src.utils.role_utils import normalize_role, is_admin_role
from src.utils.user_account_actions import resolve_audit_account, set_user_account_active, current_account_administrator
import json


class _AuditCompositeDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.palette.setColor(QPalette.ColorRole.Highlight, QColor("#222a3d"))
        option.palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#dae2fd"))
        if index.column() in (1, 3):
            option.text = ""


def _audit_record_metadata(record):
    try:
        payload = json.loads(record[4] or "{}")
    except (TypeError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        return "-", "-"
    severity = payload.get("severity") or payload.get("level") or "-"
    station = payload.get("station") or payload.get("station_id")
    ip = payload.get("ip") or payload.get("client_ip")
    location = " / ".join(str(value) for value in (station, ip) if value not in (None, ""))
    return str(severity), location or "-"

class AuditLogPage(QWidget):
    """Sistem Günlükleri (Audit Log) Sayfası"""
    def __init__(self, db, audit_logger=None):
        super().__init__()
        self.db = db
        self.audit_page_index = 0
        self.audit_page_size = 25
        self.audit_filtered_count = 0
        self.audit_logger = audit_logger if audit_logger is not None else AuditLogger(db)
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tab_main = QWidget()
        self.setup_main_tab()
        self.tabs.addTab(self.tab_main, "🛡️ Sistem Günlükleri")
        
        # 2. How to Use? Tab
        from src.utils.system_config import SystemConfig
        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "❓ Nasıl Kullanılır?")
            
        self.layout.addWidget(self.tabs)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_logs_if_live_stream_paused)
        self.load_logs()

    def setup_main_tab(self):
        layout = QVBoxLayout(self.tab_main)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        # Main Background
        self.tab_main.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.tab_main.setObjectName("AuditOperationalCanvas")
        self.tab_main.setStyleSheet(theme_qss("QWidget#AuditOperationalCanvas { background-color: @finance_canvas; }"))

        # Card Container
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(theme_qss("""
            #Card {
                background-color: @finance_canvas;
                border: none;
                border-radius: 4px;
            }
        """))
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(8)
        
        # Header Box
        header_lay = QHBoxLayout()
        header = QLabel("[AUDIT] Log Kay\u0131tlar\u0131 & G\u00fcvenlik Denetimi")
        header.setFont(QFont(DesignTokens.FONT_NAME, 13, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text; padding-bottom: 5px; border: none;"))
        header.setWordWrap(True)
        header_lay.addWidget(header)
        header_lay.addStretch()
        card_layout.addLayout(header_lay)

        header_actions = QHBoxLayout()
        header_actions.addStretch()

        self.btn_live_stream = QPushButton("Canli Akisi Durdur")
        self.btn_live_stream.setCheckable(True)
        self.btn_live_stream.setFixedHeight(32)
        self.btn_live_stream.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_live_stream.toggled.connect(
            lambda paused: self.btn_live_stream.setText("Canli Akisi Baslat" if paused else "Canli Akisi Durdur")
        )
        header_actions.addWidget(self.btn_live_stream)
        reset_filters = QPushButton("Filtreleri Sifirla")
        reset_filters.setFixedHeight(32)
        reset_filters.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        reset_filters.clicked.connect(self._reset_audit_filters)
        header_actions.addWidget(reset_filters)
        export_logs = QPushButton("Loglari Disa Aktar")
        self.export_logs_button = export_logs
        export_logs.setFixedHeight(32)
        export_logs.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        export_logs.clicked.connect(self._export_audit_logs)
        header_actions.addWidget(export_logs)
        
        self.btn_refresh = QPushButton("🔄 Listeyi Yenile")
        self.btn_refresh.setFixedSize(122, 32)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @finance_surface; color: @finance_primary; border: 1px solid @finance_outline; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: @selection_bg; }
        """))
        self.btn_refresh.clicked.connect(self.load_logs)
        header_actions.addWidget(self.btn_refresh)
        card_layout.addLayout(header_actions)
        
        sub_header = QLabel("Uygulama genelinde yapılan kritik işlemler ve güvenlik kayıtları")
        sub_header.setFixedHeight(18)
        sub_header.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; border: none;"))
        card_layout.addWidget(sub_header)

        security_status = QHBoxLayout()
        for text, color in (("Imza dogrulama verisi yok", "@text_muted"), ("Saklama politikasi verisi yok", "@text_muted"), ("Syslog telemetrisi yok", "@text_muted")):
            status = QLabel(text)
            status.setFixedHeight(22)
            status.setStyleSheet(theme_qss(f"color: {color}; background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: 700;"))
            security_status.addWidget(status)
        security_status.addStretch()
        card_layout.addLayout(security_status)

        metrics = QGridLayout()
        metrics.setSpacing(8)
        self._audit_metric_cards = []
        for title, value, note, color in (
            ("TOPLAM KAYIT", "0", "Kayitli audit hareketleri", "@finance_primary"),
            ("GUVENLIK ALARMLARI & HATA", "0", "Yuklenen sayfada", "@danger"),
            ("KAYITLI KULLANICILAR", "0", "Yuklenen sayfada", "@finance_secondary"),
            ("VERI BUTUNLUGU", "-", "Dogrulama verisi yok", "@finance_tertiary"),
        ):
            metric = QFrame()
            metric.setFixedHeight(88)
            metric.setStyleSheet(theme_qss(f"""
                QFrame {{ background: @finance_surface_alt; border: 1px solid @finance_outline; border-top: 2px solid {color}; border-radius: 6px; }}
                QLabel {{ border: none; }}
            """))
            ml = QVBoxLayout(metric)
            ml.setContentsMargins(10, 8, 10, 8)
            label = QLabel(title)
            label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; font-weight: 700;"))
            number = ReferenceMetricValueLabel(value, primary_token=color.replace('@', ''), primary_size=21)
            number.setToolTip(f"{title}: {value}")
            number.setStyleSheet(theme_qss(f"color: {color}; font-size: 21px; font-weight: 800;"))
            detail = QLabel(note)
            detail.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px;"))
            ml.addWidget(label); ml.addWidget(number); ml.addWidget(detail)
            metrics.addWidget(metric, 0, len(self._audit_metric_cards))
            self._audit_metric_cards.append((number, detail))
        card_layout.addLayout(metrics)

        filter_bar = QHBoxLayout()
        self.audit_search = QLineEdit()
        self.audit_search.setPlaceholderText("Kullanici adi, IP, islem no veya detay arayin...")
        self.audit_search.setStyleSheet(theme_qss("QLineEdit { background: @finance_surface; color: @finance_text; border: 1px solid @finance_outline; border-radius: 4px; padding: 5px; }"))
        self.audit_scope = ModernComboBox()
        self.audit_scope.addItem("Tum Moduller", None)
        self.audit_scope.addItem("Sistem", ("system", "sistem", "auth", "users", "settings", "logs", "audit", "backup"))
        self.audit_scope.addItem("Finans", ("finance", "finans", "financial", "accounting", "currency", "bank", "invoice", "e_invoice", "payment", "cash", "check", "cheque"))
        self.audit_scope.addItem("Servis", ("service", "servis", "srv", "device", "repair", "appointment", "field", "technician"))
        self.audit_scope.setObjectName("audit_scope_filter")
        self.audit_scope.setProperty("referenceGlyph", "chevron_down")
        self.audit_scope.setStyleSheet(theme_qss("QComboBox { background: @finance_surface_alt; color: @finance_text; border: 1px solid @finance_outline; padding: 7px; }"))
        filter_bar.addWidget(self.audit_search, 1); filter_bar.addWidget(self.audit_scope)
        card_layout.addLayout(filter_bar)

        severity_bar = QHBoxLayout()
        severity_bar.setSpacing(6)
        self.audit_severity = "Tumu"
        self.audit_severity_buttons = {}
        self.audit_severity_group = QButtonGroup(self)
        self.audit_severity_group.setExclusive(True)
        for label in ("Tumu", "INFO", "WARN", "CRITICAL", "SECURITY"):
            chip = QPushButton(label)
            chip.setCheckable(True)
            self.audit_severity_group.addButton(chip)
            self.audit_severity_buttons[label] = chip
            chip.setChecked(label == "Tumu")
            chip.setFixedHeight(28)
            chip.setStyleSheet(theme_qss(
                "QPushButton { background: @finance_surface_alt; color: @finance_text_muted; "
                "border: 1px solid @finance_outline; border-radius: 5px; padding: 4px 10px; } "
                "QPushButton:checked { background: @selection_bg; color: @selection_text; border-color: @finance_primary; }"
            ))
            chip.clicked.connect(lambda checked, value=label: self._set_audit_severity(value))
            severity_bar.addWidget(chip)
        severity_bar.addStretch()
        self.raw_columns_button = QPushButton("Ham Sutunlar")
        self.raw_columns_button.setCheckable(True)
        self.raw_columns_button.toggled.connect(lambda enabled: self.table.setColumnHidden(2, not enabled))
        severity_bar.addWidget(self.raw_columns_button)
        card_layout.addLayout(severity_bar)
        self.audit_search.textChanged.connect(self._reload_filtered_audit_logs)
        self.audit_scope.currentTextChanged.connect(self._reload_filtered_audit_logs)
        
        # Log Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Zaman", "Kullan\u0131c\u0131", "Tablo", "\u0130\u015flem / Eylem", "Payload \u00d6zeti", "Seviye", "\u0130stasyon / IP"])
        self.table.setItemDelegate(_AuditCompositeDelegate(self.table))
        self.table.setColumnHidden(2, True)
        for visual_position, logical_column in enumerate((0, 5, 3, 1, 6, 4, 2)):
            self.table.horizontalHeader().moveSection(self.table.horizontalHeader().visualIndex(logical_column), visual_position)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._update_audit_inspector)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(82)
        self.table.setFixedHeight(320)
        
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @finance_surface; alternate-background-color: @finance_surface_alt; border: none; border-radius: 4px; gridline-color: transparent; font-size: 11px; color: @finance_text;
                selection-background-color: #222a3d; selection-color: #dae2fd;
            }
            QTableWidget::item { padding: 6px; border-bottom: 1px solid @finance_outline; }
            QTableWidget::item:selected { background: @finance_surface_alt; color: @finance_text; }
            QHeaderView::section { background-color: @finance_surface_alt; color: @finance_text_muted; font-size: 10px; font-weight: 700; padding: 6px; border: none; border-bottom: 1px solid @finance_outline; }
        """))
        log_content = QHBoxLayout()
        log_content.setSpacing(12)
        log_content.addWidget(self.table, 2)
        self.inspector_panel = self._build_inspector_panel()
        self.inspector_panel.setFixedHeight(320)
        log_content.addWidget(self.inspector_panel, 1)
        card_layout.addLayout(log_content)
        pagination = QHBoxLayout()
        self.audit_page_label = QLabel("-")
        pagination.addWidget(self.audit_page_label)
        pagination.addStretch()
        self.audit_previous_button = QPushButton("Onceki")
        self.audit_previous_button.clicked.connect(lambda: self._change_audit_page(-1))
        pagination.addWidget(self.audit_previous_button)
        self.audit_next_button = QPushButton("Sonraki")
        self.audit_next_button.clicked.connect(lambda: self._change_audit_page(1))
        pagination.addWidget(self.audit_next_button)
        card_layout.addLayout(pagination)
        self.empty_state = EmptyState("Henüz günlük yok", "Sistem ve güvenlik hareketlerine ait kayıt bulunamadı.", parent=self)
        self.empty_state.hide()
        card_layout.addWidget(self.empty_state)
        card_layout.addStretch()
        layout.addWidget(card)

    def _reset_audit_filters(self):
        self.audit_search.clear()
        self.audit_scope.setCurrentIndex(0)
        self.audit_severity = "Tumu"
        self.audit_severity_buttons["Tumu"].setChecked(True)
        self._reload_filtered_audit_logs()

    def _build_inspector_panel(self):
        panel = QFrame()
        panel.setStyleSheet(theme_qss(
            "QFrame { background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 4px; }"
            "QLabel { background: transparent; border: none; }"
        ))
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(8)
        heading = QLabel("Denetci Payload Inspector")
        heading.setStyleSheet(theme_qss("font-size: 14px; font-weight: 850; color: @text;"))
        panel_layout.addWidget(heading)
        critical = QLabel("Bir audit kaydi secin.")
        self.inspector_metadata = critical
        critical.setTextFormat(Qt.TextFormat.PlainText)
        critical.setWordWrap(True)
        critical.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; line-height: 1.45;"))
        panel_layout.addWidget(critical)
        diff = QLabel("Kayitli islem ayrintilari burada gosterilir.")
        self.inspector_details = diff
        diff.setTextFormat(Qt.TextFormat.PlainText)
        diff.setWordWrap(True)
        diff.setStyleSheet(theme_qss("background: @surface; color: @text; border: 1px solid @border; border-radius: 6px; padding: 8px; font-size: 10px;"))
        panel_layout.addWidget(diff)
        panel_layout.addStretch()
        action = QPushButton("Kullaniciyi Kilitle")
        self.suspend_user_button = action
        action.clicked.connect(self._suspend_audit_account)
        action.setMinimumHeight(34)
        action.setStyleSheet(theme_qss(DesignTokens.get_button_qss("danger", size="sm")))
        panel_layout.addWidget(action)
        report = QPushButton("Adli Bilisim Olay Raporu Olustur (PDF)")
        self.event_report_button = report
        report.clicked.connect(self._export_selected_audit_event)
        report.setMinimumHeight(34)
        report.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        panel_layout.addWidget(report)
        return panel

    def _audit_administrator_context(self):
        return current_account_administrator(self, self.db)

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start(10000)
        self._update_audit_inspector()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def _refresh_logs_if_live_stream_paused(self):
        if self.isVisible() and not self.btn_live_stream.isChecked():
            self.load_logs()

    def _suspendable_audit_account(self):
        context = self._audit_administrator_context()
        log = getattr(self, "inspector_log", None)
        if not context or not log:
            return None
        account = resolve_audit_account(self.db, log[1])
        if not account or not account[2] or str(account[0]) == str(context["id"]):
            return None
        return account

    def _suspend_audit_account(self):
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog

        account = self._suspendable_audit_account()
        if not account:
            return
        confirm = ModernConfirmDialog(
            "Hesap Erisimini Durdur",
            f"{account[1]} (ID: {account[0]}) hesabinin yeni girisleri engellenecek. Acik oturumlar sonlandirilmaz. Devam edilsin mi?",
            self, confirm_text="Erisimi Durdur", cancel_text="Iptal", destructive=True,
        )
        if confirm.exec() and self._suspendable_audit_account() == account:
            try:
                set_user_account_active(self.db, account[0], False)
                self._update_audit_inspector()
                show_toast(self, "Hesap yeni girislere kapatildi. Acik oturumlar degistirilmedi.", "success")
            except Exception as exc:
                show_toast(self, f"Hesap durumu degistirilemedi: {exc}", "error")

    def _export_audit_logs(self):
        records = []
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                item = self.table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole):
                    records.append(item.data(Qt.ItemDataRole.UserRole))
        path, _selected_filter = QFileDialog.getSaveFileName(self, "Audit Kayitlarini Aktar", "audit_logs.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            export_audit_csv(path, records)
            show_toast(self, f"{len(records)} audit kaydi aktarildi.", "success")
        except Exception as exc:
            show_toast(self, f"Aktarim basarisiz: {exc}", "error")

    def _export_selected_audit_event(self):
        log = getattr(self, "inspector_log", None)
        if not log:
            return
        path, _selected_filter = QFileDialog.getSaveFileName(self, "Audit Olay Raporu", f"audit_event_{log[0]}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            export_audit_event_pdf(path, log)
            show_toast(self, "Kayitli audit olay raporu olusturuldu.", "success")
        except Exception as exc:
            show_toast(self, f"Rapor olusturulamadi: {exc}", "error")

    def _update_audit_inspector(self):
        if not hasattr(self, "inspector_metadata"):
            return
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        log = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.inspector_log = log
        self.event_report_button.setEnabled(bool(log))
        self.suspend_user_button.setEnabled(self._suspendable_audit_account() is not None)
        self.suspend_user_button.setToolTip("Yonetici onayi ile yeni girisleri engeller; acik oturumlari kapatmaz. Kayitli baska bir aktif hesap gereklidir.")
        if not log:
            self.inspector_metadata.setText("Bir audit kaydi secin.")
            self.inspector_details.setText("Kayitli islem ayrintilari burada gosterilir.")
            return
        self.inspector_metadata.setText(
            f"Kayit: {log[0]}\nKullanici: {log[1]}\nTablo: {log[2]}\nIslem: {log[3]}\nZaman: {log[5]}"
        )
        self.inspector_details.setText(str(log[4] or "Ayrinti yok."))

    def _set_audit_severity(self, value):
        self.audit_severity = value
        self._reload_filtered_audit_logs()

    def _reload_filtered_audit_logs(self, *_args):
        self.audit_page_index = 0
        self.load_logs()

    def _change_audit_page(self, delta):
        pages = max(1, (self.audit_filtered_count + self.audit_page_size - 1) // self.audit_page_size)
        if 0 <= self.audit_page_index + delta < pages:
            self.audit_page_index += delta
            self.load_logs()

    def _apply_log_filters(self):
        query = self.audit_search.text().strip().lower() if hasattr(self, "audit_search") else ""
        scope_prefixes = self.audit_scope.currentData() if hasattr(self, "audit_scope") else None
        severity = getattr(self, "audit_severity", "Tumu")
        for row in range(self.table.rowCount()):
            values = []
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item:
                    values.append(item.text().lower())
                cell_widget = self.table.cellWidget(row, column)
                if isinstance(cell_widget, QLabel):
                    values.append(cell_widget.text().lower())
            haystack = " ".join(values)
            visible = (not query or query in haystack)
            if severity != "Tumu":
                severity_item = self.table.item(row, 5)
                visible = visible and bool(severity_item and severity_item.text().upper() == severity)
            if scope_prefixes:
                table_item = self.table.item(row, 2)
                table_name = table_item.text().strip().lower() if table_item else ""
                visible = visible and table_name.startswith(tuple(scope_prefixes))
            self.table.setRowHidden(row, not visible)
        current = self.table.currentRow()
        if current < 0 or self.table.isRowHidden(current):
            visible_row = next((row for row in range(self.table.rowCount()) if not self.table.isRowHidden(row)), None)
            if visible_row is None:
                self.table.clearSelection()
                self.table.setCurrentCell(-1, -1)
            else:
                self.table.selectRow(visible_row)
        self._update_audit_inspector()

    def setup_usage_guide_tab(self):
        from src.utils.design_system import DesignTokens
        layout = QVBoxLayout(self.tab_guide)
        layout.setContentsMargins(40, 40, 40, 40)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(20)
        
        guide_text = f"""
        <h1 style='color: {tc("accent")};'>🛡️ Sistem Günlükleri Kullanım Kılavuzu</h1>
        <p style='font-size: 14px; color: {tc("text")};'>Uygulama genelinde yapılan tüm kritik işlemler burada kayıt altına alınır.</p>
        
        <h3 style='color: {tc("accent")};'>📋 İzlenen İşlemler</h3>
        <ul style='color: {tc("text")}; line-height: 1.6;'>
            <li><b>Giriş/Çıkış:</b> Kullanıcıların sisteme giriş ve çıkış zamanları.</li>
            <li><b>Veri Değişiklikleri:</b> Stok ekleme, müşteri silme veya kasa hareketleri.</li>
            <li><b>Sistem Ayarları:</b> Genel konfigürasyon değişiklikleri.</li>
            <li><b>Hatalar:</b> Sistem tarafında oluşan kritik çalışma zamanı hataları.</li>
        </ul>
        """
        
        lbl = QLabel(guide_text)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        cl.addWidget(lbl)
        cl.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        self._apply_dark_mode_if_needed()
        
    @staticmethod
    def _audit_composite_label(text):
        label = QLabel(str(text))
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setMargin(4)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        label.setToolTip(str(text))
        label.setStyleSheet(theme_qss("QLabel { background: transparent; border: none; color: @finance_text; font-size: 10px; }"))
        return label

    def load_logs(self):
        """Gerçek log verilerini veritabanından çeker"""
        try:
            self.table.setRowCount(0)
            options = dict(query=self.audit_search.text(), scope_prefixes=self.audit_scope.currentData(), severity=self.audit_severity)
            logs, self.audit_filtered_count = self.audit_logger.get_recent_activity_page(
                limit=self.audit_page_size, offset=self.audit_page_index * self.audit_page_size, **options
            )
            pages = max(1, (self.audit_filtered_count + self.audit_page_size - 1) // self.audit_page_size)
            if self.audit_page_index >= pages:
                self.audit_page_index = pages - 1
                logs, self.audit_filtered_count = self.audit_logger.get_recent_activity_page(
                    limit=self.audit_page_size, offset=self.audit_page_index * self.audit_page_size, **options
                )
            self.audit_page_label.setText(f"{self.audit_filtered_count} kayit | Her sayfada {self.audit_page_size} | Sayfa {self.audit_page_index + 1} / {pages}")
            self.audit_previous_button.setEnabled(self.audit_page_index > 0)
            self.audit_next_button.setEnabled(self.audit_page_index + 1 < pages)
            has_logs = bool(logs)
            if hasattr(self, "_audit_metric_cards"):
                total_count = len(logs)
                try:
                    total_count = int(self.db.cursor.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] or 0)
                except Exception:
                    pass
                alarm_count = sum(1 for log in logs if str(log[3] or "").upper() in {"BLOCK", "ERROR", "CRITICAL"})
                station_count = len({str(log[1] or "") for log in logs})
                self._audit_metric_cards[0][0].setText("{:,.0f}".format(total_count))
                self._audit_metric_cards[1][0].setText(str(alarm_count))
                self._audit_metric_cards[2][0].setText(str(station_count))
            self.table.setVisible(has_logs)
            self.empty_state.setVisible(not has_logs)
            if not logs:
                return

            self.table.setRowCount(len(logs))
            try:
                account_rows = self.db.conn.execute(
                    "SELECT u.id, u.username, u.role, p.name FROM users u LEFT JOIN personnel p ON p.id=u.personnel_id"
                ).fetchall()
                account_names = {str(row[0]): row for row in account_rows}
                for account in account_rows:
                    account_names.setdefault(str(account[1]), account)
            except Exception:
                account_names = {}
            for r, log in enumerate(logs):
                # audit_logs schema: id(0), user_id(1), table_name(2), action(3), details(4), created_at(5)
                
                # Zaman
                time_item = QTableWidgetItem(str(log[5]))
                time_item.setData(Qt.ItemDataRole.UserRole, tuple(log))
                self.table.setItem(r, 0, time_item)
                
                # Kullanıcı
                user_item = QTableWidgetItem(str(log[1]))
                user_item.setFont(QFont(DesignTokens.FONT_NAME, 9, QFont.Weight.Bold))
                self.table.setItem(r, 1, user_item)
                account = account_names.get(str(log[1]))
                user_text = f"{account[3] or account[1]}\n{normalize_role(account[2])}" if account else str(log[1])
                self.table.setCellWidget(r, 1, self._audit_composite_label(user_text))
                
                # Tablo
                tab_item = QTableWidgetItem(str(log[2] or "SİSTEM").upper())
                self.table.setItem(r, 2, tab_item)
                
                # İşlem
                action = str(log[3]).upper()
                act_item = QTableWidgetItem(action)
                act_item.setFont(QFont(DesignTokens.FONT_NAME, 9, QFont.Weight.ExtraBold))
                
                if not getattr(self, "_dark_mode", False):
                    if "LOGIN" in action or "INSERT" in action:
                        act_item.setForeground(qc("success"))
                    elif "DELETE" in action:
                        act_item.setForeground(qc("danger"))
                    elif "UPDATE" in action:
                        act_item.setForeground(qc("warning"))
                    else:
                        act_item.setForeground(qc("accent"))
                
                self.table.setItem(r, 3, act_item)
                self.table.setCellWidget(r, 3, self._audit_composite_label(f"{action}\n{log[2] or '-'}"))
                
                # Detaylar
                det_item = QTableWidgetItem(str(log[4]))
                self.table.setItem(r, 4, det_item)
                severity, station = _audit_record_metadata(log)
                for column, value in ((5, severity), (6, station)):
                    metadata_item = QTableWidgetItem(value)
                    if value == "-":
                        metadata_item.setToolTip("Bu audit kaydinda ilgili metadata bulunmuyor.")
                    self.table.setItem(r, column, metadata_item)
                
                if getattr(self, "_dark_mode", False):
                    for it in (time_item, user_item, tab_item, act_item, det_item):
                        it.setForeground(qc("surface_alt"))

            for column, width in ((0, 122), (1, 112), (2, 160), (3, 124), (5, 60), (6, 94)):
                self.table.setColumnWidth(column, width)
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            self._apply_log_filters()
            self._update_audit_inspector()
            
        except Exception as e:
            logger.error(f"AuditLogPage data load error: {e}")
    
    def _apply_dark_mode_if_needed(self):
        # ThemeManager now handles dark/light transitions globally.
        # Keep page-specific override disabled to avoid mixed "zebra" rendering.
        self._dark_mode = False


