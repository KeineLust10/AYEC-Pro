"""AYEC Pro Admin Console - privileged operation audit trail."""
import json
import csv
import hashlib
import io

from PyQt6.QtCore import QEvent, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QBoxLayout,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import api_client


def _integrity_icon() -> QIcon:
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#4edea3"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(2, 8, 6, 12)
    painter.drawLine(6, 12, 14, 3)
    painter.end()
    return QIcon(pixmap)


_ACTION_LABELS = {
    "admin_company_updated": "Firma g\u00fcncellendi",
    "company_sector_changed": "Sekt\u00f6r de\u011fi\u015ftirildi",
    "admin_password_reset_link": "Kullan\u0131c\u0131 Ge\u00e7ici Parola Atama",
    "admin_password_reset": "Parola s\u0131f\u0131rland\u0131",
    "admin_backup_created": "Otomatik Veritaban\u0131 Yedekleme",
    "admin_backup_sync": "Bulut Yedek Senkronizasyonu (S3 Bucket)",
    "password_reset_link_created": "Parola ba\u011flant\u0131s\u0131 olu\u015fturuldu",
    "password_reset_completed": "Parola yenilendi",
    "admin_license_updated": "Lisans g\u00fcncellendi",
    "admin_notification_sent": "Bildirim g\u00f6nderildi",
    "admin_update_deployed": "OTA Firmware Yama Da\u011f\u0131t\u0131m\u0131",
    "admin_readonly_query": "Salt Okunur SQL Sorgusu \u00c7al\u0131\u015ft\u0131r\u0131ld\u0131",
    "desktop_restore_queued": "Geri y\u00fckleme kuyrukland\u0131",
    "admin_legacy_restore_queued": "Eski yedek geri y\u00fckleme kuyrukland\u0131",
    "control_company_updated": "Firma ayarlar\u0131 g\u00fcncellendi",
    "control_user_updated": "Kullan\u0131c\u0131 g\u00fcncellendi",
    "control_notification_sent": "Y\u00f6netim bildirimi g\u00f6nderildi",
    "control_update_staged": "G\u00fcncelleme yay\u0131na haz\u0131rland\u0131",
}


