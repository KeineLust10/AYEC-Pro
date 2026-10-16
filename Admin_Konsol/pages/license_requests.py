"""Admin approval page for manually verified license payments."""
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QScrollArea,
    QHeaderView, QFrame, QGridLayout, QMessageBox, QSizePolicy, QProgressBar, QApplication,
)
from datetime import date, datetime, timezone

import api_client
from product_catalog import product_code


class _MetricSparkline(QWidget):
    def __init__(self, color, points, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._points = points
        self.setFixedSize(58, 28)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        width = max(1, self.width() - 4)
        height = max(1, self.height() - 6)
        for index, value in enumerate(self._points):
            point = (2 + width * index / (len(self._points) - 1), 3 + height * (1 - value))
            if index == 0:
                path.moveTo(*point)
            else:
                path.lineTo(*point)
        painter.setPen(QPen(self._color, 2))
        painter.drawPath(path)


class _CopyButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("remoteActionBtn")
        self.setFixedWidth(26)
        self.setAccessibleName("Copy license key")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#dee2f6"))
        painter.setBrush(QColor("#303444"))
        painter.drawRoundedRect(7, 8, 10, 12, 1, 1)
        painter.drawRoundedRect(10, 5, 10, 12, 1, 1)
        painter.end()


class _OrdersWorker(QThread):
    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, status, product_code=''):
        super().__init__()
        self.status = status
        self.product_code = product_code

    def run(self):
        try:
            self.done.emit(api_client.license_orders(self.status, self.product_code))
        except Exception as error:
            self.failed.emit(str(error))


class _LicensesWorker(QThread):
    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, product_code_value=""):
        super().__init__()
        self.product_code_value = product_code_value

    def run(self):
        try:
            licenses = api_client.licenses(self.product_code_value)
            try:
                live_rows = api_client.live_status()
            except Exception:
                live_rows = []
            live_by_tenant = {
                str(row.get("id")): row
                for row in live_rows or []
                if isinstance(row, dict) and row.get("id") is not None
            }
            for license_data in licenses or []:
                if not isinstance(license_data, dict):
                    continue
                telemetry = live_by_tenant.get(str(license_data.get("tenant_id") or ""))
                if telemetry:
                    license_data["online"] = bool(telemetry.get("online"))
                    license_data["active_users"] = int(telemetry.get("active_users") or 0)
                    license_data["last_seen"] = str(telemetry.get("last_seen") or "")
            self.done.emit(licenses)
        except Exception as error:
            self.failed.emit(str(error))


class _ProvisionInvitesWorker(QThread):
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.provision_invites())
        except Exception as error:
            self.failed.emit(str(error))


class _DecisionWorker(QThread):
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, order_id, approved, note, plan_code=""):
        super().__init__()
        self.order_id = order_id
        self.approved = approved
        self.note = note
        self.plan_code = plan_code

    def run(self):
        try:
            if self.approved:
                self.done.emit(api_client.approve_license_order(self.order_id, self.note, self.plan_code))
            else:
                self.done.emit(api_client.reject_license_order(self.order_id, self.note))
        except Exception as error:
            self.failed.emit(str(error))


class _CancelWorker(QThread):
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, order_id, note):
        super().__init__()
        self.order_id = int(order_id)
        self.note = str(note or "")

    def run(self):
        try:
            self.done.emit(api_client.cancel_license_order(self.order_id, self.note))
        except Exception as error:
            self.failed.emit(str(error))


