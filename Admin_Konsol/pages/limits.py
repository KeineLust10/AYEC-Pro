"""
AYEC Pro Admin Konsol - Kota & Limit Y\u00f6netimi Sayfas\u0131
Firmalar\u0131n veritaban\u0131 limitleri, cihaz kotalar\u0131 ve kullan\u0131m seviyeleri.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QProgressBar, QLineEdit, QScrollArea, QGridLayout, QComboBox,
    QStackedWidget, QSizePolicy, QBoxLayout, QCheckBox, QToolButton, QStyle
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPainter
import api_client


class _FetchLimits(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            # Sunucu limit verilerini listele
            import requests
            import config
            h = {"Content-Type": "application/json"}
            if api_client._session_token:
                h["Cookie"] = f"ayec_session={api_client._session_token}"
            resp = requests.get(
                config.server_url() + "/api/admin/licenses/usage",
                headers=h,
                timeout=config.timeout()
            )
            if not resp.ok:
                raise RuntimeError(resp.json().get("error") or "Kullanim verisi alinamadi")
            self.done.emit(resp.json().get("usages", []))
        except Exception as exc:
            self.error.emit(str(exc))


class _ToggleSwitch(QCheckBox):
    def __init__(self, accessible_name: str, parent=None):
        super().__init__(parent)
        self.setAccessibleName(accessible_name)
        self.setFixedSize(42, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QColor("#adc6ff" if self.isChecked() else "#303444")
        painter.setPen(QColor("#4cd7f6") if self.hasFocus() else track)
        painter.setBrush(track)
        painter.drawRoundedRect(self.rect().adjusted(0, 1, -1, -1), 10, 10)
        knob_x = 23 if self.isChecked() else 3
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#102f68" if self.isChecked() else "#c2c6d6"))
        painter.drawEllipse(knob_x, 4, 14, 14)


class LimitsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._thread = None
        self._usage_rows = []
        self._build_ui()
        self._load()

    def _build_ui(self):
        self.setObjectName("adminLimitsPage")
        self.setStyleSheet("""
            QWidget#adminLimitsPage { background: #0e1321; color: #dee2f6; }
            QWidget#adminLimitsPage QLabel { background: transparent; }
            QScrollArea#limitsScroll { border: 0; background: #0e1321; }
            QScrollArea#limitsScroll > QWidget > QWidget { background: #0e1321; }
            QScrollBar:vertical { width: 8px; background: #0e1321; }
            QScrollBar::handle:vertical { min-height: 28px; background: #303444; border-radius: 4px; }
            QFrame#limitsHero, QFrame#limitsMetric, QFrame#limitsSection { background: #161b2a; border: 1px solid #252a39; border-radius: 5px; }
            QFrame#limitsHero { background: #111827; }
            QLabel#limitsEyebrow { color: #adc6ff; font: 700 9px "Segoe UI", Arial; }
            QLabel#limitsTitle { color: #dee2f6; font: 700 20px "Segoe UI", Arial; }
            QLabel#limitsDescription { color: #c2c6d6; font: 10px "Segoe UI", Arial; }
            QLabel#limitsMetricLabel { color: #8c909f; font: 700 8px "Segoe UI", Arial; }
            QLabel#limitsMetricValue { color: #dee2f6; font: 700 20px "Segoe UI", Arial; }
            QLabel#limitsMetricDetail { color: #4cd7f6; font: 8px "Segoe UI", Arial; }
            QLabel#limitsSectionTitle { color: #dee2f6; font: 700 12px "Segoe UI", Arial; }
            QLabel#limitsPolicyName { color: #dee2f6; font: 700 11px "Segoe UI", Arial; }
            QLabel#limitsMuted { color: #8c909f; font: 9px "Segoe UI", Arial; }
            QLineEdit#limitsSearch, QComboBox#limitsFilter { min-height: 32px; padding: 5px 8px; color: #dee2f6; background: #090e1c; border: 1px solid #303444; border-radius: 4px; font: 9px "Segoe UI", Arial; }
            QTableWidget#limitsTable { background: #161b2a; color: #c2c6d6; border: 1px solid #252a39; gridline-color: #252a39; font: 9px "Segoe UI", Arial; selection-background-color: #252a39; }
            QTableWidget#limitsTable::item { padding: 7px; }
            QLabel#limitsCellValue { color: #dee2f6; font: 600 10px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#limitsCellDetail { color: #8c909f; font: 9px "JetBrains Mono", "Segoe UI", Arial; }
            QProgressBar#limitsInlineProgress { max-height: 4px; border: 0; border-radius: 2px; background: #303444; }
            QProgressBar#limitsInlineProgress::chunk { border-radius: 2px; background: #4d8eff; }
            QLabel#limitsStatusBadge { color: #4edea3; background: #0e3434; border-radius: 9px; padding: 4px 8px; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#limitsHealthBadge { color: #4edea3; background: #103b3b; border-radius: 4px; padding: 6px 9px; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#limitsThresholdBadge { color: #4cd7f6; background: #102a3d; border-radius: 4px; padding: 6px 9px; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QPushButton#limitsRowAction { min-height: 27px; padding: 3px 7px; color: #adc6ff; background: #1a1f2e; border: 0; border-radius: 3px; }
            QToolButton#limitsInspectAction { min-width: 28px; max-width: 28px; min-height: 27px; color: #adc6ff; background: transparent; border: 0; }
            QHeaderView::section { padding: 8px; color: #8c909f; background: #1a1f2e; border: 0; font: 700 8px "Segoe UI", Arial; }
            QFrame#limitsTenantCard { background: #161b2a; border: 1px solid #252a39; border-radius: 5px; }
            QLabel#limitsTenantName { color: #dee2f6; font: 700 12px "Segoe UI", Arial; }
            QLabel#limitsTenantValue { color: #c2c6d6; font: 9px "Segoe UI", Arial; }
            QPushButton { min-height: 31px; padding: 5px 9px; color: #dee2f6; background: #252a39; border: 1px solid #303444; border-radius: 4px; font: 9px "Segoe UI", Arial; }
            QPushButton#limitsPrimary { color: #00285d; background: #4d8eff; border-color: #4d8eff; font-weight: 700; }
            QPushButton#limitsSecondary { color: #dee2f6; background: #1a1f2e; border-color: #303444; }
            QPushButton:disabled { color: #8c909f; background: #252a39; border-color: #303444; }
            QLabel#limitsStatus { color: #4cd7f6; font: 9px "Segoe UI", Arial; }
            QFrame#limitsHero { min-height: 94px; background: #161b2a; border-color: transparent; border-radius: 8px; }
            QLabel#limitsTitle { font: 700 19px "Segoe UI", Arial; }
            QLabel#limitsDescription { font: 12px "Segoe UI", Arial; }
            QFrame#limitsMetric { min-height: 132px; background: #161b2a; border: 0; border-radius: 8px; }
            QLabel#limitsMetricLabel { color: #dee2f6; font: 500 12px "Segoe UI", Arial; }
            QLabel#limitsMetricValue { color: #dee2f6; font: 700 26px "Segoe UI", Arial; }
            QLabel#limitsMetricDetail { color: #4edea3; font: 700 9px "Segoe UI", Arial; }
            QTableWidget#limitsTable { border: 0; gridline-color: #252a39; font: 10px "Segoe UI", Arial; }
            QHeaderView::section { min-height: 30px; padding: 6px; color: #c2c6d6; background: #111827; font: 700 9px "Segoe UI", Arial; }
            QFrame#limitsSection { border: 0; border-radius: 8px; }
            QFrame#limitsTableHead { background: #161b2a; border: 0; border-radius: 8px; }
            QLabel#limitsSectionTitle { font: 700 16px "Segoe UI", Arial; }
            QLabel#limitsMuted { color: #c2c6d6; font: 10px "Segoe UI", Arial; }
            QComboBox#limitsUpgradeTenant { min-height: 36px; padding: 5px 8px; color: #dee2f6; background: #1a1f2e; border: 0; border-radius: 4px; }
            QCheckBox { spacing: 8px; color: #dee2f6; font: 9px "Segoe UI", Arial; }
            QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #424754; border-radius: 9px; background: #252a39; }
            QCheckBox::indicator:checked { border-color: #adc6ff; background: #adc6ff; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("limitsScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(10)
        self._content_layout = layout

        hero = QFrame()
        self._hero = hero
        hero.setObjectName("limitsHero")
        self._hero_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, hero)
        self._hero_layout.setContentsMargins(14, 11, 14, 11)
        title_block = QVBoxLayout()
        eyebrow = QLabel("SAAS TENANT RESOURCE CONTROL")
        eyebrow.setObjectName("limitsEyebrow")
        eyebrow.setWordWrap(True)
        eyebrow.setMinimumWidth(0)
        eyebrow.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title = QLabel("Kota & Limit Kontrol\u00fc (SaaS Multi-Tenant)")
        title.setObjectName("limitsTitle")
        title.setWordWrap(True)
        title.setMinimumWidth(0)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        description = QLabel("Tenant veritaban\u0131 boyutunu, kullan\u0131c\u0131 say\u0131s\u0131n\u0131, kay\u0131tl\u0131 cihazlar\u0131 ve servis kay\u0131tlar\u0131n\u0131 merkezi API'den izleyin.")
        description.setObjectName("limitsDescription")
        description.setWordWrap(True)
        description.setMinimumWidth(0)
        description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_block.addWidget(eyebrow)
        title_block.addWidget(title)
        title_block.addWidget(description)
        self._hero_layout.addLayout(title_block, 1)
        hero_actions = QWidget(hero)
        self._hero_actions = hero_actions
        hero_actions.setStyleSheet("background: transparent;")
        hero_actions.setMinimumWidth(0)
        hero_actions_layout = QVBoxLayout(hero_actions)
        hero_actions_layout.setContentsMargins(0, 0, 0, 0)
        hero_actions_layout.setSpacing(5)
        badge_row = QHBoxLayout()
        self._hero_badge_row = badge_row
        badge_row.setContentsMargins(0, 0, 0, 0)
        self._health_badge = QLabel("T\u00fcm Kotalar Normal (0 A\u015f\u0131m)")
        self._health_badge.setObjectName("limitsHealthBadge")
        self._health_badge.setWordWrap(True)
        self._health_badge.setMinimumWidth(0)
        self._health_badge.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        threshold_badge = QLabel("Otomatik Uyar\u0131 E\u015fi\u011fi: %85")
        threshold_badge.setObjectName("limitsThresholdBadge")
        threshold_badge.setWordWrap(True)
        threshold_badge.setMinimumWidth(0)
        threshold_badge.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        badge_row.addWidget(self._health_badge)
        badge_row.addWidget(threshold_badge)
        hero_actions_layout.addLayout(badge_row)
        action_row = QHBoxLayout()
        self._hero_action_row = action_row
        action_row.setContentsMargins(0, 0, 0, 0)
        self._refresh_button = QPushButton("Kotalar\u0131 Yenile")
        self._refresh_button.setObjectName("limitsSecondary")
        self._refresh_button.clicked.connect(self._load)
        package_button = QPushButton("Kota Paketi Tan\u0131mla")
        package_button.setObjectName("limitsPrimary")
        self._package_button = package_button
        package_button.clicked.connect(lambda: self._upgrade_tenant.setFocus())
        action_row.addWidget(self._refresh_button)
        action_row.addWidget(package_button)
        action_row.setStretch(0, 1)
        action_row.setStretch(1, 1)
        hero_actions_layout.addLayout(action_row)
        self._hero_layout.addWidget(hero_actions)
        layout.addWidget(hero)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self._metric_grid = metrics
        self._metric_tenants = QLabel("0")
        self._metric_critical = QLabel("0")
        self._metric_db = QLabel("0 MB")
        self._metric_users = QLabel("0")
        self._metric_devices = QLabel("0")
        self._metric_services = QLabel("0")
        self._metric_cards = []
        for caption_text, value, detail in (
            ("Toplam Veritabani Hacmi", self._metric_db, "Cok Dusuk Yuk  |  0.04% Kullanim"),
            ("Aktif Lisansli Kullanici", self._metric_users, "32 Bos Lisans  |  20.0% Kapasite"),
            ("Kayitli Terminal / Cihaz", self._metric_devices, "Stabil & Rezerv  |  6.0% Kullanim"),
            ("Aylik Servis Formu Uretimi", self._metric_services, "Kota Asimi Yok  |  10.3% Hacim"),
        ):
            card = QFrame()
            card.setObjectName("limitsMetric")
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(11, 9, 11, 9)
            caption = QLabel(caption_text)
            caption.setObjectName("limitsMetricLabel")
            caption.setWordWrap(True)
            value.setObjectName("metricValue")
            value.setObjectName("limitsMetricValue")
            value.setWordWrap(True)
            value.setMinimumWidth(0)
            value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            detail_label = QLabel(detail)
            detail_label.setObjectName("limitsMetricDetail")
            detail_label.setWordWrap(True)
            detail_label.setMinimumWidth(0)
            detail_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            card_lay.addWidget(caption)
            card_lay.addWidget(value)
            card_lay.addWidget(detail_label)
            self._metric_cards.append(card)
        self._metric_columns = 0
        layout.addLayout(metrics)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("limitsTableHead")
        self._table_toolbar_frame = toolbar_frame
        toolbar = QHBoxLayout(toolbar_frame)
        self._table_toolbar = toolbar
        toolbar.setContentsMargins(12, 8, 12, 8)
        toolbar.setSpacing(8)
        table_heading_widget = QWidget(toolbar_frame)
        self._table_heading_widget = table_heading_widget
        table_heading = QVBoxLayout(table_heading_widget)
        table_heading.setContentsMargins(0, 0, 0, 0)
        table_heading.setSpacing(2)
        table_title = QLabel("Kiraci Firma Kota ve Kaynak Tuketim Tablosu")
        table_title.setObjectName("limitsSectionTitle")
        table_title.setWordWrap(True)
        table_title.setMinimumWidth(0)
        table_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        table_subtitle = QLabel("Canli senkronize edilen kiraci depolama, kullanici ve islem metrikleri")
        table_subtitle.setObjectName("limitsMuted")
        table_subtitle.setWordWrap(True)
        table_subtitle.setMinimumWidth(0)
        table_subtitle.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        table_heading.addWidget(table_title)
        table_heading.addWidget(table_subtitle)
        toolbar.addWidget(table_heading_widget, 0)
        self._search = QLineEdit()
        self._search.setObjectName("limitsSearch")
        self._search.setMinimumWidth(0)
        self._search.setMaximumWidth(224)
        self._search.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._search.setPlaceholderText("Firma ad\u0131 veya tenant kimli\u011fi ara...")
        self._search.textChanged.connect(self._filter_usages)
        toolbar.addWidget(self._search, 1)
        self._status_filter = QComboBox()
        self._status_filter.setObjectName("limitsFilter")
        self._status_filter.addItem("T\u00fcm firmalar", "all")
        self._status_filter.addItem("Limit uyar\u0131lar\u0131", "critical")
        self._status_filter.setMinimumWidth(126)
        self._status_filter.setMaximumWidth(126)
        self._status_filter.currentIndexChanged.connect(lambda _index: self._filter_usages(self._search.text()))
        toolbar.addWidget(self._status_filter)
        layout.addWidget(toolbar_frame)

        self._table = QTableWidget()
        self._table.setObjectName("limitsTable")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Kirac\u0131 Firma / Paket", "DB Boyutu (Kullanim / Limit)", "Kullan\u0131c\u0131 Kotasi", "Kay\u0131tl\u0131 Cihaz", "Ayl\u0131k Servis Formu", "Durum", "Yonetim"
        ])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setWordWrap(True)
        self._table.setMinimumWidth(0)
        self._table.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self._mobile_list = QWidget()
        self._mobile_list.setMinimumWidth(0)
        self._mobile_list.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self._mobile_layout = QVBoxLayout(self._mobile_list)
        self._mobile_layout.setContentsMargins(0, 0, 0, 0)
        self._mobile_layout.setSpacing(8)
        self._data_stack = QStackedWidget()
        self._data_stack.addWidget(self._table)
        self._data_stack.addWidget(self._mobile_list)
        layout.addWidget(self._data_stack, 0)
        table_footer = QHBoxLayout()
        table_footer.setContentsMargins(4, 0, 4, 0)
        self._table_total = QLabel("Toplam 0 aktif kiraci firma listeleniyor")
        self._table_total.setObjectName("limitsMuted")
        self._table_total.setWordWrap(True)
        self._table_total.setMinimumWidth(0)
        self._table_total.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        table_footer.addWidget(self._table_total, 1)
        self._page_previous = QPushButton("Onceki")
        self._page_previous.setEnabled(False)
        self._page_number = QPushButton("1")
        self._page_number.setObjectName("limitsPrimary")
        self._page_next = QPushButton("Sonraki")
        self._page_next.setEnabled(False)
        table_footer.addWidget(self._page_previous)
        table_footer.addWidget(self._page_number)
        table_footer.addWidget(self._page_next)
        layout.addLayout(table_footer)

        panels = QGridLayout()
        panels.setSpacing(10)
        self._panels_grid = panels
        self._panels_compact = None
        self._policy_panel = self._unavailable_panel(
            "Otomatik Limit A\u015f\u0131m Politikalar\u0131",
            "Soft limit bildirimi, hard limit i\u015flemi ve istisna listesi API taraf\u0131nda sunulmuyor.",
            "Desteklenmiyor",
        )
        self._upgrade_panel = self._unavailable_panel(
            "Se\u00e7ili Firma \u0130\u00e7in H\u0131zl\u0131 Kota Y\u00fckseltme",
            "Kota ve fiyat de\u011fi\u015fiklikleri merkezi katalog ve lisans API'siyle y\u00f6netilmeli.",
            "Desteklenmiyor",
        )
        panels.addWidget(self._policy_panel, 0, 0)
        panels.addWidget(self._upgrade_panel, 0, 1)
        layout.addLayout(panels)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("limitsStatus")
        self._status_lbl.setWordWrap(True)
        layout.addWidget(self._status_lbl)
        self._scroll.setWidget(content)
        root.addWidget(self._scroll, 1)
        self._apply_responsive_layout()

    def _unavailable_panel(self, title: str, detail: str, action: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("limitsSection")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("limitsSectionTitle")
        heading.setWordWrap(True)
        heading.setMinimumWidth(0)
        heading.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        description = QLabel(detail)
        description.setObjectName("limitsMuted")
        description.setWordWrap(True)
        description.setMinimumWidth(0)
        description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(heading)
        layout.addWidget(description)
        if title.startswith("Otomatik"):
            self._policy_controls = []
            for name, explanation in (
                ("Veritabani %90 doldugunda firmaya bildirim gonder", "Yetkili e-posta ve WhatsApp hattina otomatik kota uyari sablonu iletilir"),
                ("Kota asildiginda sistemi salt okunur moda al (Yazma engelle)", "Sadece sorgu ve raporlamaya izin verilir; yeni servis formu olusturulamaz"),
                ("Kullanici limiti doldugunda yeni davet gonderimini engelle", "Maksimum kullanici sayisina ulasilan subelerde davet kodu islemleri durdurulur"),
            ):
                row = QWidget(panel)
                row.setMinimumWidth(0)
                row.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 7, 0, 7)
                copy = QVBoxLayout()
                label = QLabel(name)
                label.setObjectName("limitsPolicyName")
                label.setWordWrap(True)
                label.setMinimumWidth(0)
                label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                note = QLabel(explanation)
                note.setObjectName("limitsMuted")
                note.setWordWrap(True)
                note.setMinimumWidth(0)
                note.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                copy.addWidget(label)
                copy.addWidget(note)
                toggle = _ToggleSwitch(name)
                toggle.setChecked(True)
                self._policy_controls.append(toggle)
                row_layout.addLayout(copy, 1)
                row_layout.addWidget(toggle)
                layout.addWidget(row)
        else:
            self._upgrade_tenant = QComboBox(panel)
            self._upgrade_tenant.setObjectName("limitsUpgradeTenant")
            self._upgrade_tenant.setMinimumWidth(0)
            self._upgrade_tenant.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            self._upgrade_tenant.addItem("ASLAN TIC (ID: #AYEC-1001, Kurumsal Paket)", "tenant-a")
            layout.addWidget(QLabel("Hedef Kiraci Firma"))
            layout.addWidget(self._upgrade_tenant)
            options = QHBoxLayout()
            self._upgrade_options_layout = options
            self._upgrade_options = []
            for label in ("+5 Koltuk", "+50 GB", "+2,000 Fis"):
                option = QCheckBox(label)
                option.setChecked(label != "+2,000 Fis")
                self._upgrade_options.append(option)
                options.addWidget(option, 1)
            layout.addLayout(options)
            action_button = QPushButton("$ 750 / Ay")
            action_button.setEnabled(False)
            layout.addWidget(action_button)
            self._upgrade_total = action_button
            for option in self._upgrade_options:
                option.toggled.connect(self._update_upgrade_total)
        return panel

    def _update_upgrade_total(self):
        prices = (450, 300, 200)
        total = sum(price for price, option in zip(prices, self._upgrade_options) if option.isChecked())
        self._upgrade_total.setText(f"$ {total} / Ay")

    def _select_upgrade_tenant(self, tenant_id):
        index = self._upgrade_tenant.findData(tenant_id)
        if index >= 0:
            self._upgrade_tenant.setCurrentIndex(index)

    def _apply_responsive_layout(self):
        compact = self.width() < 760
        if compact:
            self._content_layout.setContentsMargins(20, 20, 20, 14)
            self._hero.setMinimumHeight(248)
            self._refresh_button.setText("Kotalar\u0131\nYenile")
            self._package_button.setText("Kota Paketi\nTan\u0131mla")
            self._table_toolbar.setDirection(QBoxLayout.Direction.TopToBottom)
            self._table_toolbar_frame.setMaximumHeight(240)
            self._table_toolbar_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._table_heading_widget.setMinimumWidth(0)
            self._search.setMaximumWidth(16777215)
            self._status_filter.setMaximumWidth(16777215)
        else:
            self._content_layout.setContentsMargins(20, 16, 20, 18)
            self._hero.setMinimumHeight(0)
            self._refresh_button.setText("Kotalar\u0131 Yenile")
            self._package_button.setText("Kota Paketi Tan\u0131mla")
            self._table_toolbar.setDirection(QBoxLayout.Direction.LeftToRight)
            self._table_toolbar_frame.setFixedHeight(68)
            self._table_toolbar_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._table_heading_widget.setMinimumWidth(360)
            self._search.setMaximumWidth(224)
            self._status_filter.setMaximumWidth(126)
        self._hero_layout.setDirection(QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight)
        self._hero_actions.setMinimumWidth(0 if compact else 480)
        self._hero_badge_row.setDirection(QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight)
        self._hero_action_row.setDirection(QBoxLayout.Direction.LeftToRight)
        self._upgrade_options_layout.setDirection(QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight)
        columns = 1 if compact else 4
        if columns != self._metric_columns:
            for card in self._metric_cards:
                self._metric_grid.removeWidget(card)
            for index, card in enumerate(self._metric_cards):
                self._metric_grid.addWidget(card, index // columns, index % columns)
            self._metric_columns = columns
        self._data_stack.setCurrentWidget(self._mobile_list if compact else self._table)
        self._data_stack.setMinimumWidth(0)
        if compact:
            self._data_stack.setMaximumHeight(16777215)
            self._data_stack.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        else:
            row_height = sum(self._table.rowHeight(row) for row in range(self._table.rowCount()))
            table_height = self._table.horizontalHeader().height() + row_height + 2
            self._data_stack.setFixedHeight(max(250, table_height))
            self._data_stack.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        if compact != self._panels_compact:
            for panel in (self._policy_panel, self._upgrade_panel):
                self._panels_grid.removeWidget(panel)
            if compact:
                self._panels_grid.addWidget(self._policy_panel, 0, 0)
                self._panels_grid.addWidget(self._upgrade_panel, 1, 0)
            else:
                self._panels_grid.addWidget(self._policy_panel, 0, 0)
                self._panels_grid.addWidget(self._upgrade_panel, 0, 1)
            self._panels_compact = compact
        self._policy_panel.setMinimumWidth(0)
        self._upgrade_panel.setMinimumWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _load(self):
        if self._thread and self._thread.isRunning():
            return
        self._refresh_button.setEnabled(False)
        t = _FetchLimits()
        t.done.connect(self._populate)
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        t.finished.connect(lambda: self._refresh_button.setEnabled(True))
        t.start()
        self._thread = t

    def _populate(self, usages: list):
        self._status_lbl.setText("")
        self._table.setRowCount(0)
        self._usage_rows = []
        total_db = 0.0
        critical_count = 0
        total_users = 0
        total_devices = 0
        total_services = 0
        while self._mobile_layout.count():
            item = self._mobile_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for u in usages:
            users_count = int(u.get("users_count", 0) or 0)
            devices_count = int(u.get("devices_count", 0) or 0)
            services_count = int(u.get("services_count", 0) or 0)
            users_limit = int(u.get("users_limit", 10) or 10)
            devices_limit = int(u.get("devices_limit", 100) or 100)
            services_limit = int(u.get("services_limit", 1000) or 1000)
            db_size_mb = float(u.get("db_size_mb", 0) or 0)
            exceeded = users_count >= users_limit or devices_count >= devices_limit or services_count >= services_limit
            status = "Limit A\u015f\u0131m\u0131/Kritik" if exceeded else "Normal"
            color = QColor("#ffb4ab" if exceeded else "#4edea3")
            total_db += db_size_mb
            total_users += users_count
            total_devices += devices_count
            total_services += services_count
            if exceeded:
                critical_count += 1
            tenant_id = str(u.get("tenant_id") or "")
            company = str(u.get("company_name") or "Firma")
            self._usage_rows.append({"company": company, "tenant_id": tenant_id, "critical": exceeded})
            row = self._table.rowCount()
            self._table.insertRow(row)
            items = [
                f"{company}  #{u.get('license_code') or 'AYEC-1001'}\n{u.get('package_name') or 'Kurumsal Paket'}",
                f"{db_size_mb:.2f} MB / {float(u.get('db_limit_gb', 10) or 10):.2f} GB",
                f"{users_count} / {users_limit} Koltuk",
                f"{devices_count} / {devices_limit}",
                f"{services_count} / {services_limit}",
                status,
                "Kotayi Artir  |  \u25ce",
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(str(val))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, {"tenant_id": tenant_id, "company_name": company})
                elif col == 5:
                    item.setForeground(color)
                if 1 <= col <= 6:
                    item.setData(Qt.ItemDataRole.UserRole + 1, str(val))
                    item.setText("")
                self._table.setItem(row, col, item)
            database_limit_mb = float(u.get("db_limit_gb", 10) or 10) * 1024
            usage_cells = (
                (1, f"{db_size_mb:.2f} MB", f"{float(u.get('db_limit_gb', 10) or 10):.2f} GB", db_size_mb / database_limit_mb * 100 if database_limit_mb else 0),
                (2, f"{users_count} / {users_limit} Koltuk", f"Aktif: {users_count} kullanici", users_count / users_limit * 100 if users_limit else 0),
                (3, f"{devices_count} / {devices_limit}", f"%{devices_count / devices_limit * 100:.0f} Hacim" if devices_limit else "%0 Hacim", devices_count / devices_limit * 100 if devices_limit else 0),
                (4, f"{services_count} / {services_limit:,}".replace(",", "."), f"{services_count / services_limit * 100:.1f}%" if services_limit else "%0", services_count / services_limit * 100 if services_limit else 0),
            )
            for column, primary_text, detail_text, percent in usage_cells:
                cell = QWidget()
                cell.setStyleSheet("background: transparent;")
                cell_layout = QVBoxLayout(cell)
                cell_layout.setContentsMargins(5, 3, 5, 3)
                cell_layout.setSpacing(2)
                value_row = QHBoxLayout()
                value_row.setContentsMargins(0, 0, 0, 0)
                primary = QLabel(primary_text)
                primary.setObjectName("limitsCellValue")
                detail = QLabel(detail_text)
                detail.setObjectName("limitsCellDetail")
                value_row.addWidget(primary)
                value_row.addStretch(1)
                value_row.addWidget(detail)
                cell_layout.addLayout(value_row)
                progress = QProgressBar()
                progress.setObjectName("limitsInlineProgress")
                progress.setRange(0, 100)
                progress.setValue(max(0, min(100, round(percent))))
                progress.setTextVisible(False)
                cell_layout.addWidget(progress)
                self._table.setCellWidget(row, column, cell)
            status_badge = QLabel(status)
            status_badge.setObjectName("limitsStatusBadge")
            status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_badge.setFixedSize(82, 24)
            if exceeded:
                status_badge.setStyleSheet("color: #ffb4ab; background: #47252b; border-radius: 9px; padding: 4px 8px; font-weight: 700;")
            status_cell = QWidget()
            status_cell.setStyleSheet("background: transparent;")
            status_layout = QHBoxLayout(status_cell)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.addStretch(1)
            status_layout.addWidget(status_badge)
            status_layout.addStretch(1)
            self._table.setCellWidget(row, 5, status_cell)
            action_cell = QWidget()
            action_cell.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(3)
            upgrade_button = QPushButton("Kotayi Artir")
            upgrade_button.setObjectName("limitsRowAction")
            upgrade_button.clicked.connect(lambda _, value=tenant_id: self._select_upgrade_tenant(value))
            inspect_button = QToolButton()
            inspect_button.setObjectName("limitsInspectAction")
            inspect_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
            inspect_button.setAccessibleName("Firmayi Goruntule")
            inspect_button.clicked.connect(lambda _, value=tenant_id: self._select_upgrade_tenant(value))
            action_layout.addWidget(upgrade_button)
            action_layout.addWidget(inspect_button)
            self._table.setCellWidget(row, 6, action_cell)
            self._table.setRowHeight(row, 55)

            card = QFrame()
            card.setObjectName("limitsTenantCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(11, 9, 11, 9)
            card_layout.setSpacing(5)
            name = QLabel(company)
            name.setObjectName("limitsTenantName")
            tenant = QLabel(tenant_id or "Tenant ID verisi yok")
            tenant.setObjectName("limitsMuted")
            card_layout.addWidget(name)
            card_layout.addWidget(tenant)
            for label, value in (("DB boyutu", f"{db_size_mb:.2f} MB"), ("Kullan\u0131c\u0131lar", f"{users_count} / {users_limit}"), ("Cihazlar", f"{devices_count} / {devices_limit}"), ("Servis formlar\u0131", f"{services_count} / {services_limit}")):
                line = QHBoxLayout()
                title_label = QLabel(label)
                title_label.setObjectName("limitsMuted")
                value_label = QLabel(value)
                value_label.setObjectName("limitsTenantValue")
                line.addWidget(title_label)
                line.addStretch()
                line.addWidget(value_label)
                card_layout.addLayout(line)
            state = QLabel(status)
            state.setObjectName("limitsTenantValue")
            state.setStyleSheet(f"color: {color.name()}; font-weight: 700;")
            card_layout.addWidget(state)
            self._mobile_layout.addWidget(card)
        self._metric_tenants.setText(str(len(usages)))
        self._metric_critical.setText(str(critical_count))
        self._health_badge.setText(
            f"T\u00fcm Kotalar Normal ({critical_count} A\u015f\u0131m)" if not critical_count else f"{critical_count} Kritik Kota A\u015f\u0131m\u0131"
        )
        self._metric_db.setText(f"{total_db:.2f} MB / 100 GB")
        self._metric_users.setText(str(total_users))
        self._metric_devices.setText(f"{total_devices} / 400 Cihaz")
        self._metric_services.setText(f"{total_services} / 4,000 Fis")
        self._table_total.setText(f"Toplam {len(usages)} aktif kiraci firma listeleniyor  |  Son senkronizasyon: 12 saniye once")
        self._upgrade_tenant.clear()
        for usage in usages:
            tenant_id = str(usage.get("tenant_id") or "")
            company = str(usage.get("company_name") or "Firma")
            license_code = str(usage.get("license_code") or "AYEC-1001")
            package = str(usage.get("package_name") or "Kurumsal Paket")
            self._upgrade_tenant.addItem(f"{company} (ID: #{license_code}, {package})", tenant_id)
        self._filter_usages(self._search.text())

    def _filter_usages(self, query: str):
        needle = str(query or "").strip().casefold()
        critical_only = self._status_filter.currentData() == "critical"
        for row in range(self._table.rowCount()):
            values = [
                self._table.item(row, column).data(Qt.ItemDataRole.UserRole + 1)
                or self._table.item(row, column).text()
                for column in range(self._table.columnCount())
                if self._table.item(row, column) is not None
            ]
            row_data = self._usage_rows[row]
            values.append(row_data["tenant_id"])
            visible = (not needle or needle in " ".join(values).casefold()) and (not critical_only or row_data["critical"])
            self._table.setRowHidden(row, not visible)
            self._mobile_list.layout().itemAt(row).widget().setVisible(visible)

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1000)
        super().closeEvent(event)
