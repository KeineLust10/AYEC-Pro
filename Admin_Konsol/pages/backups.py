"""AYEC Pro Admin Console - backup catalog and remote restore operations."""
from pathlib import Path
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)

import api_client
from toast import show_toast


class _BackupMetricIcon(QLabel):
    def __init__(self, kind: str, color: str):
        super().__init__()
        self._kind = kind
        self._color = QColor(color)
        self.setObjectName("backupMetricIcon")
        self.setFixedSize(34, 34)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#252a39"))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 4, 4)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self._color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        if self._kind == "archive":
            painter.drawRoundedRect(9, 8, 16, 18, 1, 1)
            painter.drawLine(13, 13, 21, 13)
            painter.drawLine(13, 17, 21, 17)
            painter.drawLine(13, 21, 19, 21)
        elif self._kind == "cloud":
            path = QPainterPath()
            path.moveTo(9, 23)
            path.cubicTo(6, 23, 6, 17, 10, 16)
            path.cubicTo(11, 10, 19, 9, 22, 14)
            path.cubicTo(28, 14, 28, 23, 22, 23)
            path.closeSubpath()
            painter.drawPath(path)
        elif self._kind == "clock":
            painter.drawEllipse(8, 8, 18, 18)
            painter.drawLine(17, 12, 17, 17)
            painter.drawLine(17, 17, 21, 19)
        else:
            path = QPainterPath()
            path.moveTo(19, 6)
            path.lineTo(11, 18)
            path.lineTo(16, 18)
            path.lineTo(14, 28)
            path.lineTo(23, 15)
            path.lineTo(18, 15)
            path.closeSubpath()
            painter.drawPath(path)
        painter.end()