class LicenseRequestsPage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.orders = []
        self.worker = None
        self.licenses = []
        self.license_worker = None
        self.invite_worker = None
        self._build()
        self.reload()

    def _build(self):
        self.setObjectName("licenseRequestsPage")
        self.setStyleSheet("""
            QWidget#licenseRequestsPage { background: #0e1321; color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
            QWidget#licenseRequestsPage QLabel { background: transparent; color: #dee2f6; }
            QWidget#licenseContent, QScrollArea#licenseScroll, QScrollArea#licenseScroll QWidget#qt_scrollarea_viewport { background: #0e1321; }
            QFrame#licensePanel { background: #161b2a; border: 1px solid #424754; border-radius: 6px; }
            QFrame#licenseHero { background: #1a1f2e; border: 1px solid #252a39; border-radius: 6px; }
            QFrame#licenseProductContext { background: #252a39; border: none; border-radius: 4px; }
            QLabel#licenseProductName { color: #dee2f6; font-size: 16px; font-weight: 700; }
            QLabel#licenseProductMeta { color: #4edea3; font: 700 10px 'Segoe UI', Arial; }
            QLabel#pageTitle { color: #dee2f6; font-size: 28px; font-weight: 700; }
            QLabel#licenseHsmBadge { color: #adc6ff; background: rgba(77,142,255,0.2); border-radius: 12px; padding: 3px 8px; font: 700 9px 'Segoe UI', Arial; }
            QLabel#licensePageSubtitle { color: #c2c6d6; font-size: 12px; }
            QLabel#licenseMetricTitle { color: #8c909f; font-family: 'Segoe UI', Arial; font-size: 10px; font-weight: 700; }
            QLabel#licenseMetricValue { color: #dee2f6; font-size: 28px; font-weight: 700; }
            QLineEdit#licenseSearch { background: #252a39; border: 1px solid #424754; border-radius: 3px; padding: 7px 9px; color: #dee2f6; min-width: 210px; }
            QFrame#detailCard, QFrame#formCard, QFrame#metricCard { background: #161b2a; border: 1px solid #424754; border-radius: 6px; }
            QFrame#metricCard { min-height: 0px; }
            QFrame#licenseInventoryPanel { background: #161b2a; border: 1px solid #252a39; border-radius: 6px; }
            QWidget#licenseInventoryHeader { background: #1c2231; }
            QLabel#licenseInventoryFooter { color: #8c909f; background: #161b2a; padding: 4px 12px; font: 700 9px 'Segoe UI', Arial; }
            QLabel#inventoryCount { background: #090e1c; color: #adc6ff; border-radius: 10px; padding: 3px 8px; font: 700 9px 'Segoe UI', Arial; }
            QFrame#requestCard { background: #1a1f2e; border: 1px solid #252a39; border-top: 3px solid #4cd7f6; border-radius: 10px; }
            QFrame#queueDock { background: #161b2a; border: none; border-radius: 10px; }
            QFrame#queueIcon { background: #93000a; border: none; border-radius: 7px; }
            QLabel#queueBadge { background: #303444; color: #ffb4ab; border-radius: 12px; padding: 5px 12px; font-size: 10px; font-weight: 700; }
            QLabel#requestCompany { color: #dee2f6; font-size: 16px; font-weight: 700; }
            QLabel#requestMeta { color: #4cd7f6; font-family: 'Segoe UI', Arial; font-size: 10px; font-weight: 600; }
            QLabel#requestDetail { color: #c2c6d6; background: #0e1321; border-radius: 4px; padding: 10px; }
            QLabel#cardDetail { color: #8c909f; font-family: 'Segoe UI', Arial; font-size: 10px; }
            QLabel#panelTitle { color: #dee2f6; font-size: 15px; font-weight: 700; }
            QComboBox#combo { background: #0d1b30; color: #edf4ff; border: 1px solid #365779; border-radius: 8px; padding: 7px 10px; min-width: 140px; }
            QPushButton#primaryBtn { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4d8eff,stop:0.55 #adc6ff,stop:1 #4cd7f6); color: #001a42; border: none; border-radius: 8px; padding: 0 8px; font-weight: 700; }
            QPushButton#secondaryBtn { background: #132742; color: #c8d7ea; border: 1px solid #365779; border-radius: 8px; padding: 7px 12px; }
            QPushButton#dangerBtn, QPushButton#tableDangerBtn { background: #2b1621; color: #ffb4ab; border: 1px solid #8c3942; border-radius: 8px; padding: 7px 12px; }
            QPushButton#remoteActionBtn { background: #303444; color: #dee2f6; border: none; border-radius: 4px; padding: 4px 10px; font-weight: 700; }
            QTableWidget#dataTable, QTableWidget#licenseInventoryTable { background: #090e1c; alternate-background-color: #161b2a; border: 1px solid #424754; color: #dee2f6; gridline-color: #252a39; }
            QTableWidget#dataTable::item, QTableWidget#licenseInventoryTable::item { color: #dee2f6; padding: 7px 8px; }
            QTableWidget#dataTable QHeaderView::section, QTableWidget#licenseInventoryTable QHeaderView::section { background: #090e1c; color: #8c909f; border: none; padding: 8px; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 9px; font-weight: 700; }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("licenseScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("licenseContent")
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        root = QVBoxLayout(content)
        root.setContentsMargins(4, 0, 12, 5)
        root.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("licenseHero")
        hero.setMinimumHeight(90)
        hero_layout = QGridLayout(hero)
        hero_layout.setContentsMargins(12, 10, 12, 10)
        hero_layout.setHorizontalSpacing(16)
        self._hero_layout = hero_layout
        self._hero = hero
        top = QGridLayout()
        top.setHorizontalSpacing(12)
        self._page_header = top
        product_context = QFrame()
        product_context.setObjectName("licenseProductContext")
        product_context.setFixedWidth(294)
        product_layout = QVBoxLayout(product_context)
        product_layout.setContentsMargins(12, 8, 12, 8)
        product_layout.setSpacing(3)
        product_label = QLabel("AKTIF YAZILIM KUMESI")
        product_label.setObjectName("licenseMetricTitle")
        product_name = QLabel("AYEC Pro Teknik Servis")
        product_name.setObjectName("licenseProductName")
        self._product_name_label = product_name
        product_meta = QLabel("Aktif  \u2022  4 Kayitli Firma")
        product_meta.setObjectName("licenseProductMeta")
        self._product_meta_label = product_meta
        product_layout.addWidget(product_label)
        product_layout.addWidget(product_name)
        product_layout.addWidget(product_meta)
        self._product_context = product_context
        hero_layout.addWidget(product_context, 0, 0)
        title_box = QVBoxLayout()
        title = QLabel("Lisans & Yetki Da\u011f\u0131t\u0131m \u0130stasyonu")
        title.setObjectName("pageTitle")
        title.setWordWrap(True)
        self._page_title = title
        title_row = QHBoxLayout()
        title_row.setSpacing(9)
        title_row.addWidget(title)
        hsm_badge = QLabel("HSM-VAULT v2.5")
        hsm_badge.setObjectName("licenseHsmBadge")
        title_row.addWidget(hsm_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        title_box.addLayout(title_row)
        subtitle = QLabel(
            "Donan\u0131m kilitli istemci anahtarlar\u0131, uzaktan lisans sa\u011flama ve kriptografik davet t\u00fcnel"
        )
        subtitle.setObjectName("licensePageSubtitle")
        subtitle.setWordWrap(True)
        self._page_subtitle = subtitle
        title_box.addWidget(subtitle)
        self._page_title_box = title_box
        top.addLayout(title_box, 0, 0)
        invite = QPushButton("+  Yeni Davet Kodu \u00dcret")
        invite.setObjectName("primaryBtn")
        invite.setFixedSize(226, 40)
        invite.clicked.connect(lambda: self.navigate_requested.emit("invite_codes"))
        self._invite_button = invite
        top.addWidget(invite, 0, 1)
        top.setColumnStretch(0, 1)
        hero_layout.addLayout(top, 0, 1)
        root.addWidget(hero)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.search_field = QLineEdit()
        self.search_field.setObjectName("licenseSearch")
        self.search_field.setMinimumWidth(0)
        self.search_field.setPlaceholderText("Firma, talep no veya lisans ara...")
        self.search_field.textChanged.connect(self._filter_table)
        filters.addWidget(self.search_field, 1)
        self.status_filter = QComboBox()
        self.status_filter.setObjectName("combo")
        self.status_filter.setMinimumWidth(0)
        self.status_filter.addItem("Tum talepler", "")
        self.status_filter.addItem("Odeme bildirildi", "payment_reported")
        self.status_filter.addItem("Odeme bekleniyor", "payment_pending")
        self.status_filter.addItem("Onaylandi", "approved")
        self.status_filter.addItem("Reddedildi", "rejected")
        self.status_filter.addItem("Iptal edildi", "cancelled")
        self.status_filter.currentIndexChanged.connect(self.reload)
        filters.addWidget(self.status_filter)
        refresh = QPushButton("Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self.reload)
        filters.addWidget(refresh)
        self.search_field.hide()
        self.status_filter.hide()
        refresh.hide()

        summary = QGridLayout()
        summary.setSpacing(12)
        self._summary_grid = summary
        self._metric_cards = []
        self._summary_bars = {}
        self._summary_labels = {}
        metric_colors = ("#adc6ff", "#4edea3", "#4cd7f6", "#ffb4ab")
        metric_statuses = ("+6 Bu Hafta", "Kullan\u0131ma Haz\u0131r", "%71 D\u00f6n\u00fc\u015f\u00fcm", "Kritik Yenileme")
        metric_sparks = ((.25, .45, .35, .7, .55, .82, .68, .95), (.3, .3, .42, .4, .76, .5, .84, .52), (.28, .38, .32, .62, .55, .78, .7, .96), (.85, .72, .88, .55, .75, .42, .58, .32))
        for index, (key, title_text) in enumerate((
            ("total", "\u00dcRET\u0130LEN TOPLAM KOD"),
            ("paid", "AKT\u0130F TOKEN (BEKLEYEN)"),
            ("active", "KULLANILMI\u015e / KURULMU\u015e"),
            ("pending", "S\u00dcRES\u0130 DOLAN / \u0130PTAL"),
        )):
            card = QFrame()
            card.setObjectName("metricCard")
            accent = metric_colors[index]
            card.setStyleSheet(f"QFrame#metricCard {{ background: #1a1f2e; border: none; border-bottom: 3px solid {accent}; border-radius: 10px; }}")
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(12, 10, 12, 10)
            card_lay.setSpacing(5)
            title_row = QHBoxLayout()
            title_row.setContentsMargins(0, 0, 0, 0)
            title_row.setSpacing(4)
            label = QLabel(title_text)
            label.setObjectName("licenseMetricTitle")
            title_row.addWidget(label, 1)
            title_row.addWidget(_MetricSparkline(accent, metric_sparks[index]))
            card_lay.addLayout(title_row)
            value_row = QHBoxLayout()
            value_row.setContentsMargins(0, 0, 0, 0)
            value_row.setSpacing(7)
            value = QLabel("0")
            value.setObjectName("licenseMetricValue")
            value.setStyleSheet(f"color: {accent};")
            value_row.addWidget(value, 0, Qt.AlignmentFlag.AlignVCenter)
            status = QLabel(metric_statuses[index])
            status.setStyleSheet(f"color: {accent}; font: 700 10px 'JetBrains Mono', 'Segoe UI', Arial;")
            value_row.addWidget(status, 0, Qt.AlignmentFlag.AlignVCenter)
            value_row.addStretch(1)
            card_lay.addLayout(value_row)
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(100)
            progress.setTextVisible(False)
            progress.setFixedHeight(4)
            progress.setStyleSheet(
                "QProgressBar { border: none; border-radius: 2px; background: #303444; } "
                f"QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}"
            )
            card_lay.addWidget(progress)
            card.setFixedHeight(94)
            summary.addWidget(card, 0, len(self._summary_labels))
            self._summary_labels[key] = value
            self._summary_bars[key] = progress
            self._metric_cards.append(card)
        root.addLayout(summary)
        root.addSpacing(8)

        queue_panel = QFrame()
        queue_panel.setObjectName("queueDock")
        queue_layout = QVBoxLayout(queue_panel)
        queue_layout.setContentsMargins(12, 12, 12, 13)
        queue_layout.setSpacing(9)
        queue_header = QGridLayout()
        self._queue_header = queue_header
        queue_icon = QFrame()
        queue_icon.setObjectName("queueIcon")
        queue_icon.setFixedSize(28, 28)
        queue_icon_layout = QVBoxLayout(queue_icon)
        queue_icon_layout.setContentsMargins(0, 0, 0, 0)
        queue_icon_text = QLabel("!")
        queue_icon_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        queue_icon_text.setStyleSheet("color: #ffdad6; font-weight: 700; font-size: 16px;")
        queue_icon_layout.addWidget(queue_icon_text)
        self._queue_icon = queue_icon
        queue_header.addWidget(queue_icon, 0, 0)
        queue_title_box = QVBoxLayout()
        queue_title = QLabel("Gelen Lisans Talepleri & Canl\u0131 Sipari\u015fler")
        queue_title.setObjectName("panelTitle")
        queue_title.setWordWrap(True)
        queue_caption = QLabel("Bankac\u0131l\u0131k & Sanal POS Entegrasyon Kuyru\u011fu")
        queue_caption.setObjectName("cardDetail")
        queue_title_box.addWidget(queue_title)
        queue_title_box.addWidget(queue_caption)
        self._queue_title_box = queue_title_box
        queue_header.addLayout(queue_title_box, 0, 1)
        queue_header.setColumnStretch(1, 1)
        self._queue_badge = QLabel("0 YEN\u0130 B\u0130LD\u0130R\u0130M")
        self._queue_badge.setObjectName("queueBadge")
        self._queue_badge.setWordWrap(True)
        queue_header.addWidget(self._queue_badge, 0, 2)
        queue_layout.addLayout(queue_header)

        self._cards_widget = QWidget()
        self._cards_grid = QGridLayout(self._cards_widget)
        self._cards_grid.setContentsMargins(0, 0, 0, 0)
        self._cards_grid.setSpacing(12)
        self._request_cards = []
        self._request_card_parts = []
        queue_layout.addWidget(self._cards_widget)
        root.addWidget(queue_panel)

        self.table = QTableWidget(0, 9)
        self.table.setObjectName("dataTable")
        self.table.setHorizontalHeaderLabels([
            "Talep No", "Firma", "Paket", "Tutar", "Referans",
            "Lisans Kodu", "Durum", "Tarih", "Islem",
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for column, width in ((0, 112), (1, 156), (2, 118), (3, 108),
                              (4, 128), (5, 160), (6, 116), (8, 144)):
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._show_selected)
        self.table.setMinimumHeight(120)
        self.table.setMaximumHeight(220)
        self.table.hide()

        action_card = QFrame()
        action_card.setObjectName("formCard")
        action_root = QVBoxLayout(action_card)
        action_root.setContentsMargins(18, 14, 18, 14)
        self.selection_label = QLabel("Bir lisans talebi secin.")
        self.selection_label.setObjectName("panelTitle")
        action_root.addWidget(self.selection_label)
        actions = QGridLayout()
        actions.setHorizontalSpacing(8)
        actions.setVerticalSpacing(8)
        self._action_widgets = []
        plan_label = QLabel("Onay paketi:")
        actions.addWidget(plan_label, 0, 0)
        self.plan = QComboBox()
        self.plan.setObjectName("combo")
        self.plan.setMinimumWidth(0)
        self.plan.addItem("Talepteki paket", "")
        self.plan.addItem("Aylik", "monthly")
        self.plan.addItem("6 Aylik", "six_months")
        self.plan.addItem("1 Yillik", "one_year")
        self.plan.addItem("2 Yillik", "two_years")
        self.plan.addItem("3 Yillik", "three_years")
        actions.addWidget(self.plan, 0, 1)
        note_label = QLabel("Yonetici notu:")
        actions.addWidget(note_label, 0, 2)
        self.note = QLineEdit()
        self.note.setMinimumWidth(0)
        self.note.setPlaceholderText("Odeme kontrol notu")
        actions.addWidget(self.note, 0, 3)
        self.approve = QPushButton("Lisans Uret ve Etkinlestir")
        self.approve.setObjectName("primaryBtn")
        self.approve.clicked.connect(lambda: self.decide(True))
        actions.addWidget(self.approve, 0, 4)
        self.reject = QPushButton("Talebi Reddet")
        self.reject.setObjectName("dangerBtn")
        self.reject.clicked.connect(lambda: self.decide(False))
        actions.addWidget(self.reject, 0, 5)
        self._action_widgets = [plan_label, self.plan, note_label, self.note, self.approve, self.reject]
        actions.setColumnStretch(3, 1)
        action_root.addLayout(actions)
        action_card.hide()
        self._action_card = action_card

        inventory_panel = QFrame()
        inventory_panel.setObjectName("licenseInventoryPanel")
        inventory_panel_layout = QVBoxLayout(inventory_panel)
        inventory_panel_layout.setContentsMargins(0, 0, 0, 0)
        inventory_panel_layout.setSpacing(0)
        inventory_heading = QGridLayout()
        inventory_heading_widget = QWidget()
        inventory_heading_widget.setObjectName("licenseInventoryHeader")
        inventory_heading_widget.setLayout(inventory_heading)
        inventory_heading.setContentsMargins(12, 3, 12, 19)
        inventory_heading.setHorizontalSpacing(8)
        inventory_heading.setVerticalSpacing(8)
        self._inventory_heading = inventory_heading
        inventory_title = QLabel("Lisans Envanteri")
        inventory_title.setObjectName("panelTitle")
        self._inventory_title = inventory_title
        inventory_heading.addWidget(inventory_title, 0, 0)
        inventory_count = QLabel("0 Kayit")
        inventory_count.setObjectName("inventoryCount")
        self._inventory_count = inventory_count
        inventory_heading.addWidget(inventory_count, 0, 1)
        self.inventory_search = QLineEdit()
        self.inventory_search.setObjectName("licenseSearch")
        self.inventory_search.setMinimumWidth(0)
        self.inventory_search.setPlaceholderText("Firma veya lisans anahtar\u0131 ara...")
        self.inventory_search.textChanged.connect(self._filter_inventory)
        self.inventory_heading_widgets = [inventory_title, inventory_count, self.inventory_search]
        inventory_refresh = QPushButton("Yenile")
        inventory_refresh.setObjectName("secondaryBtn")
        inventory_refresh.clicked.connect(self._load_licenses)
        self._inventory_refresh = inventory_refresh
        self.inventory_heading_widgets.append(inventory_refresh)
        inventory_heading.addWidget(self.inventory_search, 0, 2)
        inventory_heading.addWidget(inventory_refresh, 0, 3)
        inventory_heading.setColumnStretch(2, 1)
        inventory_panel_layout.addWidget(inventory_heading_widget)

        self.inventory_table = QTableWidget(0, 7)
        self.inventory_table.setObjectName("licenseInventoryTable")
        self.inventory_table.setHorizontalHeaderLabels([
            "F\u0130RMA / BAY\u0130 B\u0130LG\u0130S\u0130", "MOD\u00dcL YETK\u0130", "KR\u0130PTOGRAF\u0130K\nL\u0130SANS ANAHTARI",
            "L\u0130SANS T\u00dcR\u00dc", "KALAN S\u00dcRE /\nPER\u0130YOT", "TELEMETR\u0130 &\nP\u0130NG", "UZAKTAN\nEYLEM",
        ])
        inventory_header = self.inventory_table.horizontalHeader()
        inventory_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._inventory_column_weights = (210, 160, 175, 145, 175, 175, 90)
        self.inventory_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.inventory_table.setWordWrap(True)
        self.inventory_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.inventory_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.inventory_table.verticalHeader().setVisible(False)
        self.inventory_table.verticalHeader().setDefaultSectionSize(68)
        inventory_header.setFixedHeight(52)
        self.inventory_table.setMinimumHeight(180)
        inventory_panel_layout.addWidget(self.inventory_table, 1)
        self.status_label = QLabel("")
        self.status_label.setObjectName("licenseInventoryFooter")
        self.status_label.setMinimumHeight(26)
        inventory_panel_layout.addWidget(self.status_label)
        root.addWidget(inventory_panel, 1)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        QTimer.singleShot(0, self._layout_inventory_columns)

    def reload(self):
        worker = _OrdersWorker(self.status_filter.currentData(), getattr(self, 'product_code', ''))
        worker.done.connect(self.populate)
        worker.failed.connect(lambda error: self.status_label.setText(f"Hata: {error}"))
        worker.start()
        self.worker = worker
        self._load_licenses()
        self._load_provision_invites()

    def _load_provision_invites(self):
        worker = _ProvisionInvitesWorker()
        worker.done.connect(self._populate_invite_metrics)
        worker.failed.connect(lambda _error: self._populate_invite_metrics({"invites": []}))
        worker.start()
        self.invite_worker = worker

    def _populate_invite_metrics(self, payload):
        invites = [item for item in (payload.get("invites") or []) if isinstance(item, dict)]
        now = datetime.now(timezone.utc)
        active_count = 0
        used_count = 0
        expired_count = 0
        for item in invites:
            try:
                expiry = datetime.fromisoformat(str(item.get("expires_at") or "").replace("Z", "+00:00"))
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                expired = expiry <= now
            except ValueError:
                expired = True
            revoked = bool(item.get("revoked_at"))
            used = int(item.get("use_count") or 0) >= int(item.get("max_uses") or 0)
            if revoked or expired:
                expired_count += 1
            elif used:
                used_count += 1
            else:
                active_count += 1
        counts = {
            "total": len(invites),
            "paid": active_count,
            "active": used_count,
            "pending": expired_count,
        }
        for key, value in counts.items():
            self._summary_labels[key].setText(str(value))
            self._summary_bars[key].setValue(round(value * 100 / len(invites)) if invites else 0)

    def set_product_filter(self, product_name: str):
        self.product_code = product_code(product_name)
        product_labels = {
            "teknik_servis": "AYEC Pro Teknik Servis",
            "otomotiv": "AYEC Pro Otomotiv Servis",
            "muhasebe": "AYEC Pro Muhasebe & Finans",
            "saha": "AYEC Pro Saha & Lojistik",
        }
        product_label = product_labels.get(self.product_code, "")
        if product_label:
            self._product_name_label.setText(product_label)
        self._inventory_title.setText(
            f"{product_label} \u2014 Lisans Envanteri" if product_label else "Lisans Envanteri"
        )
        self.reload()

    def _load_licenses(self):
        worker = _LicensesWorker(getattr(self, "product_code", ""))
        worker.done.connect(self.populate_inventory)
        worker.failed.connect(lambda error: self.status_label.setText(f"Hata: {error}"))
        worker.start()
        self.license_worker = worker

    def populate_inventory(self, licenses):
        self.licenses = list(licenses or [])
        company_ids = {
            str(item.get("tenant_id") or item.get("company_name") or "")
            for item in self.licenses
        }
        company_ids.discard("")
        self._product_meta_label.setText(
            f"Aktif  \u2022  {len(company_ids)} Kayitli Firma"
        )
        self._inventory_count.setText(f"{len(self.licenses)} Kayit")
        self.inventory_table.setRowCount(0)
        for license_data in self.licenses:
            row = self.inventory_table.rowCount()
            self.inventory_table.insertRow(row)
            status = str(license_data.get("status") or "-")
            license_type = str(license_data.get("license_type") or "-")
            end_date = str(license_data.get("license_end") or "").strip()
            if license_type.casefold() in {"lifetime", "omur boyu"}:
                remaining = "\u00d6m\u00fcr Boyu"
            elif end_date:
                try:
                    remaining_days = (date.fromisoformat(end_date[:10]) - date.today()).days
                    remaining = "S\u00fcresi Doldu" if remaining_days < 0 else f"{remaining_days} g\u00fcn"
                except ValueError:
                    remaining = end_date
            else:
                remaining = "-"
            product_names = {
                "teknik_servis": "Teknik Servis Core + GSM",
                "otomotiv": "Teknik Servis ODB Entegre",
                "muhasebe": "Muhasebe & Finans",
                "saha": "Saha & Lojistik",
            }
            license_type_names = {
                "three_years": "3 Y\u0131ll\u0131k Kurumsal",
                "lifetime": "Lifetime S\u0131n\u0131rs\u0131z",
                "one_year_pro": "1 Y\u0131ll\u0131k Pro",
                "pilot": "15 G\u00fcnl\u00fck Pilot",
            }
            product = str(license_data.get("product_code") or "-")
            company_name = str(license_data.get("company_name") or "-")
            company_details = [
                str(license_data.get(key) or "").strip()
                for key in ("branch_name", "city")
                if str(license_data.get(key) or "").strip()
            ]
            company_display = company_name
            if company_details:
                company_display += "\n" + "  \u2022  ".join(company_details)
            updated = str(license_data.get("license_updated_at") or "")
            values = [
                company_display,
                product_names.get(product, product.replace("_", " ").title()),
                license_data.get("license_code", "-"),
                license_type_names.get(license_type.casefold(), license_type),
                remaining,
                (
                    f"{'ONLINE' if license_data.get('online') else 'OFFLINE'}  \u2022  "
                    f"{int(license_data.get('active_users') or 0)} oturum"
                    if "online" in license_data
                    else f"{status}  \u2022  {updated or 'G\u00fcncelleme bilgisi yok'}"
                ),
                "",
            ]
            for column, value in enumerate(values):
                cell_text = str(value)
                cell = QTableWidgetItem("" if column in {0, 2, 4, 5, 6} else cell_text)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, cell_text)
                if column in {2, 4, 5, 6}:
                    cell.setData(Qt.ItemDataRole.UserRole, cell_text)
                if column == 2:
                    cell.setToolTip(str(value))
                self.inventory_table.setItem(row, column, cell)
            company_cell = QWidget()
            company_cell_layout = QHBoxLayout(company_cell)
            company_cell_layout.setContentsMargins(8, 4, 4, 4)
            company_cell_layout.setSpacing(10)
            initials = "".join(part[:1] for part in company_name.split()[:2]).upper() or "--"
            company_avatar = QLabel(initials)
            company_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            company_avatar.setFixedSize(32, 32)
            company_avatar.setStyleSheet("background: #303444; color: #adc6ff; border-radius: 4px; font: 700 11px 'Segoe UI', Arial;")
            company_text = QVBoxLayout()
            company_text.setContentsMargins(0, 0, 0, 0)
            company_text.setSpacing(2)
            company_title = QLabel(company_name)
            company_title.setWordWrap(True)
            company_title.setStyleSheet("color: #dee2f6; font-size: 12px; font-weight: 700;")
            company_meta = QLabel("  \u2022  ".join(company_details) if company_details else product_names.get(product, product))
            company_meta.setWordWrap(True)
            company_meta.setStyleSheet("color: #8c909f; font: 10px 'Segoe UI', Arial;")
            company_text.addWidget(company_title)
            company_text.addWidget(company_meta)
            company_cell_layout.addWidget(company_avatar)
            company_cell_layout.addLayout(company_text, 1)
            self.inventory_table.setCellWidget(row, 0, company_cell)
            key_text = str(license_data.get("license_code") or "-")
            key_cell = QWidget()
            key_layout = QHBoxLayout(key_cell)
            key_layout.setContentsMargins(4, 4, 4, 4)
            key_layout.setSpacing(4)
            key_label = QLabel(key_text)
            key_label.setToolTip(key_text)
            key_label.setStyleSheet("background: #090e1c; color: #4cd7f6; padding: 5px; border-radius: 3px; font-family: 'Segoe UI', Arial; font-size: 9px;")
            key_layout.addWidget(key_label, 1)
            copy_button = _CopyButton()
            copy_button.setAccessibleName("Lisans anahtar\u0131n\u0131 kopyala")
            copy_button.clicked.connect(lambda _, code=key_text: self._copy_license_code(code))
            key_layout.addWidget(copy_button)
            self.inventory_table.setCellWidget(row, 2, key_cell)
            remaining_cell = QWidget()
            remaining_layout = QVBoxLayout(remaining_cell)
            remaining_layout.setContentsMargins(4, 4, 6, 4)
            remaining_layout.setSpacing(3)
            remaining_label = QLabel(remaining)
            remaining_label.setStyleSheet("color: #dee2f6; font-family: 'Segoe UI', Arial; font-size: 10px; font-weight: 700;")
            remaining_layout.addWidget(remaining_label)
            remaining_bar = QProgressBar()
            remaining_bar.setRange(0, 100)
            remaining_bar.setTextVisible(False)
            remaining_bar.setFixedHeight(4)
            if license_type.casefold() in {"lifetime", "omur boyu"}:
                remaining_pct = 100
            else:
                try:
                    start_date = date.fromisoformat(str(license_data.get("license_start") or "")[:10])
                    end_date_value = date.fromisoformat(end_date[:10])
                    total_days = max(1, (end_date_value - start_date).days)
                    remaining_pct = max(0, min(100, round((end_date_value - date.today()).days * 100 / total_days)))
                except ValueError:
                    remaining_pct = 0
            remaining_bar.setValue(remaining_pct)
            remaining_bar.setStyleSheet("QProgressBar { border: none; border-radius: 2px; background: #303444; } QProgressBar::chunk { background: #adc6ff; border-radius: 2px; }")
            remaining_layout.addWidget(remaining_bar)
            self.inventory_table.setCellWidget(row, 4, remaining_cell)
            telemetry_widget = QWidget()
            telemetry_layout = QHBoxLayout(telemetry_widget)
            telemetry_layout.setContentsMargins(6, 0, 4, 0)
            telemetry_layout.setSpacing(7)
            telemetry_dot = QFrame()
            online = bool(license_data.get("online"))
            telemetry_dot.setFixedSize(8, 8)
            telemetry_dot.setStyleSheet(
                f"background: {'#4edea3' if online else '#ffb4ab'}; border-radius: 4px;"
            )
            telemetry_layout.addWidget(telemetry_dot)
            telemetry_label = QLabel(
                f"{'ONLINE' if online else 'OFFLINE'}  ({int(license_data.get('active_users') or 0)})"
                if "online" in license_data
                else "PING --"
            )
            telemetry_label.setStyleSheet(
                f"color: {'#4edea3' if online else '#ffb4ab'}; font-family: 'Segoe UI', Arial; font-size: 9px; font-weight: 700;"
            )
            telemetry_layout.addWidget(telemetry_label)
            telemetry_layout.addStretch(1)
            telemetry_widget.setToolTip(str(license_data.get("last_seen") or "Canli oturum verisi"))
            self.inventory_table.setCellWidget(row, 5, telemetry_widget)
            action = QPushButton("\u22ee")
            action.setObjectName("remoteActionBtn")
            action.setToolTip("Lisans telemetri ayr\u0131nt\u0131lar\u0131")
            action.setAccessibleName(f"{license_data.get('company_name') or '-'} lisans ayr\u0131nt\u0131lar\u0131")
            action.clicked.connect(lambda _, current=dict(license_data): self._show_license_details(current))
            self.inventory_table.setCellWidget(row, 6, action)
            self.inventory_table.setRowHeight(row, 68)
            key_item = self.inventory_table.item(row, 2)
            if key_item is not None:
                key_item.setForeground(Qt.GlobalColor.cyan)
                key_item.setFont(QFont("Segoe UI", 9))
        self._filter_inventory(self.inventory_search.text())
        live_count = sum(1 for item in self.licenses if "online" in item)
        self.status_label.setText(
            f"{len(self.orders)} lisans talebi listelendi.  "
            f"Canl\u0131 telemetri: {live_count}/{len(self.licenses)} firma."
        )

    def _show_license_details(self, license_data):
        company = str(license_data.get("company_name") or "-")
        code = str(license_data.get("license_code") or "-")
        status = str(license_data.get("status") or "-")
        self.status_label.setText(f"{company}  |  {code}  |  {status}")

    def _copy_license_code(self, code):
        QApplication.clipboard().setText(str(code or ""))
        self.status_label.setText("Lisans anahtar\u0131 panoya kopyaland\u0131.")

    def _filter_inventory(self, query: str):
        needle = str(query or "").strip().casefold()
        for row in range(self.inventory_table.rowCount()):
            values = [
                f"{self.inventory_table.item(row, column).text()} {self.inventory_table.item(row, column).data(Qt.ItemDataRole.UserRole) or ''}"
                for column in range(self.inventory_table.columnCount())
                if self.inventory_table.item(row, column) is not None
            ]
            self.inventory_table.setRowHidden(
                row, bool(needle) and needle not in " ".join(values).casefold()
            )

    def populate(self, orders):
        self.orders = orders
        self.table.setRowCount(0)
        for card in self._request_cards:
            card.deleteLater()
        self._request_cards = []
        self._request_card_parts = []
        pending_count = 0
        for order in orders:
            row = self.table.rowCount()
            self.table.insertRow(row)
            amount = float(order.get("amount_try") or 0)
            values = [
                order.get("request_no", "-"),
                order.get("company_name", "-"),
                order.get("plan_label", "-"),
                f"{amount:,.2f} TRY",
                order.get("payment_reference", "-"),
                order.get("license_code", "-") or "-",
                order.get("status", "-"),
                order.get("created_at", "-"),
                "",
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, int(order.get("id") or 0))
            self.table.item(row, 1).setToolTip(
                f"Yetkili: {order.get('requester_name') or '-'}\n"
                f"Konum: {order.get('location_json') or 'Konum bilgisi yok'}"
            )
            status = str(order.get("status") or "")
            cancel_button = QPushButton(
                "Iptal Edildi" if status == "cancelled" else "Lisansi Iptal Et"
            )
            cancel_button.setObjectName("tableDangerBtn")
            cancel_button.setEnabled(status == "active")
            cancel_button.clicked.connect(
                lambda _, current=dict(order): self.cancel_license(current)
            )
            self.table.setCellWidget(row, 8, cancel_button)
            self._request_cards.append(self._build_request_card(order, row, amount))
            if status in {"payment_pending", "payment_reported"}:
                pending_count += 1
        self._queue_badge.setText(f"{pending_count} YEN\u0130 B\u0130LD\u0130R\u0130M \u2014 \u0130NCELEME BEKL\u0130YOR")
        self.status_label.setText(f"{len(orders)} lisans talebi listelendi.")
        if orders:
            self.table.selectRow(0)
        else:
            self.selection_label.setText("Bir lisans talebi secin.")
        self._filter_table()
        self._layout_request_cards()

    def _build_request_card(self, order, row, amount):
        card = QFrame()
        card.setObjectName("requestCard")
        card.setMinimumHeight(216)
        accent = "#00a572" if row % 2 == 0 else "#03b5d3"
        card.setStyleSheet(
            "QFrame#requestCard { background: #1a1f2e; border: 1px solid #252a39; "
            f"border-top: 3px solid {accent}; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        heading = QGridLayout()
        heading.setSpacing(10)
        initials = "".join(part[:1] for part in str(order.get("company_name") or "-").split()[:2]).upper()
        avatar = QLabel(initials or "--")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(38, 38)
        avatar.setStyleSheet(f"background: #303444; color: {accent}; border-radius: 7px; font-size: 15px; font-weight: 700;")
        heading.addWidget(avatar, 0, 0)
        company_box = QVBoxLayout()
        company_box.setSpacing(2)
        company = QLabel(str(order.get("company_name") or "-"))
        company.setObjectName("requestCompany")
        company.setWordWrap(True)
        request_id = QLabel(f"#{order.get('request_no') or '-'}")
        request_id.setObjectName("cardDetail")
        company_box.addWidget(company)
        company_box.addWidget(request_id)
        heading.addLayout(company_box, 0, 1)
        payment = str(order.get("payment_note") or "")
        if not payment:
            payment = {
                "payment_reported": "Banka havalesi bildirildi",
                "payment_pending": "\u00d6deme onay\u0131 bekleniyor",
                "active": "Lisans etkinle\u015ftirildi",
                "approved": "Talep onayland\u0131",
                "rejected": "Talep reddedildi",
                "cancelled": "Talep iptal edildi",
            }.get(str(order.get("status") or ""), str(order.get("status") or "-"))
        status_label = QLabel(payment)
        status_label.setObjectName("requestMeta")
        status_label.setWordWrap(True)
        heading.addWidget(status_label, 0, 2)
        amount_box = QVBoxLayout()
        amount_box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        amount_label = QLabel(f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " \u20ba")
        amount_label.setStyleSheet(f"color: {accent}; font-size: 18px; font-weight: 700;")
        plan_label = QLabel(f"Paket: {order.get('plan_label') or '-'}")
        plan_label.setObjectName("cardDetail")
        amount_box.addWidget(amount_label)
        amount_box.addWidget(plan_label)
        heading.addLayout(amount_box, 0, 3)
        heading.setColumnStretch(1, 1)
        layout.addLayout(heading)
        detail = QLabel(str(order.get("description") or order.get("note") or order.get("payment_reference") or "License request received."))
        detail.setObjectName("requestDetail")
        detail.setWordWrap(True)
        detail.setFixedHeight(60)
        layout.addWidget(detail)
        layout.addStretch(1)
        footer = QGridLayout()
        footer.setHorizontalSpacing(8)
        footer.setVerticalSpacing(8)
        client_text = order.get("requester_email") or order.get("requester_name") or "-"
        client = QLabel(f"\u0130stemci: {client_text}  \u2022  {order.get('created_at') or '-'}")
        client.setObjectName("cardDetail")
        client.setWordWrap(True)
        footer.addWidget(client, 0, 0, 1, 4)
        reject = QPushButton("Reddet")
        reject.setObjectName("requestRejectBtn")
        reject.setStyleSheet("background: #303444; color: #c2c6d6; border: none; border-radius: 6px; padding: 7px 12px;")
        reject.setProperty("requestAction", "reject")
        reject.clicked.connect(lambda _, current=row: self._decide_request(current, False))
        footer.addWidget(reject, 0, 1)
        select = QPushButton("\u00d6nizle")
        select.setObjectName("requestPreviewBtn")
        select.setStyleSheet("background: #303444; color: #dee2f6; border: none; border-radius: 6px; padding: 7px 12px;")
        select.setProperty("requestAction", "preview")
        select.clicked.connect(lambda _, current=row: self._select_request(current))
        footer.addWidget(select, 0, 2)
        approve = QPushButton("Lisans\u0131 Derle & G\u00f6nder")
        approve.setObjectName("requestApproveBtn")
        approve.setProperty("requestAction", "approve")
        approve.setStyleSheet(f"background: {accent}; color: #002113; border: none; font-weight: 700;")
        approve.clicked.connect(lambda _, current=row: self._decide_request(current, True))
        footer.addWidget(approve, 0, 3)
        layout.addLayout(footer)
        self._request_card_parts.append((heading, avatar, company_box, status_label, amount_box, footer, client, reject, select, approve))
        return card

    def _decide_request(self, row, approved):
        self._select_request(row)
        self.decide(approved)

    def _layout_request_cards(self, available_width=None):
        while self._cards_grid.count():
            self._cards_grid.takeAt(0)
        width = self.width() if available_width is None else int(available_width)
        columns = 2 if width >= 760 else 1
        for index, card in enumerate(self._request_cards):
            self._cards_grid.addWidget(card, index // columns, index % columns)
        self._layout_request_card_controls()
        row_count = (len(self._request_cards) + columns - 1) // columns
        self._cards_widget.setMinimumHeight(max(120, row_count * 208 + max(0, row_count - 1) * self._cards_grid.verticalSpacing()))

    def _layout_request_card_controls(self):
        compact = self.width() < 700
        for parts in self._request_card_parts:
            heading, avatar, company_box, status, amount, footer, client, reject, preview, approve = parts
            heading.removeWidget(avatar)
            heading.removeItem(company_box)
            heading.removeWidget(status)
            heading.removeItem(amount)
            footer.removeWidget(client)
            footer.removeWidget(reject)
            footer.removeWidget(preview)
            footer.removeWidget(approve)
            if compact:
                heading.addWidget(avatar, 0, 0, 2, 1)
                heading.addLayout(company_box, 0, 1, 2, 1)
                heading.addLayout(amount, 2, 0, 1, 2)
                heading.addWidget(status, 3, 0, 1, 2)
                amount.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                footer.addWidget(client, 0, 0, 1, 2)
                footer.addWidget(reject, 1, 0)
                footer.addWidget(preview, 1, 1)
                footer.addWidget(approve, 2, 0, 1, 2)
                footer.setColumnStretch(0, 1)
                footer.setColumnStretch(1, 1)
            else:
                heading.addWidget(avatar, 0, 0)
                heading.addLayout(company_box, 0, 1)
                heading.addWidget(status, 0, 2)
                heading.addLayout(amount, 0, 3)
                amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
                footer.addWidget(client, 0, 0)
                footer.addWidget(reject, 0, 1)
                footer.addWidget(preview, 0, 2)
                footer.addWidget(approve, 0, 3)
                footer.setColumnStretch(0, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_request_cards"):
            self._layout_request_cards()
        if hasattr(self, "_metric_cards"):
            self._layout_metric_cards()
        if hasattr(self, "_page_header"):
            self._layout_hero()
            self._layout_page_header()
        if hasattr(self, "_queue_header"):
            self._layout_queue_header()
        if hasattr(self, "inventory_heading_widgets"):
            self._layout_inventory_heading()
            QTimer.singleShot(0, self._layout_inventory_columns)
        if hasattr(self, "_action_widgets"):
            self._layout_action_controls()
            compact = self.width() < 900
            self._page_title.setWordWrap(compact)
            self._page_subtitle.setWordWrap(compact)

    def _layout_inventory_columns(self):
        if not hasattr(self, "_inventory_column_weights"):
            return
        available = self.inventory_table.viewport().width()
        if available <= 0:
            return
        total = sum(self._inventory_column_weights)
        widths = [available * weight // total for weight in self._inventory_column_weights]
        widths[-1] += available - sum(widths)
        for column, width in enumerate(widths):
            self.inventory_table.setColumnWidth(column, width)

    def _layout_action_controls(self):
        layout = self.approve.parentWidget().layout()
        if not isinstance(layout, QGridLayout):
            return
        for widget in self._action_widgets:
            layout.removeWidget(widget)
        if self.width() < 900:
            positions = ((0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1))
        else:
            positions = ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5))
        for widget, (row, column) in zip(self._action_widgets, positions):
            layout.addWidget(widget, row, column)
        layout.setColumnStretch(1, 1 if self.width() < 900 else 0)
        layout.setColumnStretch(3, 1 if self.width() >= 900 else 0)

    def _layout_metric_cards(self):
        layout = self._summary_grid
        while layout.count():
            layout.takeAt(0)
        width = self.width()
        columns = 4 if width >= 1050 else 2 if width >= 600 else 1
        for index, card in enumerate(self._metric_cards):
            layout.addWidget(card, index // columns, index % columns)

    def _layout_inventory_heading(self):
        layout = self._inventory_heading
        for widget in self.inventory_heading_widgets:
            layout.removeWidget(widget)
        if self.width() < 900:
            layout.addWidget(self._inventory_title, 0, 0)
            layout.addWidget(self._inventory_count, 0, 1)
            layout.addWidget(self.inventory_search, 1, 0)
            layout.addWidget(self._inventory_refresh, 1, 1)
            layout.setColumnStretch(0, 1)
        else:
            layout.addWidget(self._inventory_title, 0, 0)
            layout.addWidget(self._inventory_count, 0, 1)
            layout.addWidget(self.inventory_search, 0, 2)
            layout.addWidget(self._inventory_refresh, 0, 3)
            layout.setColumnStretch(2, 1)

    def _layout_page_header(self):
        layout = self._page_header
        layout.removeItem(self._page_title_box)
        layout.removeWidget(self._invite_button)
        if self.width() < 700:
            layout.addLayout(self._page_title_box, 0, 0, 1, 2)
            layout.addWidget(self._invite_button, 1, 0, 1, 2)
            layout.setColumnStretch(0, 1)
        else:
            layout.addLayout(self._page_title_box, 0, 0)
            layout.addWidget(self._invite_button, 0, 1)
            layout.setColumnStretch(0, 1)

    def _layout_hero(self):
        layout = self._hero_layout
        layout.removeWidget(self._product_context)
        layout.removeItem(self._page_header)
        if self.width() < 900:
            self._hero.setMinimumHeight(0)
            layout.addWidget(self._product_context, 0, 0, 1, 2)
            layout.addLayout(self._page_header, 1, 0, 1, 2)
        else:
            self._hero.setMinimumHeight(90)
            layout.addWidget(self._product_context, 0, 0)
            layout.addLayout(self._page_header, 0, 1)
            layout.setColumnStretch(1, 1)

    def _layout_queue_header(self):
        layout = self._queue_header
        layout.removeWidget(self._queue_icon)
        layout.removeItem(self._queue_title_box)
        layout.removeWidget(self._queue_badge)
        if self.width() < 700:
            layout.addWidget(self._queue_icon, 0, 0)
            layout.addLayout(self._queue_title_box, 0, 1)
            layout.addWidget(self._queue_badge, 1, 0, 1, 2)
            layout.setColumnStretch(1, 1)
        else:
            layout.addWidget(self._queue_icon, 0, 0)
            layout.addLayout(self._queue_title_box, 0, 1)
            layout.addWidget(self._queue_badge, 0, 2)
            layout.setColumnStretch(1, 1)

    def _select_request(self, row):
        self.table.selectRow(row)
        self._show_selected()

    def _filter_table(self):
        query = self.search_field.text().strip().casefold()
        for row in range(self.table.rowCount()):
            match = not query or any(query in (self.table.item(row, column).text().casefold() if self.table.item(row, column) else "") for column in range(8))
            self.table.setRowHidden(row, not match)
            if row < len(self._request_cards):
                self._request_cards[row].setVisible(match)

    def _show_selected(self):
        row = self.table.currentRow()
        if row < 0:
            self.selection_label.setText("Bir lisans talebi secin.")
            return
        company = self.table.item(row, 1).text() if self.table.item(row, 1) else "-"
        plan = self.table.item(row, 2).text() if self.table.item(row, 2) else "-"
        status = self.table.item(row, 6).text() if self.table.item(row, 6) else "-"
        self.selection_label.setText(
            f"Secili talep: {company}  |  {plan}  |  Durum: {status}"
        )

    def selected_order_id(self):
        row = self.table.currentRow()
        if row < 0 or not self.table.item(row, 0):
            return 0
        return int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) or 0)

    def cancel_license(self, order):
        if str(order.get("status") or "") != "active":
            self.status_label.setText("Yalnizca aktif bir lisans iptal edilebilir.")
            return
        company = str(order.get("company_name") or "-")
        answer = QMessageBox.question(
            self,
            "Lisans Iptali",
            f"{company} firmasinin lisansi iptal edilsin mi?\n\n"
            "Firma programda islem yapamayacak ve masaustune iptal bildirimi gonderilecek.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        note = self.note.text().strip() or "Yonetim panelinden iptal edildi."
        worker = _CancelWorker(int(order.get("id") or 0), note)
        worker.done.connect(self._cancel_done)
        worker.failed.connect(lambda error: self.status_label.setText(f"Hata: {error}"))
        worker.start()
        self.worker = worker

    def _cancel_done(self, _result):
        self.note.clear()
        self.status_label.setText("Lisans iptal edildi ve masaustune bildirim gonderildi.")
        self.reload()

    def decide(self, approved):
        order_id = self.selected_order_id()
        if not order_id:
            self.status_label.setText("Lutfen bir lisans talebi secin.")
            return
        worker = _DecisionWorker(
            order_id,
            approved,
            self.note.text().strip(),
            self.plan.currentData() if approved else "",
        )
        worker.done.connect(lambda result: self._decision_done(approved, result))
        worker.failed.connect(lambda error: self.status_label.setText(f"Hata: {error}"))
        worker.start()
        self.worker = worker

    def _decision_done(self, approved, result=None):
        self.note.clear()
        self.status_label.setText("Lisans onaylandi." if approved else "Lisans talebi reddedildi.")
        self.reload()
        if approved and isinstance(result, dict):
            if result.get("mail_sent"):
                QMessageBox.information(self, "Lisans onayi", "Lisans onaylandi. Musteriye info@ayecpro.com adresinden e-posta gonderildi.")
            else:
                QMessageBox.warning(self, "E-posta gonderilemedi", "Lisans onaylandi ancak e-posta gonderilemedi. " + str(result.get("mail_message") or "SMTP ayarlarini kontrol edin."))
