"""AYEC Pro Admin Console - controlled desktop update deployment."""
import re
import json

from PyQt6.QtCore import QRect, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import api_client


class _CompanyInfoDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        item_option = QStyleOptionViewItem(option)
        self.initStyleOption(item_option, index)
        item_option.text = ""
        option.widget.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            item_option,
            painter,
            option.widget,
        )
        rect = option.rect.adjusted(8, 4, -4, -4)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.save()
        name_font = QFont(option.font)
        name_font.setPointSize(max(8, name_font.pointSize() - 1))
        name_font.setBold(True)
        painter.setFont(name_font)
        painter.setPen(option.palette.highlightedText().color() if selected else QColor("#dee2f6"))
        painter.drawText(QRect(rect.x(), rect.y(), rect.width(), 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(index.data(Qt.ItemDataRole.DisplayRole) or ""))
        meta_font = QFont(option.font)
        meta_font.setPointSize(max(7, meta_font.pointSize() - 2))
        painter.setFont(meta_font)
        painter.setPen(QColor("#8c909f"))
        painter.drawText(QRect(rect.x(), rect.y() + 18, rect.width(), 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(index.data(Qt.ItemDataRole.UserRole + 2) or ""))
        painter.restore()


class _FetchCompanies(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception as exc:
            self.error.emit(str(exc))


class _DeployUpdate(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, version: str, targets: list, changelog: str, channel: str):
        super().__init__()
        self._version = version
        self._targets = targets
        self._changelog = changelog
        self._channel = channel

    def run(self):
        try:
            self.done.emit(api_client.deploy_update(
                self._version,
                self._targets,
                self._changelog,
                self._channel,
            ))
        except Exception as exc:
            self.error.emit(str(exc))


class UpdatesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._workers: set[QThread] = set()
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        self.setObjectName("updatesPage")
        self.setStyleSheet("""
            QWidget#updatesPage { background: #0e1321; color: #dee2f6; }
            QWidget#updatesPage QLabel { background: transparent; }
            QWidget#updatesContent { background: #0e1321; }
            QFrame#updatePanel { background: #161b2a; border: 1px solid #252a39; border-radius: 6px; }
            QFrame#updateMetric { background: #1a1f2e; border: none; border-radius: 6px; }
            QFrame#updateStatusChip, QFrame#updateTelemetryRow, QFrame#updateSecurityRow { background: #252a39; border: none; border-radius: 4px; }
            QLabel#updateEyebrow, QLabel#updateCode { color: #4cd7f6; font-family: 'Segoe UI', Arial; font-size: 10px; font-weight: 700; }
            QLabel#updateTitle { color: #dee2f6; font-size: 23px; font-weight: 700; }
            QLabel#updateSubtitle, QLabel#updateMuted { color: #8c909f; }
            QLabel#updateHeaderBadge, QLabel#updatePilotBadge, QLabel#updateCdnBadge { background: #252a39; border-radius: 4px; padding: 6px 8px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QLabel#updateHeaderBadge { color: #adc6ff; }
            QLabel#updatePilotBadge { color: #4edea3; }
            QLabel#updateCdnBadge { color: #c2c6d6; }
            QLabel#updateSectionTitle { color: #dee2f6; font-size: 15px; font-weight: 700; }
            QLabel#updateMetricTitle { color: #8c909f; font-size: 10px; font-weight: 700; }
            QLabel#updateMetricValue { color: #adc6ff; font-size: 24px; font-weight: 700; }
            QLabel#updateTelemetryEmpty { background: #090e1c; border: 1px solid #252a39; border-radius: 4px; padding: 12px; }
            QLineEdit#fieldInput, QComboBox#combo, QLineEdit#searchInput, QTextEdit#textArea { background: #090e1c; color: #dee2f6; border: 1px solid #424754; border-radius: 4px; padding: 8px 10px; }
            QTextEdit#textArea { background: #090e1c; }
            QTableWidget#updateMatrix { background: #090e1c; alternate-background-color: #161b2a; border: 1px solid #252a39; color: #dee2f6; gridline-color: #252a39; }
            QTableWidget#updateMatrix::item { padding: 7px 8px; }
            QTableWidget#updateMatrix QHeaderView::section { background: #252a39; color: #adc6ff; border: none; padding: 9px 7px; font-size: 9px; font-weight: 700; }
            QTextEdit#codeBox { background: #090e1c; color: #4edea3; border: 1px solid #252a39; border-radius: 4px; padding: 9px; font-family: 'Segoe UI', Arial; }
            QPushButton#secondaryBtn { background: #252a39; color: #dee2f6; border: 1px solid #424754; border-radius: 4px; padding: 7px 10px; }
            QPushButton#primaryBtn { background: #adc6ff; color: #001a42; border: none; border-radius: 5px; padding: 9px 13px; font-weight: 700; }
            QPushButton#dangerBtn { background: #93000a; color: #ffdad6; border: 1px solid #ffb4ab; border-radius: 4px; padding: 7px 10px; }
            QPushButton#updateRowAction { background: #252a39; color: #c2c6d6; border: none; border-radius: 3px; padding: 5px; }
            QCheckBox#forceUpdate { color: #c2c6d6; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("updatesScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("updatesContent")
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 14, 20, 20)
        root.setSpacing(12)

        header_panel = QFrame()
        header_panel.setObjectName("updatePanel")
        header_layout = QGridLayout(header_panel)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setHorizontalSpacing(14)
        header_text = QVBoxLayout()
        eyebrow = QLabel("AYEC PRO OTA PIPELINE  //  DEPLOYMENT CONSOLE")
        eyebrow.setObjectName("updateEyebrow")
        header_text.addWidget(eyebrow)
        title = QLabel("G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131 & OTA S\u00fcr\u00fcm Y\u00f6netimi")
        title.setObjectName("updateTitle")
        title.setWordWrap(True)
        header_text.addWidget(title)
        info = QLabel(
            "Yeni masa\u00fcst\u00fc ve sunucu s\u00fcr\u00fcmlerini \u00f6nce se\u00e7ili pilot firmalarda test edin; "
            "da\u011f\u0131t\u0131m durumunu telemetri geldik\u00e7e izleyin."
        )
        info.setObjectName("updateSubtitle")
        info.setWordWrap(True)
        header_text.addWidget(info)
        header_layout.addLayout(header_text, 0, 0)
        badges = QGridLayout()
        self._stable_badge = QLabel("KARARLI S\u00dcR\u00dcM\nAPI B\u0130LG\u0130S\u0130 YOK")
        self._stable_badge.setObjectName("updateHeaderBadge")
        self._pilot_badge = QLabel("P\u0130LOT KANAL\n" + "Pilot")
        self._pilot_badge.setObjectName("updatePilotBadge")
        self._cdn_badge = QLabel("DA\u011eITIM SUNUCUSU\nAPI DURUMU YOK")
        self._cdn_badge.setObjectName("updateCdnBadge")
        for badge in (self._stable_badge, self._pilot_badge, self._cdn_badge):
            badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        badges.addWidget(self._stable_badge, 0, 0)
        badges.addWidget(self._pilot_badge, 0, 1)
        badges.addWidget(self._cdn_badge, 1, 0, 1, 2)
        header_layout.addLayout(badges, 0, 1)
        header_layout.setColumnStretch(0, 1)
        self._header_layout = header_layout
        self._header_text_layout = header_text
        self._badges_layout = badges
        root.addWidget(header_panel)

        metrics = QGridLayout()
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setSpacing(10)
        self._metric_active = QLabel("0")
        self._metric_selected = QLabel("0")
        self._metric_channel = QLabel("Pilot")
        self._metric_release = QLabel("Draft")
        self._metric_pilot_success = QLabel("--")
        self._metric_deploy_state = QLabel("Beklemede")
        self._metric_mode = QLabel("Silent OTA")
        self._pilot_metric_note = QLabel("Canl\u0131 test telemetrisi bekleniyor")
        metric_items = (
            ("DA\u011eITIMA HAZIR PAKET", self._metric_release, "Paket boyutu ve imza API'de yok"),
            ("P\u0130LOT TEST BA\u015eARISI", self._metric_pilot_success, self._pilot_metric_note),
            ("GENEL DA\u011eITIM DURUMU", self._metric_deploy_state, "\u0130nsan onay\u0131 gerekli"),
            ("\u0130STEMC\u0130 G\u00dcNCELLEME MODU", self._metric_mode, "Arka planda sessiz da\u011f\u0131t\u0131m"),
        )
        self._metric_cards = []
        for index, (caption_text, value, note_text) in enumerate(metric_items):
            card = QFrame()
            card.setObjectName("updateMetric")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(13, 10, 13, 10)
            caption = QLabel(caption_text)
            caption.setObjectName("updateMetricTitle")
            value.setObjectName("updateMetricValue")
            note = note_text if isinstance(note_text, QLabel) else QLabel(note_text)
            note.setObjectName("updateMuted")
            card_layout.addWidget(caption)
            card_layout.addWidget(value)
            card_layout.addWidget(note)
            self._metric_cards.append(card)
            metrics.addWidget(card, 0, index)
        self._metric_grid = metrics
        root.addLayout(metrics)

        content_grid = QGridLayout()
        content_grid.setContentsMargins(0, 0, 0, 0)
        content_grid.setHorizontalSpacing(12)
        content_grid.setVerticalSpacing(12)
        self._content_grid = content_grid
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        params_panel = QFrame()
        params_panel.setObjectName("updatePanel")
        params_layout = QVBoxLayout(params_panel)
        params_layout.setContentsMargins(14, 12, 14, 12)
        params_heading = QHBoxLayout()
        params_title = QLabel("Da\u011f\u0131t\u0131m & Kanal Parametreleri")
        params_title.setObjectName("updateSectionTitle")
        params_heading.addWidget(params_title, 1)
        self._channel_badge = QLabel("KANAL: PILOT")
        self._channel_badge.setObjectName("updateCode")
        params_heading.addWidget(self._channel_badge)
        params_layout.addLayout(params_heading)

        version_row = QGridLayout()
        self._version_label = QLabel("Hedef OTA Paketi")
        version_row.addWidget(self._version_label, 0, 0)
        self._version = QLineEdit()
        self._version.setObjectName("fieldInput")
        self._version.setPlaceholderText("2.0.1")
        self._version.textChanged.connect(self._sync_metrics)
        version_row.addWidget(self._version, 1, 0)
        self._channel_label = QLabel("Da\u011f\u0131t\u0131m Kanal\u0131")
        version_row.addWidget(self._channel_label, 0, 1)
        self._channel = QComboBox()
        self._channel.setObjectName("combo")
        self._channel.addItem("Pilot", "pilot")
        self._channel.addItem("Kararl\u0131", "stable")
        self._channel.currentIndexChanged.connect(self._sync_metrics)
        version_row.addWidget(self._channel, 1, 1)
        version_row.setColumnStretch(0, 1)
        version_row.setColumnStretch(1, 1)
        params_layout.addLayout(version_row)
        self._version_row = version_row
        self._force_update = QCheckBox("Zorunlu g\u00fcncelleme zorlamas\u0131")
        self._force_update.setObjectName("forceUpdate")
        self._force_update.setEnabled(False)
        self._force_update.setToolTip("Zorunlu guncelleme bayragi bu API tarafinda desteklenmiyor.")
        params_layout.addWidget(self._force_update)
        left_layout.addWidget(params_panel)

        matrix_panel = QFrame()
        matrix_panel.setObjectName("updatePanel")
        matrix_layout = QVBoxLayout(matrix_panel)
        matrix_layout.setContentsMargins(14, 12, 14, 12)
        matrix_heading = QHBoxLayout()
        matrix_title = QLabel("Hedef Firma Da\u011f\u0131t\u0131m Matrisi")
        matrix_title.setObjectName("updateSectionTitle")
        matrix_heading.addWidget(matrix_title, 1)
        select_all = QPushButton("T\u00fcm\u00fcn\u00fc Se\u00e7")
        select_all.setObjectName("secondaryBtn")
        select_all.clicked.connect(lambda: self._set_all_checks(Qt.CheckState.Checked))
        matrix_heading.addWidget(select_all)
        clear = QPushButton("Temizle")
        clear.setObjectName("secondaryBtn")
        clear.clicked.connect(lambda: self._set_all_checks(Qt.CheckState.Unchecked))
        matrix_heading.addWidget(clear)
        matrix_layout.addLayout(matrix_heading)
        matrix_subtitle = QLabel("Se\u00e7ilen firmalara e\u015fzamanl\u0131 hash do\u011frulamal\u0131 paket da\u011f\u0131t\u0131l\u0131r.")
        matrix_subtitle.setObjectName("updateMuted")
        matrix_layout.addWidget(matrix_subtitle)

        scope_row = QHBoxLayout()
        self._pilot = QRadioButton("Se\u00e7ili pilot firmalar")
        self._all = QRadioButton("T\u00fcm aktif firmalar")
        self._pilot.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self._pilot)
        group.addButton(self._all)
        self._scope_group = group
        scope_row.addWidget(self._pilot)
        scope_row.addWidget(self._all)
        scope_row.addStretch(1)
        self._target_summary = QLabel("0 Firma Se\u00e7ili")
        self._target_summary.setObjectName("counterLabel")
        scope_row.addWidget(self._target_summary)
        matrix_layout.addLayout(scope_row)

        self._company_search = QLineEdit()
        self._company_search.setObjectName("searchInput")
        self._company_search.setPlaceholderText("Firma veya istasyon ara...")
        self._company_search.textChanged.connect(self._filter_companies)
        matrix_layout.addWidget(self._company_search)

        self._companies = QTableWidget(0, 5)
        self._companies.setObjectName("updateMatrix")
        self._companies.setItemDelegateForColumn(1, _CompanyInfoDelegate(self._companies))
        self._companies.setHorizontalHeaderLabels([
            "SE\u00c7", "F\u0130RMA / \u0130STASYON B\u0130LG\u0130S\u0130", "MEVCUT S\u00dcR\u00dcM", "DURUM", "EYLEM"
        ])
        self._companies.verticalHeader().hide()
        self._companies.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for column, width in ((0, 42), (2, 112), (3, 124), (4, 48)):
            self._companies.setColumnWidth(column, width)
        self._companies.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._companies.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._companies.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._companies.verticalHeader().setDefaultSectionSize(60)
        self._companies.setWordWrap(True)
        self._companies.setMinimumHeight(240)
        self._companies.setMaximumHeight(470)
        self._companies.itemChanged.connect(self._update_target_summary)
        matrix_layout.addWidget(self._companies)
        self._matrix_footer = QLabel("Toplam hedef havuzu: 0 kayit")
        self._matrix_footer.setObjectName("updateCode")
        matrix_layout.addWidget(self._matrix_footer)
        left_layout.addWidget(matrix_panel)

        notes_panel = QFrame()
        notes_panel.setObjectName("updatePanel")
        notes_layout = QVBoxLayout(notes_panel)
        notes_layout.setContentsMargins(14, 10, 14, 12)
        notes_header = QHBoxLayout()
        notes_heading = QLabel("S\u00fcr\u00fcm De\u011fi\u015fiklik Notlar\u0131 (Changelog)")
        notes_heading.setObjectName("updateSectionTitle")
        notes_header.addWidget(notes_heading, 1)
        format_badge = QLabel("MARKDOWN FORMAT")
        format_badge.setObjectName("updateMuted")
        notes_header.addWidget(format_badge)
        notes_layout.addLayout(notes_header)
        self._changelog = QTextEdit()
        self._changelog.setObjectName("textArea")
        self._changelog.setMinimumHeight(130)
        self._changelog.setMaximumHeight(220)
        self._changelog.setPlaceholderText(
            "D\u00fczeltilen hatalar\u0131 ve kullan\u0131c\u0131y\u0131 etkileyen de\u011fi\u015fiklikleri yaz\u0131n."
        )
        notes_layout.addWidget(self._changelog)
        publish_actions = QHBoxLayout()
        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        publish_actions.addWidget(self._status, 1)
        self._test_button = QPushButton("Test Uc Noktasina Gonder")
        self._test_button.setObjectName("secondaryBtn")
        self._test_button.setEnabled(False)
        self._test_button.setToolTip("Test ucu bu Admin API tarafinda sunulmuyor.")
        publish_actions.addWidget(self._test_button)
        deploy = QPushButton("Dagitimi Kuyrukla & Yayinla")
        deploy.setObjectName("primaryBtn")
        deploy.clicked.connect(self._deploy)
        self._deploy_button = deploy
        publish_actions.addWidget(deploy)
        notes_layout.addLayout(publish_actions)
        left_layout.addWidget(notes_panel)

        telemetry_panel = QFrame()
        telemetry_panel.setObjectName("updatePanel")
        telemetry_layout = QVBoxLayout(telemetry_panel)
        telemetry_layout.setContentsMargins(14, 10, 14, 12)
        telemetry_layout.setSpacing(10)
        telemetry_header = QHBoxLayout()
        telemetry_heading = QLabel("Canl\u0131 Da\u011f\u0131t\u0131m Telemetrisi")
        telemetry_heading.setObjectName("updateSectionTitle")
        telemetry_heading.setMaximumHeight(28)
        telemetry_header.addWidget(telemetry_heading, 1)
        stream_badge = QLabel("TELEMETR\u0130 AKI\u015eI")
        stream_badge.setObjectName("updateCode")
        telemetry_header.addWidget(stream_badge)
        telemetry_layout.addLayout(telemetry_header)
        stream_info = QFrame()
        stream_info.setObjectName("updateTelemetryRow")
        stream_layout = QVBoxLayout(stream_info)
        stream_layout.setContentsMargins(10, 8, 10, 8)
        stream_title = QLabel("HTTPS Encrypted Chunk Stream")
        stream_title.setObjectName("updateCode")
        stream_title.setMaximumHeight(22)
        stream_layout.addWidget(stream_title)
        self._telemetry_status = QLabel("Da\u011f\u0131t\u0131m telemetrisi API taraf\u0131ndan saglanmiyor.")
        self._telemetry_status.setObjectName("updateMuted")
        self._telemetry_status.setWordWrap(True)
        self._telemetry_status.setMaximumHeight(48)
        stream_layout.addWidget(self._telemetry_status)
        telemetry_layout.addWidget(stream_info)

        self._telemetry_empty = QLabel("Dagitim kuyruklandiginda sunucu yaniti burada gorunur.")
        self._telemetry_empty.setObjectName("updateTelemetryEmpty")
        self._telemetry_empty.setWordWrap(True)
        self._telemetry_empty.setMinimumHeight(150)
        self._telemetry_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        telemetry_layout.addWidget(self._telemetry_empty)

        self._telemetry_log = QTextEdit()
        self._telemetry_log.setObjectName("codeBox")
        self._telemetry_log.setReadOnly(True)
        self._telemetry_log.setFixedHeight(150)
        self._telemetry_log.setPlainText("Canli telemetri kaydi henuz alinmadi.")
        telemetry_layout.addWidget(self._telemetry_log)
        security_panel = QFrame()
        security_panel.setObjectName("updatePanel")
        security_layout = QVBoxLayout(security_panel)
        security_layout.setContentsMargins(14, 10, 14, 12)
        security_title = QLabel("OTA Guvenlik & Dogrulama Durumu")
        security_title.setObjectName("updateSectionTitle")
        security_layout.addWidget(security_title)
        for label_text, status_text in (
            ("GPG imza dogrulama", "API bilgisi sunulmuyor"),
            ("Rollback korumasi", "API bilgisi sunulmuyor"),
        ):
            row = QFrame()
            row.setObjectName("updateSecurityRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(9, 8, 9, 8)
            label = QLabel(label_text)
            label.setObjectName("updateMuted")
            status = QLabel(status_text)
            status.setObjectName("updateCode")
            row_layout.addWidget(label, 1)
            row_layout.addWidget(status)
            security_layout.addWidget(row)

        right_column = QWidget()
        self._right_layout = QVBoxLayout(right_column)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(12)
        self._right_layout.addWidget(telemetry_panel, 1)
        self._right_layout.addWidget(security_panel)
        self._left_column = left_column
        self._right_column = right_column
        root.addLayout(content_grid, 1)
        self._layout_content_panels()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _keep(self, worker: QThread):
        self._workers.add(worker)
        worker.finished.connect(lambda: self._workers.discard(worker))
        worker.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_content_panels()

    def _layout_content_panels(self):
        if not hasattr(self, "_content_grid"):
            return
        compact = self.width() < 600
        while self._header_layout.count():
            self._header_layout.takeAt(0)
        if compact:
            self._header_layout.addLayout(self._header_text_layout, 0, 0, 1, 2)
            self._header_layout.addLayout(self._badges_layout, 1, 0, 1, 2)
            self._header_layout.setColumnStretch(0, 1)
            self._header_layout.setColumnStretch(1, 1)
            while self._version_row.count():
                self._version_row.takeAt(0)
            self._version_row.addWidget(self._version_label, 0, 0)
            self._version_row.addWidget(self._version, 1, 0)
            self._version_row.addWidget(self._channel_label, 2, 0)
            self._version_row.addWidget(self._channel, 3, 0)
            self._version_row.setColumnStretch(0, 1)
            self._version_row.setColumnStretch(1, 0)
            while self._metric_grid.count():
                self._metric_grid.takeAt(0)
            for index, card in enumerate(self._metric_cards):
                self._metric_grid.addWidget(card, index, 0)
            for column in (0, 1):
                self._metric_grid.setColumnStretch(column, int(column == 0))
            self._metric_grid.setColumnStretch(2, 0)
            self._metric_grid.setColumnStretch(3, 0)
            for column, width in ((0, 34), (2, 82), (3, 86), (4, 34)):
                self._companies.setColumnWidth(column, width)
            for column in (2, 3, 4):
                self._companies.setColumnHidden(column, True)
            for row in range(self._companies.rowCount()):
                item = self._companies.item(row, 1)
                if item:
                    version = self._companies.item(row, 2).text()
                    status = self._companies.item(row, 3).text()
                    meta = str(item.data(Qt.ItemDataRole.UserRole + 3) or "")
                    item.setData(Qt.ItemDataRole.UserRole + 2, " \u00b7 ".join(part for part in (meta, "Surum: " + version, status) if part))
        else:
            self._header_layout.addLayout(self._header_text_layout, 0, 0)
            self._header_layout.addLayout(self._badges_layout, 0, 1)
            self._header_layout.setColumnStretch(0, 1)
            self._header_layout.setColumnStretch(1, 0)
            while self._version_row.count():
                self._version_row.takeAt(0)
            self._version_row.addWidget(self._version_label, 0, 0)
            self._version_row.addWidget(self._version, 1, 0)
            self._version_row.addWidget(self._channel_label, 0, 1)
            self._version_row.addWidget(self._channel, 1, 1)
            self._version_row.setColumnStretch(0, 1)
            self._version_row.setColumnStretch(1, 1)
            while self._metric_grid.count():
                self._metric_grid.takeAt(0)
            for index, card in enumerate(self._metric_cards):
                self._metric_grid.addWidget(card, 0, index)
            for column in range(4):
                self._metric_grid.setColumnStretch(column, 1)
            for column, width in ((0, 42), (2, 112), (3, 124), (4, 48)):
                self._companies.setColumnWidth(column, width)
            for column in (2, 3, 4):
                self._companies.setColumnHidden(column, False)
            for row in range(self._companies.rowCount()):
                item = self._companies.item(row, 1)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole + 2, item.data(Qt.ItemDataRole.UserRole + 3))
        while self._content_grid.count():
            self._content_grid.takeAt(0)
        if self.width() >= 1100:
            self._content_grid.addWidget(self._left_column, 0, 0)
            self._content_grid.addWidget(self._right_column, 0, 1)
            self._content_grid.setColumnStretch(0, 7)
            self._content_grid.setColumnStretch(1, 5)
            self._content_grid.setRowStretch(0, 1)
            self._right_column.setMinimumWidth(300)
        else:
            self._content_grid.addWidget(self._left_column, 0, 0)
            self._content_grid.addWidget(self._right_column, 1, 0)
            self._content_grid.setColumnStretch(0, 1)
            self._content_grid.setRowStretch(0, 0)
            self._content_grid.setRowStretch(1, 1)
            self._right_column.setMinimumWidth(0)

    def _load_companies(self):
        worker = _FetchCompanies()
        worker.done.connect(self._populate_companies)
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _populate_companies(self, companies: list):
        self._companies.setRowCount(0)
        for company in companies:
            if int(company.get("active", 1) or 0) != 1:
                continue
            row = self._companies.rowCount()
            self._companies.insertRow(row)
            checked = QTableWidgetItem("")
            checked.setFlags(checked.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            checked.setCheckState(Qt.CheckState.Unchecked)
            self._companies.setItem(row, 0, checked)
            company_name = str(company.get("company_name", "?"))
            name = QTableWidgetItem(company_name)
            name.setData(Qt.ItemDataRole.UserRole, company.get("id", ""))
            station = company.get("station_name") or company.get("station") or ""
            station_id = company.get("station_id") or company.get("station_code") or ""
            terminal_count = company.get("terminal_count") or company.get("device_count") or 0
            station_details = [str(station)] if station else []
            if station_id:
                station_details.append("Istasyon #" + str(station_id))
            if terminal_count:
                station_details.append(str(terminal_count) + " Terminal")
            if not station_details:
                station_details.append("Firma merkezi / terminal bilgisi yok")
            searchable = " ".join((company_name, *station_details, str(company.get("id", ""))))
            name.setData(Qt.ItemDataRole.UserRole + 1, searchable)
            name.setData(Qt.ItemDataRole.UserRole + 2, " \u00b7 ".join(station_details))
            name.setData(Qt.ItemDataRole.UserRole + 3, " \u00b7 ".join(station_details))
            name.setToolTip(f"{station}\nID: {company.get('id', '-')}")
            self._companies.setItem(row, 1, name)
            self._companies.setItem(row, 2, QTableWidgetItem(str(company.get("current_version") or company.get("app_version") or company.get("version") or "--")))
            status_text = str(company.get("update_status") or company.get("status") or "Active")
            display_status = "Aktif" if status_text.casefold() == "active" else status_text
            status_item = QTableWidgetItem(display_status)
            status_color = "#4edea3" if status_text.casefold() in {"active", "online", "guncel", "g\u00fcncel & aktif"} else "#c2c6d6"
            status_item.setForeground(QBrush(QColor(status_color)))
            self._companies.setItem(row, 3, status_item)
            action = QTableWidgetItem("\u203a")
            action.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._companies.setItem(row, 4, action)
        self._matrix_footer.setText(f"Toplam hedef havuzu: {self._companies.rowCount()} kayit")
        self._filter_companies(self._company_search.text())
        self._update_target_summary()
        self._sync_metrics()
        self._status.setText(f"{self._companies.rowCount()} aktif firma y\u00fcklendi.")

    def _filter_companies(self, query: str):
        needle = str(query or "").strip().casefold()
        for row in range(self._companies.rowCount()):
            values = " ".join(
                str(self._companies.item(row, column).data(Qt.ItemDataRole.UserRole + 1) or self._companies.item(row, column).text())
                for column in range(1, self._companies.columnCount())
                if self._companies.item(row, column)
            )
            self._companies.setRowHidden(row, bool(needle) and needle not in values.casefold())

    def _update_target_summary(self, *_args):
        selected = sum(
            self._companies.item(index, 0).checkState() == Qt.CheckState.Checked
            for index in range(self._companies.rowCount())
        )
        self._target_summary.setText(f"{selected} Firma Se\u00e7ili")
        self._metric_selected.setText(str(selected))

    def _sync_metrics(self, *_args):
        self._metric_active.setText(str(self._companies.rowCount()))
        self._metric_channel.setText(self._channel.currentText())
        self._metric_release.setText(self._version.text().strip() or "Draft")
        self._channel_badge.setText(f"KANAL: {self._channel.currentText().upper()}")
        self._pilot_badge.setText("PILOT KANAL\n" + self._channel.currentText())

    def _set_all_checks(self, state: Qt.CheckState):
        for row in range(self._companies.rowCount()):
            item = self._companies.item(row, 0)
            if not self._companies.isRowHidden(row):
                item.setCheckState(state)
        self._update_target_summary()

    def _selected_targets(self) -> list[str]:
        return [
            str(self._companies.item(index, 1).data(Qt.ItemDataRole.UserRole))
            for index in range(self._companies.rowCount())
            if self._companies.item(index, 0).checkState() == Qt.CheckState.Checked
        ]

    def _deploy(self):
        version = self._version.text().strip()
        changelog = self._changelog.toPlainText().strip()
        channel = str(self._channel.currentData() or "pilot")
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9.-]+)?", version):
            self._status.setText("Ge\u00e7erli bir s\u00fcr\u00fcm numaras\u0131 girin. \u00d6rnek: 2.0.1")
            return
        if not changelog:
            self._status.setText("S\u00fcr\u00fcm notlar\u0131 bo\u015f olamaz.")
            return
        targets = [] if self._all.isChecked() else self._selected_targets()
        if self._pilot.isChecked() and not targets:
            self._status.setText("En az bir pilot firma se\u00e7in.")
            return
        if self._all.isChecked():
            answer = QMessageBox.warning(
                self,
                "Genel Da\u011f\u0131t\u0131m Onay\u0131",
                f"{version} s\u00fcr\u00fcm\u00fc t\u00fcm aktif firmalara g\u00f6nderilecek. "
                "Pilot do\u011frulamas\u0131n\u0131 tamamlad\u0131\u011f\u0131n\u0131zdan emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
        else:
            answer = QMessageBox.question(
                self,
                "Pilot Da\u011f\u0131t\u0131m Onay\u0131",
                f"{version} s\u00fcr\u00fcm\u00fc {len(targets)} pilot firmaya g\u00f6nderilsin mi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._status.setText("Da\u011f\u0131t\u0131m komutlar\u0131 olu\u015fturuluyor...")
        worker = _DeployUpdate(version, targets, changelog, channel)
        worker.done.connect(self._deploy_done)
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _deploy_done(self, result: dict):
        targets = result.get("targets", "all")
        target_text = "t\u00fcm firmalar" if targets == "all" else f"{len(targets)} firma"
        deployment_id = result.get("deployment_id") or result.get("job_id") or "-"
        server_status = result.get("status") or "Queued"
        self._telemetry_status.setText(
            f"Sunucu durumu: {server_status}  |  Dagitim kimligi: {deployment_id}"
        )
        self._telemetry_log.setPlainText(json.dumps(result, ensure_ascii=True, indent=2))
        self._status.setText(
            f"\u2713 {result.get('version', '')} s\u00fcr\u00fcm\u00fc {target_text} i\u00e7in kuyru\u011fa al\u0131nd\u0131."
        )

