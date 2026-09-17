# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QHeaderView, QAbstractItemView, QLineEdit, QFrame, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from datetime import datetime

from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens
from src.utils.system_config import SystemConfig
from src.utils.date_formatter import format_date
from src.ui.widgets.empty_state import EmptyState

class CustomersBaseMixin:
    """Base UI and layout logic for CustomersPage."""

    def apply_theme_styles(self):
        self.setStyleSheet(theme_qss("background: @window;"))
        if hasattr(self, "tabs"):
            self.tabs.setStyleSheet(
                theme_qss("""
                QTabWidget::pane { background: @window; border: none; }
                QTabBar::tab {
                    background: @surface_alt;
                    color: @text;
                    padding: 9px 16px;
                    border: 1px solid @border;
                    border-bottom: none;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                    margin-right: 4px;
                    font-weight: 700;
                }
                QTabBar::tab:selected { background: @accent; color: @selection_text; }
            """)
            )
        if hasattr(self, "tab_main"):
            self.tab_main.setStyleSheet(theme_qss("background: @window;"))
        if hasattr(self, "table"):
            self.table.setStyleSheet(
                theme_qss("""
                QTableWidget { border-radius: 12px; border: 1px solid @border; background: @surface; }
                QHeaderView::section { background-color: @surface_alt; color: @text; padding: 12px 10px; font-weight: bold; border: none; }
                QTableWidget::item { padding: 10px 12px; color: @text; border-bottom: 1px solid @surface_alt; background: @surface; }
                QTableWidget::item:selected { background-color: @selection_bg; color: @selection_text; font-weight: bold; border: none; outline: none; }
                QTableWidget::item:focus { outline: none; }
            """)
            )
        if hasattr(self, "inp_search"):
            self.inp_search.setStyleSheet(
                theme_qss(
                    "border: 1px solid @border; border-radius: 8px; padding-left: 10px; background: @surface; color: @text;"
                )
            )
        for child in self.findChildren(QFrame):
            if child.objectName() == "CustomerFilterBar":
                child.setStyleSheet(theme_qss("QFrame#CustomerFilterBar { background: @surface; border: 1px solid @border; border-radius: 12px; }"))
            elif child.objectName() == "CustomerToolbarCard":
                child.setStyleSheet(theme_qss("QFrame#CustomerToolbarCard { background: @surface; border: 1px solid @border; border-radius: 12px; }"))

    def setup_ui(self):
        """Arayüz hiyerarşisini kurar"""
        self.setStyleSheet(theme_qss("background: @window;"))
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            theme_qss("""
            QTabWidget::pane { background: @window; border: none; }
            QTabBar::tab {
                background: @surface_alt;
                color: @text;
                padding: 9px 16px;
                border: 1px solid @border;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 4px;
                font-weight: 700;
            }
            QTabBar::tab:selected { background: @accent; color: @selection_text; }
        """)
        )
        self.tab_main = QWidget()
        self.tab_main.setStyleSheet(theme_qss("background: @window;"))
        self.tabs.addTab(self.tab_main, "👥 Müşteri Listesi")

        self.layout = QVBoxLayout(self.tab_main)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(12)

        # 1. Hızlı Erişim Kartları (Filtreleme)
        self._setup_banners()
        # 2. Araç Çubuğu (Dışa Aktarma & Arama)
        self._setup_toolbar()
        # 3. Veri Tablosu
        self._setup_table()
        # 4. Alt Bilgi (Footer)
        self._setup_footer()

    def _setup_header(self):
        # Note: This method was present in the plan but not called in setup_ui in the original file.
        # It's kept here for potential future use or if missed in original orkestration.
        hero = QFrame()
        hero.setObjectName("CustomersHero")
        hero.setStyleSheet(
            theme_qss("""
            QFrame#CustomersHero {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 @surface,
                    stop:1 @surface_alt
                );
                border: 1px solid @border;
                border-radius: 18px;
            }
        """)
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(18)

        icon_badge = QLabel("👥")
        icon_badge.setFixedSize(54, 54)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet(
            theme_qss("""
            QLabel {
                background: @accent;
                color: @selection_text;
                border-radius: 27px;
                font-size: 24px;
                font-weight: 700;
            }
        """)
        )
        hero_layout.addWidget(icon_badge, alignment=Qt.AlignmentFlag.AlignTop)

        title_box = QVBoxLayout()
        title_box.setSpacing(6)
        self.header_title = QLabel("Müşteri Yönetimi")
        self.header_title.setObjectName("DashboardWelcomeTitle")
        self.header_title.setStyleSheet(
            theme_qss("""
            color: @text;
            font-size: 28px;
            font-weight: 800;
            border: none;
            background: transparent;
        """)
        )
        self.header_subtitle = QLabel(
            "Müşterileri, cari durumlarını ve tahsilat aksiyonlarını tek ekranda yönetin."
        )
        self.header_subtitle.setWordWrap(True)
        self.header_subtitle.setStyleSheet(
            theme_qss("""
            color: @text_muted;
            font-size: 13px;
            border: none;
            background: transparent;
        """)
        )
        title_box.addWidget(self.header_title)
        title_box.addWidget(self.header_subtitle)
        hero_layout.addLayout(title_box, 1)

        self.header_badge = QLabel("MÜŞTERİ HUB")
        self.header_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_badge.setFixedHeight(34)
        self.header_badge.setMinimumWidth(140)
        self.header_badge.setStyleSheet(
            theme_qss("""
            QLabel {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 17px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 14px;
            }
        """)
        )
        hero_layout.addWidget(self.header_badge, alignment=Qt.AlignmentFlag.AlignTop)

        self.layout.addWidget(hero)

    def _setup_banners(self):
        banner_card = QFrame()
        banner_card.setObjectName("CustomerFilterBar")
        banner_card.setFixedHeight(52)
        banner_card.setStyleSheet(
            theme_qss(
                "QFrame#CustomerFilterBar { background: @surface; border: 1px solid @border; border-radius: 12px; }"
            )
        )
        banner_layout = QHBoxLayout(banner_card)
        banner_layout.setContentsMargins(14, 8, 14, 8)
        banner_layout.setSpacing(12)

        configs = [
            ("TÜM MÜŞTERİLER", tc("accent"), lambda: self.filter_by_type(None), 1),
            ("NET BORÇLULAR", tc("danger"), lambda: self.filter_by_type("DEBTORS"), 1),
            ("TAHSİLAT BEKLEYENLER", tc("warning"), lambda: self.filter_by_type("OPEN_RECEIVABLES"), 1),
            ("+ YENİ MÜŞTERİ EKLE", tc("success"), self.add_customer, 1),
        ]

        for text_value, color, cb, stretch in configs:
            btn = self._create_banner_btn(text_value, color)
            btn.clicked.connect(cb)
            banner_layout.addWidget(btn, stretch)

        self.layout.addWidget(banner_card)

    def _create_banner_btn(self, text, color):
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn.setStyleSheet(
            theme_qss(f"""
            QPushButton {{ background-color: {color}; color: @selection_text; border-radius: 17px; border: none; padding: 0 12px; }}
            QPushButton:hover {{ background-color: @surface; color: {color}; border: 2px solid {color}; }}
        """)
        )
        return btn

    def _setup_toolbar(self):
        toolbar_card = QFrame()
        toolbar_card.setObjectName("CustomerToolbarCard")
        toolbar_card.setFixedHeight(52)
        toolbar_card.setStyleSheet(
            theme_qss(
                "QFrame#CustomerToolbarCard { background: @surface; border: 1px solid @border; border-radius: 12px; }"
            )
        )
        toolbar = QHBoxLayout(toolbar_card)
        toolbar.setContentsMargins(14, 8, 14, 8)
        toolbar.setSpacing(10)
        tone_map = {
            "KOPYALA": "warning",
            "EXCEL": "success",
            "PDF": "secondary",
            "YAZDIR": "outline",
        }

        tools = [
            ("KOPYALA", "📋", tc("warning"), self.copy_list, "Listeyi Kopyala"),
            ("EXCEL", "📊", tc("success"), self.export_excel, "Excel'e Aktar"),
            ("PDF", "📄", tc("text"), self.export_pdf, "PDF'e Aktar"),
            ("YAZDIR", "🖨️", tc("text_muted"), self.print_list, "Yazdır"),
        ]

        for text, icon, color, cb, tooltip in tools:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                theme_qss(DesignTokens.get_icon_btn_qss())
            )
            btn.clicked.connect(cb)
            toolbar.addWidget(btn)

        btn_docs = QPushButton("🗂️")
        btn_docs.setFixedSize(40, 40)
        btn_docs.setToolTip("Belge Merkezi")
        btn_docs.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_docs.setStyleSheet(
            theme_qss(DesignTokens.get_icon_btn_qss())
        )
        btn_docs.clicked.connect(self.open_documents_center)
        toolbar.addWidget(btn_docs)

        btn_import = QPushButton("\u2b06")
        btn_import.setFixedSize(40, 40)
        btn_import.setToolTip("M\u00fc\u015fteri I\u00e7e Aktar")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setStyleSheet(
            theme_qss(DesignTokens.get_icon_btn_qss())
        )
        btn_import.clicked.connect(self.import_customers)
        toolbar.addWidget(btn_import)

        self.btn_multi = QPushButton("🔲")
        self.btn_multi.setCheckable(True)
        self.btn_multi.setFixedSize(40, 40)
        self.btn_multi.setToolTip("Çoklu Seçim")
        self.btn_multi.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_multi.setStyleSheet(
            theme_qss(DesignTokens.get_icon_btn_qss())
        )
        self.btn_multi.clicked.connect(self.toggle_multiselect)
        toolbar.addWidget(self.btn_multi)

        toolbar.addStretch()
        lbl_search = QLabel("<b>Arama:</b>")
        lbl_search.setStyleSheet(
            theme_qss("color: @text_muted; font-weight: 700; padding-right: 6px;")
        )
        toolbar.addWidget(lbl_search)
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("İsim, telefon veya e-posta...")
        self.inp_search.setFixedWidth(250)
        self.inp_search.setFixedHeight(35)
        self.inp_search.setStyleSheet(
            theme_qss(
                "border: 1px solid @border; border-radius: 8px; padding-left: 10px; background: @surface; color: @text;"
            )
        )
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(500))
        toolbar.addWidget(self.inp_search)

        self.layout.addWidget(toolbar_card)

    def _setup_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["MÜ.NO", "MÜŞTERİ", "FİRMA", "TELEFON", "E-POSTA", "BAKİYE", "İŞLEMLER"]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 76)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.table.setColumnWidth(1, 280)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 180)

        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 154)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 210)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 190)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 190)
        self.table.verticalHeader().setVisible(False)
        self.table.setCornerButtonEnabled(False)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self._on_table_cell_entered)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(
            theme_qss("""
            QTableWidget { border-radius: 12px; border: 1px solid @border; background: @surface; }
            QHeaderView::section { background-color: @surface_alt; color: @text; padding: 12px 10px; font-weight: bold; border: none; }
            QTableWidget::item { padding: 10px 12px; color: @text; border-bottom: 1px solid @surface_alt; background: @surface; }
            QTableWidget::item:selected { background-color: @selection_bg; color: @selection_text; font-weight: bold; border: none; outline: none; }
            QTableWidget::item:focus { outline: none; }
        """)
        )
        self.layout.addWidget(self.table)
        self.empty_state = EmptyState(
            "Henüz müşteri yok",
            "Bu görünümde gösterilecek müşteri kaydı bulunamadı.",
            parent=self,
        )
        self.empty_state.setMinimumHeight(280)
        self.empty_state.hide()
        self.layout.addWidget(self.empty_state)

    def _setup_footer(self):
        self.footer = QFrame()
        self.footer.setObjectName("CustomerFooterCard")
        self.footer.setFixedHeight(44)
        self.footer.setStyleSheet(
            theme_qss(
                "QFrame#CustomerFooterCard { background: @surface_alt; border: 1px solid @border; border-radius: 10px; }"
            )
        )
        f_layout = QHBoxLayout(self.footer)
        f_layout.setContentsMargins(12, 6, 12, 6)
        f_layout.setSpacing(10)
        self.lbl_total = QLabel("📊 Toplam Kayıt: 0")
        self.lbl_total.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
        self.lbl_time = QLabel(
            f"🕒 Son Güncelleme: {format_date(datetime.now(), self.db, include_time=True)}"
        )
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_time.setStyleSheet(theme_qss("color: @text_muted; border: none; background: transparent;"))

        left_box = QWidget()
        left_layout = QHBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.lbl_total)
        left_layout.addStretch()

        center_box = QWidget()
        center_layout = QHBoxLayout(center_box)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        center_layout.addStretch()

        right_box = QWidget()
        right_layout = QHBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addStretch()
        right_layout.addWidget(self.lbl_time)

        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedSize(40, 30)
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_prev.setStyleSheet(
            theme_qss(
                "background: @surface; color: @text; border: 1px solid @border; border-radius: 8px;"
            )
        )

        self.lbl_page = QLabel("1 / 1")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page.setMinimumWidth(52)
        self.lbl_page.setStyleSheet(
            theme_qss("font-weight: 800; color: @text; border: none; background: transparent;")
        )

        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedSize(40, 30)
        self.btn_next.clicked.connect(self.next_page)
        self.btn_next.setStyleSheet(
            theme_qss(
                "background: @surface; color: @text; border: 1px solid @border; border-radius: 8px;"
            )
        )

        center_layout.addWidget(self.btn_prev)
        center_layout.addWidget(self.lbl_page)
        center_layout.addWidget(self.btn_next)
        center_layout.addStretch()

        f_layout.addWidget(left_box, 1)
        f_layout.addWidget(center_box, 1)
        f_layout.addWidget(right_box, 1)

        self.layout.addWidget(self.footer)

        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget()
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "❓ Nasıl Kullanılır?")

        self.main_layout.addWidget(self.tabs)

    def _update_pagination_ui(self):
        total_pages = (self.total_count + self.limit - 1) // self.limit
        if total_pages == 0:
            total_pages = 1

        self.lbl_page.setText(f"{self.current_page + 1} / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < total_pages - 1)

    def _prepare_initial_view(self):
        """Yükleniyor durumunu göster. Worker çalışıyorsa tabloyu sıfırlama."""
        self.lbl_total.setText("⏳ Yükleniyor...")
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.request_reload()

    def next_page(self):
        total_pages = (self.total_count + self.limit - 1) // self.limit
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.request_reload()

    def filter_by_type(self, type_name):
        self.current_filter_type = type_name
        title_map = {
            None: "Müşteri Yönetimi",
            "DEBTORS": "Net Borçlular",
            "OPEN_RECEIVABLES": "Tahsilat Bekleyenler",
        }
        subtitle_map = {
            None: "Müşterileri, cari durumlarını ve tahsilat aksiyonlarını tek ekranda yönetin.",
            "DEBTORS": "Borç bakiyesi taşıyan kayıtları odak görünümünde inceleyin.",
            "OPEN_RECEIVABLES": "Tahsilat bekleyen işlemleri hızlıca filtreleyip aksiyon alın.",
        }
        badge_map = {
            None: "MÜŞTERİ HUB",
            "DEBTORS": "BORÇ ODAĞI",
            "OPEN_RECEIVABLES": "TAHSİLAT",
        }
        if hasattr(self, "header_title"):
            self.header_title.setText(
                title_map.get(type_name, "Müşteri Yönetimi")
            )
        if hasattr(self, "header_subtitle"):
            self.header_subtitle.setText(
                subtitle_map.get(type_name, subtitle_map[None])
            )
        if hasattr(self, "header_badge"):
            self.header_badge.setText(badge_map.get(type_name, badge_map[None]))
        self.current_page = 0
        self.request_reload()