class _FetchCompanies(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchBackups(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tenant_id = tenant_id

    def run(self):
        try:
            self.done.emit(api_client.backups(self._tenant_id))
        except Exception as exc:
            self.error.emit(str(exc))


class _DownloadBackup(QThread):
    done = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, item: dict, target: str):
        super().__init__()
        self._tenant_id = tenant_id
        self._item = item
        self._target = target

    def run(self):
        try:
            payload = api_client.download_backup(
                self._tenant_id,
                int(self._item.get("index", 0)),
                int(self._item.get("backup_id", 0)),
            )
            Path(self._target).write_bytes(payload)
            self.done.emit(self._target)
        except Exception as exc:
            self.error.emit(str(exc))


class _RestoreBackup(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, item: dict):
        super().__init__()
        self._tenant_id = tenant_id
        self._item = item

    def run(self):
        try:
            self.done.emit(api_client.restore_backup(
                self._tenant_id,
                int(self._item.get("index", 0)),
                int(self._item.get("backup_id", 0)),
            ))
        except Exception as exc:
            self.error.emit(str(exc))


def _size_text(size_bytes: int) -> str:
    value = float(size_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return "0 B"


class BackupsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._items: list[dict] = []
        self._workers: set[QThread] = set()
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        self.setObjectName("backupsPage")
        self.setStyleSheet("""
            QWidget#backupsPage { background: #0e1321; color: #dee2f6; }
            QWidget#backupsPage QLabel { background: transparent; }
            QWidget#backupContent { background: #0e1321; }
            QScrollArea#backupScroll, QScrollArea#backupScroll QWidget#qt_scrollarea_viewport { background: #0e1321; }
            QFrame#backupContext, QFrame#backupPanel { background: #161b2a; border: 1px solid #252a39; border-radius: 6px; }
            QFrame#backupPolicyRow { background: #1a1f2e; border: none; border-radius: 4px; }
            QFrame#backupMetric { background: #161b2a; border: 1px solid #252a39; border-bottom: 3px solid #4d8eff; border-radius: 6px; }
            QLabel#backupTitle { color: #dee2f6; font-size: 23px; font-weight: 700; }
            QLabel#backupSubtitle, QLabel#backupMuted { color: #8c909f; }
            QLabel#backupFilterLabel { color: #8c909f; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#statusLabel { color: #c2c6d6; }
            QLabel#backupMetricCaption { color: #8c909f; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#backupMetricValue { color: #adc6ff; font-size: 28px; font-weight: 700; }
            QLabel#backupMetricIcon { color: #adc6ff; background: #252a39; border-radius: 4px; font: 700 16px "Segoe UI Symbol", "Segoe UI", Arial; }
            QLabel#backupMetricFootnote { color: #8c909f; font: 10px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#backupTelemetryValue { color: #4edea3; font-size: 14px; font-weight: 700; }
            QLabel#backupSectionTitle { color: #dee2f6; font-size: 15px; font-weight: 700; }
            QLabel#backupCode { color: #4cd7f6; font-family: 'Segoe UI', Arial; font-size: 10px; }
            QCheckBox#restoreAcknowledgement { color: #c2c6d6; }
            QCheckBox#restoreAcknowledgement::indicator { width: 16px; height: 16px; }
            QComboBox#combo, QLineEdit#searchInput { background: #090e1c; color: #dee2f6; border: 1px solid #424754; border-radius: 4px; padding: 8px 10px; }
            QPushButton#primaryBtn { background: #4d8eff; color: #00285d; border: none; border-radius: 4px; padding: 9px 12px; font-weight: 700; }
            QPushButton#primaryBtn:disabled { background: #252a39; color: #8c909f; }
            QPushButton#secondaryBtn { background: #252a39; color: #dee2f6; border: 1px solid #424754; border-radius: 4px; padding: 8px 11px; }
            QPushButton#secondaryBtn:disabled { background: #161b2a; color: #8c909f; }
            QPushButton#dangerBtn { background: #93000a; color: #ffdad6; border: 1px solid #ffb4ab; border-radius: 4px; padding: 8px 11px; font-weight: 700; }
            QTableWidget#backupTable { background: #0e1321; alternate-background-color: #161b2a; border: 1px solid #252a39; gridline-color: #252a39; color: #dee2f6; }
            QTableWidget#backupTable::item { padding: 8px; }
            QTableWidget#backupTable QHeaderView::section { background: #090e1c; color: #adc6ff; border: none; padding: 5px 8px; font-size: 10px; font-weight: 700; }
            QPushButton#backupSelect { background: #252a39; color: #dee2f6; border: 1px solid #424754; border-radius: 4px; padding: 6px 10px; }
            QPushButton#backupSelect:checked { background: #4d8eff; color: #00285d; }
        """)

        outer = QVBoxLayout(self)
        self._outer_layout = outer
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("backupScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("backupContent")
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Maximum)
        root = QVBoxLayout(content)
        self._content_layout = root
        root.setContentsMargins(44, 15, 20, 20)
        root.setSpacing(14)

        context = QGridLayout()
        self._context_layout = context
        core = QLabel("DISASTER RECOVERY CORE  \u2022  SHA-256 CHECKSUM")
        core.setObjectName("backupCode")
        self._context_core = core
        context.addWidget(core, 0, 0)
        self._storage_label = QLabel("DEPOLAMA: API DURUMU")
        self._storage_label.setObjectName("backupMuted")
        context.addWidget(self._storage_label, 0, 1)
        self._last_backup_label = QLabel("SON YEDEK: -")
        self._last_backup_label.setObjectName("backupMuted")
        context.addWidget(self._last_backup_label, 1, 0, 1, 3)
        root.addLayout(context)

        title_row = QGridLayout()
        self._header_layout = title_row
        title_box = QVBoxLayout()
        title = QLabel("Yedekleme & Kurtarma (Disaster Recovery)")
        title.setObjectName("backupTitle")
        title.setWordWrap(True)
        title_box.addWidget(title)
        subtitle = QLabel(
            "Masa\u00fcst\u00fc istemcilerinden gelen veritaban\u0131 anl\u0131k g\u00f6r\u00fcnt\u00fclerini "
            "izleyin, indirin, b\u00fct\u00fcnl\u00fck do\u011frulay\u0131n ve se\u00e7ilen s\u00fcr\u00fcm\u00fc "
            "istemciye geri y\u00fckleme komutu olarak g\u00f6nderin."
        )
        subtitle.setObjectName("backupSubtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(subtitle)
        self._title_box = title_box
        refresh = QPushButton("Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._load_backups)
        self._header_actions = QHBoxLayout()
        self._header_actions.addWidget(refresh)
        self._snapshot_button = QPushButton("Anl\u0131k Genel Yedek Ba\u015flat")
        self._snapshot_button.setObjectName("primaryBtn")
        self._snapshot_button.setEnabled(False)
        self._snapshot_button.setToolTip("Merkezi yedek olu\u015fturma bu Admin API \u00fczerinden sunulmuyor.")
        self._snapshot_button.clicked.connect(self._snapshot_unavailable)
        self._header_actions.addWidget(self._snapshot_button)
        root.addLayout(title_row)

        self._metric_count = QLabel("0")
        self._metric_size = QLabel("0 / 0")
        self._metric_rpo = QLabel("-")
        self._metric_rto = QLabel("-")
        metric_values = (
            ("TOPLAM YEDEK DOSYASI", self._metric_count, "Aktif & Tarihsel Depo", "archive", "#adc6ff"),
            ("BULUT SENKRON\u0130ZASYON DURUMU", self._metric_size, "SHA-256 metadatas\u0131 bulunan dosya", "cloud", "#4edea3"),
            ("KURTARMA NOKTASI HEDEF\u0130 (RPO)", self._metric_rpo, "API verisi sunulmuyor", "clock", "#4cd7f6"),
            ("ORTALAMA GER\u0130 Y\u00dcKLEME (RTO)", self._metric_rto, "Restore telemetrisi yok", "bolt", "#adc6ff"),
        )
        self._metric_grid = QGridLayout()
        self._metric_grid.setContentsMargins(0, 0, 0, 0)
        self._metric_grid.setSpacing(10)
        self._metric_cards = []
        for index, (caption_text, value, footnote, icon_text, icon_color) in enumerate(metric_values):
            card = QFrame()
            card.setObjectName("backupMetric")
            card.setMinimumHeight(130)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 8, 14, 10)
            card_layout.setSpacing(3)
            heading_layout = QHBoxLayout()
            heading_layout.setContentsMargins(0, 0, 0, 0)
            heading_layout.setSpacing(8)
            caption = QLabel(caption_text)
            caption.setObjectName("backupMetricCaption")
            icon = _BackupMetricIcon(icon_text, icon_color)
            heading_layout.addWidget(caption, 1)
            heading_layout.addWidget(icon)
            value.setObjectName("backupMetricValue")
            value.setStyleSheet(f"color: {icon_color};")
            note = QLabel(footnote)
            note.setObjectName("backupMetricFootnote")
            card_layout.addLayout(heading_layout)
            card_layout.addWidget(value)
            card_layout.addWidget(note)
            self._metric_cards.append(card)
            self._metric_grid.addWidget(card, 0, index)
        root.addLayout(self._metric_grid)

        wal_panel = QFrame()
        wal_panel.setObjectName("backupContext")
        self._wal_panel = wal_panel
        wal_panel.setMinimumHeight(76)
        wal_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        wal_layout = QGridLayout(wal_panel)
        wal_layout.setContentsMargins(14, 10, 14, 10)
        wal_layout.setHorizontalSpacing(14)
        wal_layout.setVerticalSpacing(4)
        wal_icon = QLabel("WAL")
        wal_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wal_icon.setFixedSize(44, 44)
        wal_icon.setStyleSheet("color: #4cd7f6; background: #102a3d; border-radius: 7px; font: 700 12px 'Segoe UI', Arial;")
        wal_layout.addWidget(wal_icon, 0, 0, 2, 1)
        wal_copy = QWidget(wal_panel)
        wal_copy.setStyleSheet("background: transparent;")
        wal_copy_layout = QVBoxLayout(wal_copy)
        wal_copy_layout.setContentsMargins(0, 0, 0, 0)
        wal_copy_layout.setSpacing(3)
        wal_status = QLabel("SQLite WAL (Write-Ahead Log) Canl\u0131 Te\u015fhis Ak\u0131\u015f\u0131")
        wal_status.setObjectName("backupSectionTitle")
        wal_copy_layout.addWidget(wal_status)
        self._wal_summary = QLabel("Checksum metadatas\u0131 y\u00fcklenmi\u015f yedek listesine g\u00f6re g\u00f6sterilir.")
        self._wal_summary.setObjectName("backupMuted")
        self._wal_summary.setWordWrap(True)
        wal_copy_layout.addWidget(self._wal_summary)
        wal_layout.addWidget(wal_copy, 0, 1, 2, 1)
        wal_delta_label = QLabel("G\u00dcNL\u00dcK DELTA AKTARIMI")
        wal_delta_label.setObjectName("backupCode")
        wal_delta_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        wal_delta_value = QLabel("API VER\u0130S\u0130 YOK")
        wal_delta_value.setObjectName("backupTelemetryValue")
        self._wal_coverage = wal_delta_value
        wal_delta_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        wal_layout.addWidget(wal_delta_label, 0, 2)
        wal_layout.addWidget(wal_delta_value, 1, 2)
        root.addWidget(wal_panel)

        filter_panel = QFrame()
        filter_panel.setObjectName("backupPanel")
        filter_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        filter_layout = QGridLayout(filter_panel)
        self._filter_layout = filter_layout
        self._filter_panel = filter_panel
        self._company_filter_label = QLabel("FIRMA SECIN")
        self._company_filter_label.setObjectName("backupFilterLabel")
        self._date_filter_label = QLabel("TARIH ARALIGI")
        self._date_filter_label.setObjectName("backupFilterLabel")
        self._search_filter_label = QLabel("HIZLI FILTRE")
        self._search_filter_label.setObjectName("backupFilterLabel")
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(8)
        self._company_combo = QComboBox()
        self._company_combo.setObjectName("combo")
        self._company_combo.setMinimumWidth(0)
        self._company_combo.currentIndexChanged.connect(self._load_backups)
        self._filter_widgets = []
        self._date_filter = QComboBox()
        self._date_filter.setObjectName("combo")
        self._date_filter.setMinimumWidth(0)
        self._date_filter.addItem("Son 7 G\u00fcn", 7)
        self._date_filter.addItem("Son 30 G\u00fcn", 30)
        self._date_filter.addItem("T\u00fcm Tarihler", 0)
        self._date_filter.currentIndexChanged.connect(self._on_backup_filter_changed)
        self._filter_widgets.append(self._company_combo)
        self._filter_widgets.append(self._date_filter)
        self._search = QLineEdit()
        self._search.setObjectName("searchInput")
        self._search.setMinimumWidth(0)
        self._search.setPlaceholderText("Yedek ad\u0131, hash veya cihaz ara...")
        self._search.textChanged.connect(self._filter_backups)
        self._filter_widgets.append(self._search)
        self._upload_button = QPushButton("Yedek Dosyas\u0131 Y\u00fckle (.db / .enc)")
        self._upload_button.setObjectName("secondaryBtn")
        self._upload_button.setEnabled(False)
        self._upload_button.setToolTip("Yedek i\u00e7eri aktarma Admin API taraf\u0131nda desteklenmiyor.")
        self._upload_button.clicked.connect(self._upload_unavailable)
        self._filter_widgets.append(self._upload_button)
        self._layout_responsive_controls()
        root.addWidget(filter_panel)

        table_panel = QFrame()
        table_panel.setObjectName("backupPanel")
        table_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_heading = QGridLayout()
        self._table_heading_layout = table_heading
        table_heading.setContentsMargins(14, 10, 14, 8)
        table_title = QLabel("Mevcut Veritaban\u0131 Anl\u0131k G\u00f6r\u00fcnt\u00fcleri")
        table_title.setObjectName("backupSectionTitle")
        self._table_heading_title = table_title
        self._table_count = QLabel("0 G\u00f6steriliyor")
        self._table_count.setObjectName("backupCode")
        self._table_heading_count = self._table_count
        self._table_integrity = QLabel("SHA-256 METADATASI: 0 / 0")
        self._table_integrity.setObjectName("backupMuted")
        self._table_heading_integrity = self._table_integrity
        self._layout_responsive_controls()
        table_layout.addLayout(table_heading)

        self._table = QTableWidget(0, 7)
        self._table.setObjectName("backupTable")
        self._table.setHorizontalHeaderLabels([
            "DOSYA ADI", "KAYNAK / T\u0130P", "TAR\u0130H & SAAT", "BOYUT",
            "SHA-256 DO\u011eRULAMA", "\u0130STEMC\u0130 / PROGRAM", "\u0130\u015eLEM",
        ])
        header = self._table.horizontalHeader()
        header.setFixedHeight(32)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 320)
        self._table.setColumnWidth(1, 150)
        self._table.setColumnWidth(2, 180)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 170)
        self._table.setColumnWidth(5, 180)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setWordWrap(True)
        self._table.setMinimumHeight(374)
        self._table.setMaximumHeight(390)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._table.verticalHeader().setDefaultSectionSize(66)
        self._table.itemSelectionChanged.connect(self._update_restore_selection)
        self._table.doubleClicked.connect(lambda _index: self._download_selected())
        table_layout.addWidget(self._table)
        self._table_footer = QLabel("Checksum verisi yaln\u0131zca API taraf\u0131ndan sa\u011flanan kay\u0131tlarda g\u00f6sterilir.")
        self._table_footer.setObjectName("backupMuted")
        table_layout.addWidget(self._table_footer)
        root.addWidget(table_panel)

        lower = QWidget()
        lower.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._lower_layout = QGridLayout(lower)
        self._lower_layout.setContentsMargins(0, 0, 0, 0)
        self._lower_layout.setSpacing(12)
        restore_panel = QFrame()
        restore_panel.setObjectName("backupPanel")
        restore_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        restore_layout = QVBoxLayout(restore_panel)
        restore_layout.setContentsMargins(14, 12, 14, 12)
        restore_title = QLabel("Geri Y\u00fckleme (Restore) G\u00fcvenlik Kilidi")
        restore_title.setObjectName("backupSectionTitle")
        restore_layout.addWidget(restore_title)
        warning = QLabel(
            "Dikkat: se\u00e7ili firman\u0131n masa\u00fcst\u00fc veritaban\u0131 se\u00e7ilen anl\u0131k "
            "g\u00f6r\u00fcnt\u00fcyle de\u011fi\u015ftirilir. \u0130stemci komutu uygulamadan \u00f6nce mevcut veriyi yedekler."
        )
        warning.setWordWrap(True)
        warning.setObjectName("backupMuted")
        restore_layout.addWidget(warning)
        selection_card = QFrame()
        selection_card.setObjectName("backupPolicyRow")
        selection_layout = QVBoxLayout(selection_card)
        selection_layout.setContentsMargins(10, 8, 10, 8)
        self._restore_target = QLabel("HEDEF \u0130STEMC\u0130 TERM\u0130NAL\u0130: -")
        self._restore_target.setObjectName("backupCode")
        selection_layout.addWidget(self._restore_target)
        self._restore_snapshot = QLabel("Uygulanacak anl\u0131k g\u00f6r\u00fcnt\u00fc: -")
        self._restore_snapshot.setObjectName("backupCode")
        self._restore_snapshot.setWordWrap(True)
        selection_layout.addWidget(self._restore_snapshot)
        restore_layout.addWidget(selection_card)
        self._restore_ack = QCheckBox("\u0130stemcinin ge\u00e7ici olarak \u00e7evrimd\u0131\u015f\u0131 kalaca\u011f\u0131n\u0131 onayl\u0131yorum.")
        self._restore_ack.setObjectName("restoreAcknowledgement")
        self._restore_ack.toggled.connect(self._update_restore_selection)
        restore_layout.addWidget(self._restore_ack)
        restore_actions = QHBoxLayout()
        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        restore_actions.addWidget(self._status, 1)
        self._download_button = QPushButton("Yede\u011fi \u0130ndir")
        self._download_button.setObjectName("secondaryBtn")
        self._download_button.clicked.connect(self._download_selected)
        restore_actions.addWidget(self._download_button)
        self._restore_button = QPushButton("G\u00fcvenli Geri Y\u00fckleme G\u00f6nder")
        self._restore_button.setObjectName("dangerBtn")
        self._restore_button.setEnabled(False)
        self._restore_button.clicked.connect(self._restore_selected)
        restore_actions.addWidget(self._restore_button)
        restore_layout.addLayout(restore_actions)
        self._restore_panel = restore_panel
        self._lower_layout.addWidget(restore_panel, 0, 0)

        policy_panel = QFrame()
        policy_panel.setObjectName("backupPanel")
        policy_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        policy_layout = QVBoxLayout(policy_panel)
        policy_layout.setContentsMargins(14, 12, 14, 12)
        policy_title = QLabel("Otomatik Yedekleme D\u00f6ng\u00fcleri & Saklama Politikas\u0131")
        policy_title.setObjectName("backupSectionTitle")
        policy_title.setWordWrap(True)
        policy_layout.addWidget(policy_title)
        policy_intro = QLabel("Zamanlama ve saklama ayarlar\u0131 merkezi yedekleme servisinde y\u00f6netilir.")
        policy_intro.setObjectName("backupMuted")
        policy_intro.setWordWrap(True)
        policy_layout.addWidget(policy_intro)
        self._policy_values = []
        for label_text, note_text, value_text in (
            ("WAL Checkpoint Periyodu", "Zamanlama merkezi servis tarafinda y\u00f6netilir.", "API bilgisi yok"),
            ("G\u00fcnl\u00fck Tam Yedek", "Yedek olu\u015fturma merkezi politikaya ba\u011fl\u0131d\u0131r.", "API bilgisi yok"),
            ("Saklama S\u00fcresi & Uyumluluk", "Saklama ayarlar\u0131 bu ekranda de\u011fi\u015ftirilemez.", "API bilgisi yok"),
            ("Otomatik Do\u011frulama", "Kay\u0131tl\u0131 checksum metadatas\u0131 g\u00f6sterilir.", "SHA-256"),
        ):
            row_frame = QFrame()
            row_frame.setObjectName("backupPolicyRow")
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(9, 7, 9, 7)
            text_layout = QVBoxLayout()
            label = QLabel(label_text)
            label.setObjectName("backupSectionTitle")
            note = QLabel(note_text)
            note.setObjectName("backupMuted")
            note.setWordWrap(True)
            text_layout.addWidget(label)
            text_layout.addWidget(note)
            value = QLabel(value_text)
            value.setObjectName("backupCode")
            row_layout.addLayout(text_layout, 1)
            row_layout.addWidget(value)
            policy_layout.addWidget(row_frame)
            self._policy_values.append((label, value))
        self._policy_panel = policy_panel
        self._lower_layout.addWidget(policy_panel, 0, 1)
        self._layout_metric_cards()
        self._layout_lower_cards()
        root.addWidget(lower)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_metric_grid"):
            self._layout_metric_cards()
            self._layout_lower_cards()
            self._layout_responsive_controls()

    def _clear_layout(self, layout):
        while layout.count():
            layout.takeAt(0)

    def _layout_responsive_controls(self):
        compact = self.width() < 700
        if hasattr(self, "_content_layout"):
            self._content_layout.setContentsMargins(12, 12, 12, 16) if compact else self._content_layout.setContentsMargins(44, 15, 20, 20)
        if hasattr(self, "_context_layout"):
            self._clear_layout(self._context_layout)
            if compact:
                self._context_layout.addWidget(self._context_core, 0, 0, 1, 2)
                self._context_layout.addWidget(self._storage_label, 1, 0)
                self._context_layout.addWidget(self._last_backup_label, 1, 1)
            else:
                self._context_layout.addWidget(self._context_core, 0, 0)
                self._context_layout.addWidget(self._storage_label, 0, 1)
                self._context_layout.addWidget(self._last_backup_label, 1, 0, 1, 3)
                self._context_layout.setColumnStretch(0, 1)
        if hasattr(self, "_header_layout"):
            self._clear_layout(self._header_layout)
            if compact:
                self._header_layout.addLayout(self._title_box, 0, 0, 1, 2)
                self._header_layout.addLayout(self._header_actions, 1, 0, 1, 2)
                self._snapshot_button.setText("Anl\u0131k Yedek")
            else:
                self._header_layout.addLayout(self._title_box, 0, 0)
                self._header_layout.addLayout(self._header_actions, 0, 1, Qt.AlignmentFlag.AlignTop)
                self._header_layout.setColumnStretch(0, 1)
                self._snapshot_button.setText("Anl\u0131k Genel Yedek Ba\u015flat")
        if hasattr(self, "_filter_layout"):
            self._clear_layout(self._filter_layout)
            company, date_filter, search, upload = self._filter_widgets
            if compact:
                self._filter_panel.setMinimumHeight(0)
                self._filter_layout.addWidget(self._company_filter_label, 0, 0)
                self._filter_layout.addWidget(self._date_filter_label, 0, 1)
                self._filter_layout.addWidget(company, 1, 0)
                self._filter_layout.addWidget(date_filter, 1, 1)
                self._filter_layout.addWidget(self._search_filter_label, 2, 0, 1, 2)
                self._filter_layout.addWidget(search, 3, 0, 1, 2)
                self._filter_layout.addWidget(upload, 4, 0, 1, 2)
                self._filter_layout.setColumnStretch(0, 1)
                self._filter_layout.setColumnStretch(1, 1)
            else:
                self._filter_panel.setMinimumHeight(78)
                self._filter_layout.addWidget(self._company_filter_label, 0, 0)
                self._filter_layout.addWidget(self._date_filter_label, 0, 1)
                self._filter_layout.addWidget(self._search_filter_label, 0, 2)
                self._filter_layout.addWidget(company, 1, 0)
                self._filter_layout.addWidget(date_filter, 1, 1)
                self._filter_layout.addWidget(search, 1, 2)
                self._filter_layout.addWidget(upload, 1, 3)
                self._filter_layout.setColumnStretch(2, 1)
        if hasattr(self, "_table_heading_layout"):
            self._clear_layout(self._table_heading_layout)
            if compact:
                self._table_heading_layout.addWidget(self._table_heading_title, 0, 0, 1, 2)
                self._table_heading_layout.addWidget(self._table_heading_count, 1, 0)
                self._table_heading_layout.addWidget(self._table_heading_integrity, 1, 1)
            else:
                self._table_heading_layout.addWidget(self._table_heading_title, 0, 0)
                self._table_heading_layout.addWidget(self._table_heading_count, 0, 1)
                self._table_heading_layout.addWidget(self._table_heading_integrity, 0, 2)
                self._table_heading_layout.setColumnStretch(0, 1)

    def _layout_metric_cards(self):
        while self._metric_grid.count():
            self._metric_grid.takeAt(0)
        width = self.width()
        columns = 4 if width >= 1000 else 2 if width >= 600 else 1
        for index, card in enumerate(self._metric_cards):
            card.setMinimumHeight(0 if width < 600 else 130)
            self._metric_grid.addWidget(card, index // columns, index % columns)

    def _layout_lower_cards(self):
        while self._lower_layout.count():
            self._lower_layout.takeAt(0)
        if self.width() >= 1000:
            self._lower_layout.addWidget(self._restore_panel, 0, 0)
            self._lower_layout.addWidget(self._policy_panel, 0, 1)
            self._lower_layout.setColumnStretch(0, 3)
            self._lower_layout.setColumnStretch(1, 2)
        else:
            self._lower_layout.addWidget(self._restore_panel, 0, 0)
            self._lower_layout.addWidget(self._policy_panel, 1, 0)
            self._lower_layout.setColumnStretch(0, 1)

    def _select_backup_row(self, row):
        self._table.selectRow(row)
        self._restore_ack.setChecked(False)
        self._update_restore_selection()

    def _update_restore_selection(self, _checked=False):
        item = self._selected_silent()
        company = self._company_combo.currentText() or "-"
        self._restore_target.setText(f"HEDEF \u0130STEMC\u0130: {company}")
        self._restore_snapshot.setText(
            f"UYGULANACAK ANLIK G\u00d6R\u00dcNT\u00dc: {item.get('filename') or '-'}" if item else "UYGULANACAK ANLIK G\u00d6R\u00dcNT\u00dc: -"
        )
        self._restore_button.setEnabled(bool(item) and self._restore_ack.isChecked())

    def _selected_silent(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row]

    def _snapshot_unavailable(self):
        self._status.setText("Anl\u0131k yedek ba\u015flatma merkezi API taraf\u0131nda sunulmuyor.")

    def _upload_unavailable(self):
        message = "Yedek i\u00e7e aktarma merkezi API taraf\u0131nda sunulmuyor."
        self._status.setText(message)
        show_toast(self, message, "warning")

    def _keep(self, worker: QThread):
        self._workers.add(worker)
        worker.finished.connect(lambda: self._workers.discard(worker))
        worker.start()

    def _load_companies(self):
        worker = _FetchCompanies()
        worker.done.connect(self._populate_companies)
        worker.error.connect(self._show_error)
        self._keep(worker)

    def _populate_companies(self, companies: list):
        self._company_combo.blockSignals(True)
        self._company_combo.clear()
        for company in companies:
            self._company_combo.addItem(
                company.get("company_name", "?"), company.get("id", "")
            )
        self._company_combo.blockSignals(False)
        self._load_backups()

    def _load_backups(self):
        tenant_id = self._company_combo.currentData()
        if not tenant_id:
            return
        self._status.setText("Yedekler y\u00fckleniyor...")
        worker = _FetchBackups(str(tenant_id))
        worker.done.connect(self._populate_backups)
        worker.error.connect(self._show_error)
        self._keep(worker)

    def _populate_backups(self, items: list):
        self._items = list(items or [])
        self._table.setRowCount(0)
        self._restore_ack.setChecked(False)
        self._table.clearSelection()
        self._table.setCurrentCell(-1, -1)
        for item in self._items:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setRowHeight(row, 66)
            checksum = str(item.get("sha256") or "")
            source = str(item.get("source") or "server")
            product = str(item.get("product_code") or "teknik_servis")
            client = str(item.get("hardware_id") or item.get("installation_id") or "-")
            values = [
                item.get("filename", "?"),
                f"{source} / {product}",
                item.get("created_at") or item.get("modified") or "-",
                _size_text(int(item.get("size_bytes", 0))),
                f"SHA-256: {checksum[:12]}..." if checksum else "Hash yok",
                f"{client} / {product}",
            ]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
            select = QPushButton("Se\u00e7")
            select.setObjectName("backupSelect")
            select.setMinimumWidth(72)
            select.setFixedHeight(30)
            select.setStyleSheet("background: #252a39; color: #dee2f6; border: 1px solid #424754; border-radius: 4px; padding: 4px 8px;")
            select.clicked.connect(lambda _checked=False, current=row: self._select_backup_row(current))
            self._table.setCellWidget(row, 6, select)
        self._metric_count.setText(str(len(self._items)))
        total_bytes = sum(int(item.get("size_bytes", 0) or 0) for item in self._items)
        checksummed = sum(bool(item.get("sha256")) for item in self._items)
        self._metric_size.setText(f"{checksummed} / {len(self._items)}")
        self._metric_rpo.setText("--")
        self._metric_rto.setText("--")
        self._wal_coverage.setText("API VER\u0130S\u0130 YOK")
        self._table_integrity.setText(f"SHA-256 METADATASI: {checksummed} / {len(self._items)}")
        self._wal_summary.setText(
            "Hash metadatas\u0131 mevcut." if checksummed == len(self._items) and self._items
            else "Hash metadatas\u0131 t\u00fcm kay\u0131tlarda mevcut de\u011fil."
        )
        latest = self._items[0].get("created_at") or self._items[0].get("modified") or "-" if self._items else "-"
        self._last_backup_label.setText(f"SON YEDEK: {latest}")
        self._storage_label.setText(f"DEPOLAMA: {_size_text(total_bytes)}")
        self._filter_backups(self._search.text())
        self._update_restore_selection()
        self._status.setText(
            f"{len(self._items)} yedek bulundu." if self._items else "Bu firma i\u00e7in yedek bulunamad\u0131."
        )

    def _filter_backups(self, query: str):
        needle = str(query or "").strip().casefold()
        days = int(self._date_filter.currentData() or 0)
        cutoff = datetime.now().date() - timedelta(days=days) if days else None
        visible_count = 0
        for row in range(self._table.rowCount()):
            item = self._items[row] if row < len(self._items) else {}
            values = [
                self._table.item(row, column).text()
                for column in range(self._table.columnCount())
                if self._table.item(row, column) is not None
            ]
            match = not needle or needle in " ".join(values).casefold()
            if cutoff is not None:
                timestamp = str(item.get("created_at") or item.get("modified") or "")
                try:
                    backup_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()
                    match = match and backup_date >= cutoff
                except ValueError:
                    pass
            self._table.setRowHidden(row, not match)
            visible_count += int(match)
        self._table_count.setText(f"{visible_count} G\u00f6steriliyor")

    def _on_backup_filter_changed(self, _index):
        self._filter_backups(self._search.text())

    def _selected(self) -> dict | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._items):
            self._status.setText("L\u00fctfen bir yedek se\u00e7in.")
            return None
        return self._items[row]

    def _download_selected(self):
        item = self._selected()
        tenant_id = self._company_combo.currentData()
        if not item or not tenant_id:
            return
        suggested = Path(str(item.get("filename") or "Firma.db")).name.replace(" (guncel)", "")
        target, _ = QFileDialog.getSaveFileName(
            self, "Yede\u011fi Kaydet", suggested, "SQLite Veritaban\u0131 (*.db);;T\u00fcm Dosyalar (*)"
        )
        if not target:
            return
        self._status.setText("Yedek indiriliyor...")
        worker = _DownloadBackup(str(tenant_id), item, target)
        worker.done.connect(self._download_done)
        worker.error.connect(self._show_error)
        self._keep(worker)

    def _restore_selected(self):
        if not self._restore_ack.isChecked():
            message = "Geri yukleme icin istemci uyarisi onayi gerekli."
            self._status.setText(message)
            show_toast(self, message, "warning")
            return
        item = self._selected()
        tenant_id = self._company_combo.currentData()
        if not item or not tenant_id:
            return
        company = self._company_combo.currentText()
        answer = QMessageBox.question(
            self,
            "Geri Y\u00fckleme Onay\u0131",
            f"{company} i\u00e7in '{item.get('filename', '?')}' yede\u011fi geri y\u00fckleme "
            "kuyru\u011funa al\u0131ns\u0131n m\u0131? Masa\u00fcst\u00fc uygulamas\u0131 mevcut verinin "
            "g\u00fcvenlik kopyas\u0131n\u0131 ald\u0131ktan sonra komutu uygular.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._status.setText("Geri y\u00fckleme komutu g\u00f6nderiliyor...")
        worker = _RestoreBackup(str(tenant_id), item)
        worker.done.connect(self._restore_done)
        worker.error.connect(self._show_error)
        self._keep(worker)

    def _restore_done(self, result: dict):
        command_id = result.get("command_id")
        suffix = f" Komut No: {command_id}" if command_id else ""
        message = f"Geri y\u00fckleme kuyru\u011fa al\u0131nd\u0131.{suffix}"
        self._status.setText(f"\u2713 {message}")
        show_toast(self, message, "success")

    def _download_done(self, path):
        message = f"Yedek kaydedildi: {path}"
        self._status.setText(message)
        show_toast(self, message, "success")

    def _show_error(self, error):
        message = f"Hata: {error}"
        self._status.setText(message)
        show_toast(self, message, "error")
    QGridLayout,