class _FetchCompanies(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchAudit(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tenant_id = tenant_id

    def run(self):
        try:
            self.done.emit(api_client.audit_logs(self._tenant_id, 500))
        except Exception as exc:
            self.error.emit(str(exc))


class AuditLogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._logs: list[dict] = []
        self._workers: set[QThread] = set()
        self._active_category = "all"
        self._export_count = 0
        self._event_cards = []
        self._event_card_layouts = []
        self._diff_row_layouts = []
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        self.setObjectName("auditLogsPage")
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("auditPageScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("auditContent")
        content.setMinimumWidth(0)
        root = QVBoxLayout(content)
        self._root_layout = root
        root.setContentsMargins(40, 1, 16, 10)
        root.setSpacing(7)
        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self._page_scroll = scroll
        self.setStyleSheet("""
            QWidget#auditLogsPage { background: #0e1321; color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
            QWidget#auditContent { background: #0e1321; color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
            QWidget#auditContent QLabel { color: #dee2f6; background: transparent; }
            QWidget#auditContent QLabel#auditCompliance { color: #4edea3; background: #161b2a; }
            QWidget#auditContent QLabel#auditBadge { color: #adc6ff; background: #303444; }
            QWidget#auditContent QLabel#auditRisk { color: #4edea3; background: #003824; }
            QWidget#auditContent QLabel#auditDiffOld { color: #ffb4ab; background: #34303a; }
            QWidget#auditContent QLabel#auditDiffNew { color: #4edea3; background: #17342c; }
            QWidget#auditContent QLabel#auditHash { color: #adc6ff; background: #252a39; }
            QScrollArea#auditPageScroll { background: #0e1321; }
            QLabel#pageTitle { color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; font-size: 20px; font-weight: 700; }
            QLabel#panelTitle { color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; font-size: 16px; font-weight: 800; }
            QLabel#metricTitle { font: 700 11px 'JetBrains Mono', 'Segoe UI', Arial; letter-spacing: 1px; }
            QLabel#metricValue { color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; font-size: 24px; font-weight: 800; }
            QFrame#metricCard { background: #161b2a; border: 1px solid #252a39; border-radius: 8px; }
            QWidget#auditStreamPanel { background: #161b2a; border: 1px solid #1e293b; border-radius: 8px; }
            QPushButton#auditCategory { background: #090e1c; color: #c2c6d6; border: none; border-radius: 4px; padding: 7px 10px; }
            QPushButton#auditCategory:checked { background: #4d8eff; color: #00285d; font-weight: 700; }
            QPushButton#auditCategory:hover { background: #252a39; }
            QPushButton#auditCategory:checked:hover { background: #4d8eff; }
            QPushButton#auditVerifyButton { background: #161b2a; color: #c2c6d6; border: 1px solid #1e293b; border-radius: 4px; padding: 7px 9px; font: 700 10px 'Plus Jakarta Sans', 'Segoe UI', Arial; }
            QPushButton#auditVerifyButton:hover { background: #252a39; border-color: #4edea3; }
            QFrame#auditStreamCard { background: #090e1c; border: 1px solid #1e293b; border-radius: 4px; }
            QFrame#auditStreamCard[selected="true"] { border-left: 3px solid #adc6ff; background: #252a39; }
            QLabel#auditMeta { color: #8c909f; font: 10px 'Segoe UI', Arial; }
            QLabel#auditAction { color: #dee2f6; font-size: 13px; font-weight: 700; }
            QLabel#auditBadge { background: #303444; color: #adc6ff; padding: 3px 6px; border-radius: 3px; }
            QLabel#auditRisk { background: #003824; color: #4edea3; padding: 3px 6px; border-radius: 3px; }
            QFrame#auditInspector { background: #161b2a; border: 1px solid #1e293b; border-radius: 4px; }
            QFrame#auditStreamCard QLabel { background: transparent; border: none; }
            QLabel#auditCompliance { background: #161b2a; color: #4edea3; border-radius: 4px; padding: 7px 9px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QFrame#auditFilterPanel { background: #161b2a; border: 1px solid #1e293b; border-radius: 4px; }
            QFrame#auditCategoryShelf { background: transparent; border: none; }
            QFrame#auditDetailSection { background: #090e1c; border: 1px solid #252a39; border-radius: 4px; }
            QFrame#auditDiffRow { background: #1a1f2e; border-radius: 3px; }
            QLabel#auditDetailCaption { color: #8c909f; font-size: 10px; font-weight: 700; }
            QLabel#auditDetailValue { color: #dee2f6; font-size: 11px; }
            QLabel#auditDiffOld { color: #ffb4ab; background: #34303a; padding: 4px 6px; }
            QLabel#auditDiffNew { color: #4edea3; background: #17342c; padding: 4px 6px; }
            QLabel#auditHash { color: #adc6ff; background: #252a39; padding: 8px; font-size: 10px; }
        """)

        top = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._audit_header_layout = top
        title = QLabel("Denetim Kay\u0131tlar\u0131 & G\u00fcvenlik \u0130zleme Masas\u0131")
        title.setObjectName("pageTitle")
        title.setFont(QFont("Plus Jakarta Sans", 20, QFont.Weight.Bold))
        title.setWordWrap(True)
        self._audit_title = title
        title.setFixedWidth(360)
        title.setMaximumHeight(64)
        top.addWidget(title)
        for badge_text in ("SHA-256 \u0130mzal\u0131 & De\u011fi\u015ftirilemez", "SOC2 / ISO 27001 Uyumlu", "Audit Engine: Active Watch"):
            badge = QLabel(badge_text)
            badge.setObjectName("auditCompliance")
            badge.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
            badge.setMaximumHeight(38)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            top.addWidget(badge)
        self._verify_integrity_button = QPushButton("B\u00fct\u00fcnl\u00fck Do\u011frula")
        self._verify_integrity_button.setObjectName("auditVerifyButton")
        self._verify_integrity_button.setIcon(_integrity_icon())
        self._verify_integrity_button.setToolTip(
            "Y\u00fcklenen kay\u0131tlardaki mevcut previous_hash ba\u011flant\u0131lar\u0131n\u0131 denetler."
        )
        self._verify_integrity_button.clicked.connect(self._verify_integrity)
        top.addWidget(self._verify_integrity_button)
        root.addLayout(top)

        info = QLabel(
            "Parola, lisans, sekt\u00f6r, yedek, bildirim, g\u00fcncelleme ve uzaktan sorgu "
            "gibi ayr\u0131cal\u0131kl\u0131 i\u015flemler burada kriptografik zaman damgas\u0131yla izlenir."
        )
        info.setObjectName("metricSub")
        info.setWordWrap(True)
        info.setMaximumWidth(700)
        root.addWidget(info)
        root.addSpacing(17)

        metrics = QGridLayout()
        self._metrics_grid = metrics
        metrics.setSpacing(12)
        self._metric_values = {}
        self._metric_cards = []
        for index, (key, caption, accent) in enumerate((
            ("total", "TOPLAM DENETIM KAYDI", "#adc6ff"),
            ("risk", "G\u00dcVENL\u0130K \u0130HLAL\u0130 / R\u0130SK", "#4edea3"),
            ("actors", "Y\u00d6NET\u0130C\u0130 OTURUMLARI", "#4cd7f6"),
            ("exports", "DI\u015eA AKTARIM DENET\u0130M\u0130", "#adc6ff"),
        )):
            card = QFrame()
            card.setObjectName("metricCard")
            card.setFixedHeight(110)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            caption_label = QLabel(caption)
            caption_label.setObjectName("metricTitle")
            caption_label.setWordWrap(True)
            caption_label.setMinimumWidth(0)
            value = QLabel("0")
            value.setObjectName("metricValue")
            value.setStyleSheet(f"color: {accent};")
            note = QLabel("Live audit stream")
            note.setObjectName("metricSub")
            note.setWordWrap(True)
            note.setMinimumWidth(0)
            card.setMinimumWidth(0)
            card_layout.addWidget(caption_label)
            card_layout.addWidget(value)
            card_layout.addWidget(note)
            self._metric_cards.append(card)
            self._metric_values[key] = (value, note)
        self._reflow_metrics()
        root.addLayout(metrics)
        root.addSpacing(8)

        self._company = QComboBox()
        self._company.setObjectName("combo")
        self._company.setMinimumWidth(0)
        self._company.currentIndexChanged.connect(self._load_logs)
        filter_panel = QFrame()
        filter_panel.setObjectName("auditFilterPanel")
        filter_layout = QVBoxLayout(filter_panel)
        filter_layout.setContentsMargins(10, 9, 10, 9)
        filter_layout.setSpacing(8)

        query_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._audit_query_layout = query_row
        self._search = QLineEdit()
        self._search.setObjectName("searchInput")
        self._search.setMinimumWidth(0)
        self._search.setPlaceholderText(
            "Islem adi, yonetici kimligi, IP veya kayit numarasi ara (#AUD-9942)..."
        )
        self._search.textChanged.connect(self._filter_logs)
        query_row.addWidget(self._search, 1)
        query_row.addWidget(self._company)
        self._risk_filter = QComboBox()
        self._risk_filter.setObjectName("combo")
        self._risk_filter.setMinimumWidth(0)
        self._risk_filter.addItem("Risk: T\u00fcm\u00fc", "all")
        self._risk_filter.addItem("D\u00fc\u015f\u00fck", "low")
        self._risk_filter.addItem("Orta", "medium")
        self._risk_filter.addItem("Kritik / Yetkili", "critical")
        self._risk_filter.currentIndexChanged.connect(self._filter_logs)
        query_row.addWidget(self._risk_filter)
        self._export_button = QPushButton("Imzali Rapor Indir (PDF/CSV)")
        self._export_button.setObjectName("secondaryBtn")
        self._export_button.setMinimumWidth(0)
        self._export_button.setToolTip("\u0130mzal\u0131 Rapor \u0130ndir (PDF/CSV)")
        self._export_button.clicked.connect(self._export_csv)
        query_row.addWidget(self._export_button)
        filter_layout.addLayout(query_row)

        category_scroll = QScrollArea()
        category_scroll.setObjectName("auditCategoryShelf")
        category_scroll.setMinimumWidth(0)
        category_scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        category_scroll.setWidgetResizable(True)
        category_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        category_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        category_scroll.setFixedHeight(52)
        self._category_scroll = category_scroll
        category_shelf = QWidget()
        category_shelf.setMinimumWidth(0)
        category_row = QHBoxLayout(category_shelf)
        category_row.setContentsMargins(8, 6, 8, 6)
        category_row.setSizeConstraint(QHBoxLayout.SizeConstraint.SetMinimumSize)
        self._category_buttons = {}
        categories = (
            ("all", "T\u00fcm \u0130\u015flemler"),
            ("identity", "Kimlik && Parola"),
            ("license", "Lisans && Yetki"),
            ("database", "SQL && Veritaban\u0131"),
            ("backup", "Yedekleme && Restore"),
            ("system", "Sistem && Da\u011f\u0131t\u0131m"),
        )
        for key, label in categories:
            button = QPushButton(label)
            button.setObjectName("auditCategory")
            button.setCheckable(True)
            button.setChecked(key == "all")
            button.clicked.connect(lambda checked, target=key: self._set_category(target))
            category_row.addWidget(button)
            self._category_buttons[key] = button
        category_scroll.setWidget(category_shelf)
        filter_layout.addWidget(category_scroll)
        root.addWidget(filter_panel)

        splitter = QSplitter()
        splitter.setMinimumWidth(0)
        splitter.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self._audit_splitter = splitter
        self._table = QTableWidget()
        self._table.setObjectName("dataTable")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Kayit No", "Zaman Damgasi", "Islem / Olay", "Firma", "Risk", "Yonetici", "IP / Hash"
        ])
        self._table.verticalHeader().hide()
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for column, width in ((0, 96), (1, 142), (3, 100), (4, 62), (5, 105), (6, 108)):
            self._table.setColumnWidth(column, width)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.currentCellChanged.connect(self._show_detail)
        self._table.hide()
        stream_panel = QWidget()
        stream_panel.setObjectName("auditStreamPanel")
        stream_panel.setMinimumWidth(0)
        stream_panel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        stream_layout = QVBoxLayout(stream_panel)
        stream_layout.setContentsMargins(12, 12, 12, 12)
        stream_layout.setSpacing(13)
        stream_header = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._stream_header_layout = stream_header
        stream_title = QLabel("Denetim Gunlugu Kayit Akisi")
        stream_title.setObjectName("panelTitle")
        stream_header.addWidget(stream_title)
        stream_header.addStretch()
        self._stream_count = QLabel("Otomatik Yenileme")
        self._stream_count.setObjectName("metricSub")
        stream_header.addWidget(self._stream_count)
        stream_layout.addLayout(stream_header)
        self._stream_scroll = QScrollArea()
        self._stream_scroll.setWidgetResizable(True)
        self._stream_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._stream_body = QWidget()
        self._stream_layout = QVBoxLayout(self._stream_body)
        self._stream_layout.setContentsMargins(0, 0, 4, 0)
        self._stream_layout.setSpacing(7)
        self._stream_layout.addStretch()
        self._stream_scroll.setWidget(self._stream_body)
        stream_layout.addWidget(self._stream_scroll, 1)
        splitter.addWidget(stream_panel)

        detail_panel = QFrame()
        detail_panel.setObjectName("auditInspector")
        detail_panel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        self._detail_summary = QLabel("Denetim olay\u0131 se\u00e7in")
        self._detail_summary.setObjectName("panelTitle")
        self._detail_summary.setWordWrap(True)
        detail_layout.addWidget(self._detail_summary)
        self._detail_context = QLabel("Kayd\u0131n i\u015flemini yapan ki\u015fiyi, firmas\u0131n\u0131 ve kaynak bilgilerini g\u00f6rmek i\u00e7in bir olay se\u00e7in.")
        self._detail_context.setObjectName("metricSub")
        self._detail_context.setWordWrap(True)
        self._detail_context.setTextFormat(Qt.TextFormat.PlainText)
        detail_layout.addWidget(self._detail_context)
        detail_scroll = QScrollArea()
        detail_scroll.setMinimumWidth(0)
        detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail_body = QWidget()
        detail_body.setMinimumWidth(0)
        detail_body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        detail_body_layout = QVBoxLayout(detail_body)
        detail_body_layout.setContentsMargins(0, 0, 0, 0)
        detail_body_layout.setSpacing(8)
        description_card = QFrame()
        description_card.setObjectName("auditDetailSection")
        description_layout = QVBoxLayout(description_card)
        description_layout.setContentsMargins(9, 8, 9, 8)
        description_caption = QLabel("Olay A\u00e7\u0131klamas\u0131")
        description_caption.setObjectName("auditDetailCaption")
        description_caption.setWordWrap(True)
        description_layout.addWidget(description_caption)
        self._detail_description = QLabel("Denetim olay\u0131 se\u00e7in.")
        self._detail_description.setObjectName("auditDetailValue")
        self._detail_description.setWordWrap(True)
        description_layout.addWidget(self._detail_description)
        detail_body_layout.addWidget(description_card)
        diff_title = QLabel("\u0130\u015flem \u00d6ncesi ve Sonras\u0131 Fark\u0131 (DIFF)")
        diff_title.setObjectName("auditDetailCaption")
        diff_title.setWordWrap(True)
        diff_title.setMinimumWidth(0)
        detail_body_layout.addWidget(diff_title)
        self._diff_rows = QVBoxLayout()
        self._diff_rows.setSpacing(4)
        detail_body_layout.addLayout(self._diff_rows)
        security_title = QLabel("G\u00fcvenlik ve istemci bilgileri")
        security_title.setObjectName("auditDetailCaption")
        security_title.setWordWrap(True)
        security_title.setMinimumWidth(0)
        detail_body_layout.addWidget(security_title)
        metadata_card = QFrame()
        metadata_card.setObjectName("auditDetailSection")
        metadata_layout = QGridLayout(metadata_card)
        metadata_layout.setContentsMargins(8, 7, 8, 7)
        metadata_layout.setHorizontalSpacing(8)
        metadata_layout.setVerticalSpacing(6)
        for column, caption in enumerate(("Kaynak IP adresi", "TLS / \u015eifreleme", "Kullan\u0131c\u0131 arac\u0131")):
            label = QLabel(caption)
            label.setObjectName("auditDetailCaption")
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            metadata_layout.addWidget(label, 0 if column < 2 else 2, column if column < 2 else 0)
        self._detail_ip = QLabel("-")
        self._detail_ip.setObjectName("auditDetailValue")
        metadata_layout.addWidget(self._detail_ip, 1, 0)
        self._detail_encryption = QLabel("-")
        self._detail_encryption.setObjectName("auditDetailValue")
        metadata_layout.addWidget(self._detail_encryption, 1, 1)
        self._detail_agent = QLabel("-")
        self._detail_agent.setObjectName("auditDetailValue")
        self._detail_agent.setWordWrap(True)
        metadata_layout.addWidget(self._detail_agent, 3, 0, 1, 2)
        detail_body_layout.addWidget(metadata_card)
        hash_title = QLabel("Kriptografik blok karmas\u0131")
        hash_title.setObjectName("auditDetailCaption")
        detail_body_layout.addWidget(hash_title)
        self._detail_hash = QLabel("-")
        self._detail_hash.setObjectName("auditHash")
        self._detail_hash.setWordWrap(True)
        detail_body_layout.addWidget(self._detail_hash)
        self._detail_previous = QLabel("")
        self._detail_previous.setObjectName("auditDetailCaption")
        self._detail_previous.setWordWrap(True)
        detail_body_layout.addWidget(self._detail_previous)
        detail_body_layout.addStretch(1)
        detail_scroll.setWidget(detail_body)
        detail_layout.addWidget(detail_scroll, 1)
        self._detail = QTextEdit()
        self._detail.setObjectName("codeBox")
        self._detail.setReadOnly(True)
        self._detail.hide()
        splitter.addWidget(detail_panel)
        detail_panel.setMinimumWidth(0)
        splitter.setHandleWidth(16)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([650, 450])
        root.addWidget(splitter, 1)

        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        self._status.setWordWrap(True)
        self._status.setMinimumWidth(0)
        root.addWidget(self._status)

    def _keep(self, worker: QThread):
        self._workers.add(worker)
        worker.finished.connect(lambda: self._workers.discard(worker))
        worker.start()

    def _reflow_metrics(self):
        if not hasattr(self, "_metrics_grid"):
            return
        while self._metrics_grid.count():
            self._metrics_grid.takeAt(0)
        columns = 4 if self.width() >= 960 else 2
        for index, card in enumerate(self._metric_cards):
            self._metrics_grid.addWidget(card, index // columns, index % columns)
        for column in range(4):
            self._metrics_grid.setColumnStretch(column, int(column < columns))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "_audit_splitter"):
            return
        compact = self.width() < 760
        self._root_layout.setContentsMargins(
            12 if compact else 40,
            1,
            12 if compact else 16,
            10,
        )
        self._export_button.setText(
            "Rapor \u0130ndir" if compact else "\u0130mzal\u0131 Rapor \u0130ndir (PDF/CSV)"
        )
        self._audit_header_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
        )
        self._stream_header_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
        )
        for metadata_layout, footer_layout in self._event_card_layouts:
            direction = QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
            metadata_layout.setDirection(direction)
            footer_layout.setDirection(direction)
        for row_layout, field, old_label, new_label in self._diff_row_layouts:
            row_layout.setDirection(QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight)
            field.setMinimumWidth(0 if compact else 72)
            old_label.setMinimumWidth(0)
            new_label.setMinimumWidth(0)
        self._audit_query_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
        )
        self._audit_title.setFixedWidth(max(1, min(360, self.width() - 64)))
        self._audit_splitter.setOrientation(
            Qt.Orientation.Vertical if compact else Qt.Orientation.Horizontal
        )
        self._reflow_metrics()
        stream_panel = self._audit_splitter.widget(0)
        detail_panel = self._audit_splitter.widget(1)
        if compact:
            for panel in (stream_panel, detail_panel):
                panel.setMinimumSize(0, 0)
                panel.setMaximumSize(16777215, 16777215)
            self._audit_splitter.setSizes([380, 460])
        else:
            if self.window().width() >= 1400:
                stream_panel.setFixedHeight(655)
                detail_panel.setFixedSize(457, 662)
                self._audit_splitter.setSizes([
                    max(0, self._audit_splitter.width() - 16 - 457),
                    457,
                ])
            else:
                for panel in (stream_panel, detail_panel):
                    panel.setMinimumSize(0, 0)
                    panel.setMaximumSize(16777215, 16777215)
                available_width = max(0, self._audit_splitter.width() - 16)
                detail_width = round(available_width * 5 / 12)
                self._audit_splitter.setSizes([available_width - detail_width, detail_width])

    def _load_companies(self):
        worker = _FetchCompanies()
        worker.done.connect(self._populate_companies)
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _populate_companies(self, companies: list):
        self._company.blockSignals(True)
        self._company.clear()
        self._company.addItem("T\u00fcm firmalar", "")
        for company in companies:
            self._company.addItem(company.get("company_name", "?"), company.get("id", ""))
        self._company.blockSignals(False)
        self._load_logs()

    def _load_logs(self):
        self._status.setText("Denetim kay\u0131tlar\u0131 y\u00fckleniyor...")
        worker = _FetchAudit(str(self._company.currentData() or ""))
        worker.done.connect(self._populate_logs)
        worker.error.connect(self._load_error)
        self._keep(worker)

    def _load_error(self, error: str):
        self._status.setText(
            f"Denetim kay\u0131tlar\u0131 al\u0131namad\u0131: {error}. "
            "Sunucu taraf\u0131n\u0131n bu konsol s\u00fcr\u00fcm\u00fcyle g\u00fcncel oldu\u011funu do\u011frulay\u0131n."
        )

    def _populate_logs(self, logs: list):
        self._logs = logs
        self._table.setRowCount(0)
        self._clear_event_cards()
        actors = set()
        risks = 0
        category_counts = {key: 0 for key in self._category_buttons}
        for entry in logs:
            row = self._table.rowCount()
            self._table.insertRow(row)
            action = str(entry.get("action") or "")
            risk = self._risk_for(entry)
            risks += risk == "critical"
            actor = entry.get("actor_username") or entry.get("actor_user_id") or "System"
            if actor != "System":
                actors.add(str(actor))
            category_counts["all"] += 1
            category_counts[self._category_for(action)] += 1
            detail = entry.get("detail") if isinstance(entry.get("detail"), dict) else {}
            values = [
                entry.get("id", ""),
                entry.get("created_at", ""),
                _ACTION_LABELS.get(action, action),
                entry.get("company_name", "Sistem"),
                {"low": "Dusuk", "medium": "Orta", "critical": "Kritik"}[risk],
                actor,
                " ".join(str(value) for value in (
                    entry.get("ip_address") or detail.get("ip_address") or detail.get("ip") or "-",
                    entry.get("record_hash") or entry.get("signature") or "",
                ) if value),
            ]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
            self._table.item(row, 6).setToolTip(
                f"IP: {entry.get('ip_address') or detail.get('ip_address') or detail.get('ip') or '-'}\n"
                f"Hash: {entry.get('record_hash') or entry.get('signature') or '-'}"
            )
        self._render_event_cards()
        self._metric_values["total"][0].setText(str(len(logs)))
        self._metric_values["total"][1].setText("Olay (30 G\u00fcn)")
        self._metric_values["risk"][0].setText(f"{risks} Risk")
        safe_percent = round((len(logs) - risks) * 100 / len(logs)) if logs else 100
        self._metric_values["risk"][1].setText(f"{safe_percent}% G\u00fcvenli")
        self._metric_values["actors"][0].setText(str(len(actors)))
        self._metric_values["actors"][1].setText("Yetkili")
        self._metric_values["exports"][0].setText(f"{self._export_count} Rapor")
        self._metric_values["exports"][1].setText("CSV d\u0131\u015fa aktar\u0131m")
        for key, button in self._category_buttons.items():
            base_label = button.property("baseLabel")
            if not base_label:
                base_label = button.text()
                button.setProperty("baseLabel", base_label)
            button.setText(f"{base_label}  {category_counts[key]}")
            button.setMinimumWidth(button.sizeHint().width())
        self._category_scroll.horizontalScrollBar().setValue(0)
        self._status.setText(f"{len(logs)} denetim kayd\u0131 g\u00f6steriliyor.")
        self._filter_logs(self._search.text())
        if logs:
            self._table.selectRow(0)
            self._show_detail(0, 0, -1, -1)
        else:
            self._detail.clear()

    def _filter_logs(self, *_args):
        needle = self._search.text().strip().casefold()
        risk_filter = str(self._risk_filter.currentData() or "all")
        category_filter = self._active_category
        visible_rows = []
        for row in range(self._table.rowCount()):
            values = [
                self._table.item(row, column).text()
                for column in range(self._table.columnCount())
                if self._table.item(row, column) is not None
            ]
            entry = self._logs[row]
            risk = self._risk_for(entry)
            action = str(entry.get("action") or "")
            match = (not needle or needle in " ".join(values).casefold())
            match = match and (risk_filter == "all" or risk_filter == risk)
            match = match and (category_filter == "all" or category_filter == self._category_for(action))
            self._table.setRowHidden(row, not match)
            if match:
                visible_rows.append(row)
        self._status.setText(f"{len(visible_rows)} / {len(self._logs)} denetim olay\u0131 g\u00f6steriliyor")
        self._stream_count.setText(f"{len(visible_rows)} / {len(self._logs)} Olay")
        for row, card in enumerate(self._event_cards):
            card.setVisible(not self._table.isRowHidden(row))

    def _clear_event_cards(self):
        while self._stream_layout.count() > 1:
            item = self._stream_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._event_cards = []
        self._event_card_layouts = []

    def _render_event_cards(self):
        for row, entry in enumerate(self._logs):
            detail = entry.get("detail") if isinstance(entry.get("detail"), dict) else {}
            action = str(entry.get("action") or "")
            actor = entry.get("actor_username") or entry.get("actor_user_id") or "System"
            company = entry.get("company_name") or "System (Master)"
            risk = self._risk_for(entry)
            card = QFrame()
            card.setObjectName("auditStreamCard")
            card.setProperty("rowIndex", row)
            card.setProperty("selected", "false")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 10, 10, 10)
            card_layout.setSpacing(8)
            meta = QBoxLayout(QBoxLayout.Direction.LeftToRight)
            record = QLabel(f"#{entry.get('id', '-')}")
            record.setObjectName("auditBadge")
            timestamp = QLabel(str(entry.get("created_at") or "-"))
            timestamp.setObjectName("auditMeta")
            tenant = QLabel(str(company))
            tenant.setObjectName("auditBadge")
            risk_label = QLabel({"low": "D\u00fc\u015f\u00fck Risk", "medium": "Orta Risk", "critical": "Kritik Risk"}[risk])
            risk_label.setObjectName("auditRisk")
            for label in (record, timestamp, tenant, risk_label):
                label.setMinimumWidth(0)
                label.setWordWrap(True)
            meta.addWidget(record)
            meta.addWidget(timestamp, 1)
            meta.addWidget(tenant)
            meta.addWidget(risk_label)
            card_layout.addLayout(meta)
            action_label = QLabel(_ACTION_LABELS.get(action, action or "System event"))
            action_label.setObjectName("auditAction")
            action_label.setWordWrap(True)
            action_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
            action_row.addWidget(action_label, 1)
            actor_label = QLabel(str(actor))
            actor_label.setObjectName("auditMeta")
            actor_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            actor_label.setMinimumWidth(0)
            actor_label.setWordWrap(False)
            action_row.addWidget(actor_label)
            card_layout.addLayout(action_row)
            footer = QBoxLayout(QBoxLayout.Direction.LeftToRight)
            source = entry.get("ip_address") or detail.get("ip_address") or detail.get("ip") or "-"
            footer_label = QLabel(f"IP: {source}")
            footer_label.setObjectName("auditMeta")
            footer_label.setMinimumWidth(0)
            footer_label.setWordWrap(True)
            signature = entry.get("record_hash") or entry.get("signature") or detail.get("record_hash") or ""
            hash_text = f"SHA: {str(signature)[:8]}...{str(signature)[-4:]}" if signature else ""
            hash_label = QLabel(hash_text)
            hash_label.setObjectName("auditMeta")
            hash_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            hash_label.setMinimumWidth(0)
            hash_label.setWordWrap(False)
            footer.addWidget(footer_label, 1)
            footer.addWidget(hash_label)
            card_layout.addLayout(footer)
            card.installEventFilter(self)
            for child in card.findChildren(QWidget):
                child.installEventFilter(self)
            self._stream_layout.insertWidget(self._stream_layout.count() - 1, card)
            self._event_cards.append(card)
            self._event_card_layouts.append((meta, footer))

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            card = watched if watched in self._event_cards else watched.parentWidget()
            while card is not None and card not in self._event_cards:
                card = card.parentWidget()
            if card in self._event_cards:
                row = int(card.property("rowIndex"))
                self._table.setCurrentCell(row, 0)
                self._show_detail(row, 0, -1, -1)
                return True
        return super().eventFilter(watched, event)

    def _set_category(self, category: str):
        self._active_category = category
        for key, button in self._category_buttons.items():
            button.setChecked(key == category)
        self._filter_logs()

    @staticmethod
    def _category_for(action: str) -> str:
        name = str(action or "").casefold()
        if any(term in name for term in ("password", "login", "auth", "user")):
            return "identity"
        if any(term in name for term in ("license", "sector", "company")):
            return "license"
        if any(term in name for term in ("sql", "query", "database")):
            return "database"
        if any(term in name for term in ("backup", "restore")):
            return "backup"
        return "system"

    @staticmethod
    def _risk_for(entry: dict) -> str:
        detail = entry.get("detail") or {}
        details = entry.get("details") or {}
        explicit = str(
            entry.get("risk_level")
            or entry.get("risk")
            or entry.get("severity")
            or (detail.get("risk_level") if isinstance(detail, dict) else "")
            or (details.get("severity") if isinstance(details, dict) else "")
            or ""
        ).casefold()
        if explicit in {"critical", "high", "severe", "kritik", "yuksek", "ciddi"}:
            return "critical"
        if explicit in {"medium", "warning", "orta", "uyari"}:
            return "medium"
        action = str(entry.get("action") or "").casefold()
        if any(term in action for term in (
            "license_cancelled",
            "permission_revoked",
            "account_deleted",
            "tenant_deleted",
        )):
            return "critical"
        return "low"

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Audit CSV", "audit-report.csv", "CSV (*.csv)")
        if not path:
            return
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(tuple(self._table.horizontalHeaderItem(column).text() for column in range(self._table.columnCount())))
        for row in range(self._table.rowCount()):
            if self._table.isRowHidden(row):
                continue
            writer.writerow(tuple(self._table.item(row, column).text() if self._table.item(row, column) else "" for column in range(self._table.columnCount())))
        digest = hashlib.sha256(buffer.getvalue().encode("utf-8")).hexdigest()
        writer.writerow(("SHA-256", digest))
        with open(path, "w", newline="", encoding="utf-8-sig") as output:
            output.write(buffer.getvalue())
        self._export_count += 1
        self._metric_values["exports"][0].setText(f"{self._export_count} Rapor")

    def _verify_integrity(self):
        links = []
        for current, older in zip(self._logs, self._logs[1:]):
            current_detail = current.get("detail") if isinstance(current.get("detail"), dict) else {}
            older_detail = older.get("detail") if isinstance(older.get("detail"), dict) else {}
            previous = current.get("previous_hash") or current_detail.get("previous_hash")
            older_hash = older.get("record_hash") or older.get("signature") or older_detail.get("record_hash")
            if previous and older_hash:
                links.append(str(previous).casefold() == str(older_hash).casefold())
        checked = len(links)
        if not checked:
            self._status.setText("Do\u011frulanabilir hash ba\u011flant\u0131s\u0131 bulunamad\u0131.")
            return
        mismatches = sum(not matches for matches in links)
        if mismatches:
            self._status.setText(
                f"Hash zincirinde {mismatches} tutars\u0131z ba\u011flant\u0131 bulundu ({checked} kontrol edildi)."
            )
        else:
            self._status.setText(
                f"Hash zincirindeki {checked} ba\u011flant\u0131 do\u011fruland\u0131."
            )

    def _show_detail(self, row: int, _column: int, _old_row: int, _old_column: int):
        if row < 0 or row >= len(self._logs):
            return
        for index, card in enumerate(self._event_cards):
            card.setProperty("selected", "true" if index == row else "false")
            card.style().unpolish(card)
            card.style().polish(card)
            card.update()
        entry = self._logs[row]
        detail_data = entry.get("detail") if isinstance(entry.get("detail"), dict) else {}
        self._detail_summary.setText(
            f"{entry.get('id') or '-'}  |  {_ACTION_LABELS.get(str(entry.get('action') or ''), entry.get('action') or '-')}"
        )
        actor = entry.get("actor_username") or entry.get("actor_user_id") or "System"
        tenant = entry.get("company_name") or "System"
        source = entry.get("ip_address") or detail_data.get("ip_address") or detail_data.get("ip") or "-"
        description = detail_data.get("description") or detail_data.get("reason") or "Bu olay i\u00e7in a\u00e7\u0131klama eklenmemi\u015f."
        self._detail_context.setText(f"{actor}  |  {tenant}  |  {entry.get('created_at') or '-'}  |  {source}")
        self._detail_description.setText(str(description))
        before = detail_data.get("before") if isinstance(detail_data.get("before"), dict) else {}
        after = detail_data.get("after") if isinstance(detail_data.get("after"), dict) else {}
        changes = detail_data.get("changes") if isinstance(detail_data.get("changes"), dict) else {}
        while self._diff_rows.count():
            item = self._diff_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._diff_row_layouts = []
        diff_text = []
        keys = list(dict.fromkeys((*before.keys(), *after.keys(), *changes.keys())))
        for key in keys:
            change = changes.get(key) if isinstance(changes.get(key), dict) else {}
            old_value = change.get("before", before.get(key))
            new_value = change.get("after", after.get(key))
            if old_value == new_value:
                continue
            old_text = json.dumps(old_value, ensure_ascii=True)
            new_text = json.dumps(new_value, ensure_ascii=True)
            row = QFrame()
            row.setObjectName("auditDiffRow")
            row.setMinimumWidth(0)
            row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            compact = self.width() < 760
            row_layout = QBoxLayout(
                QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight,
                row,
            )
            row_layout.setContentsMargins(6, 5, 6, 5)
            field = QLabel(str(key))
            field.setObjectName("auditDetailCaption")
            field.setMinimumWidth(0 if compact else 72)
            field.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            old_label = QLabel(old_text)
            old_label.setObjectName("auditDiffOld")
            old_label.setWordWrap(True)
            old_label.setMinimumWidth(0)
            old_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            arrow = QLabel("\u2192")
            arrow.setObjectName("auditDetailCaption")
            new_label = QLabel(new_text)
            new_label.setObjectName("auditDiffNew")
            new_label.setWordWrap(True)
            new_label.setMinimumWidth(0)
            new_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            row_layout.addWidget(field)
            row_layout.addWidget(old_label, 1)
            row_layout.addWidget(arrow)
            row_layout.addWidget(new_label, 1)
            self._diff_row_layouts.append((row_layout, field, old_label, new_label))
            self._diff_rows.addWidget(row)
            diff_text.append(f"{key}: {old_text} -> {new_text}")
        if not diff_text:
            empty_diff = QLabel("Bu olay i\u00e7in alan de\u011fi\u015fikli\u011fi kayd\u0131 bulunmuyor.")
            empty_diff.setObjectName("metricSub")
            self._diff_rows.addWidget(empty_diff)
        user_agent = entry.get("user_agent") or detail_data.get("user_agent") or "-"
        signature = entry.get("record_hash") or entry.get("signature") or detail_data.get("record_hash") or detail_data.get("sha256") or "-"
        previous = entry.get("previous_hash") or detail_data.get("previous_hash") or "-"
        self._detail_ip.setText(str(source))
        self._detail_encryption.setText(str(detail_data.get("encryption") or entry.get("encryption") or "-"))
        self._detail_agent.setText(str(user_agent))
        self._detail_hash.setText(str(signature))
        self._detail_previous.setText(f"Onceki blok: {previous}  |  Kayit: {entry.get('id') or '-'}")
        detail_lines = [str(description), *diff_text, str(source), str(user_agent), str(signature), str(previous), str(entry.get("id") or "-")]
        self._detail.setPlainText("\n".join(detail_lines))
