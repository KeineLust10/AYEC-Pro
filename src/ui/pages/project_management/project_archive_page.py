# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QScrollArea, QFrame, QGridLayout, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error
from src.utils.language_manager import LanguageManager


class ProjectArchivePage(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.lang = LanguageManager()
        self._all_projects = []
        self._current_page = 0
        self._page_size = 30
        self._total_projects = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        lbl_title = QLabel("📦 Proje Arşivi")
        lbl_title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss("color: @text;"))
        header.addWidget(lbl_title)
        header.addStretch()
        layout.addLayout(header)

        # Search
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Arşivde ara...")
        self.txt_search.setFixedHeight(38)
        self.txt_search.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @surface_alt; border: 1px solid @border;
                border-radius: 8px; padding: 0 12px; color: @text; font-size: 13px;
            }
            QLineEdit:focus { border-color: @accent; }
        """))
        self.txt_search.textChanged.connect(self._filter)
        layout.addWidget(self.txt_search)

        # Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(theme_qss("QScrollArea { border: none; background: transparent; }"))
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)

        pager = QHBoxLayout()
        pager.addStretch()
        self.btn_prev_page = QPushButton("< \u00d6nceki")
        self.lbl_page = QLabel("Sayfa 1 / 1")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_next_page = QPushButton("Sonraki >")
        self.btn_prev_page.clicked.connect(self._previous_page)
        self.btn_next_page.clicked.connect(self._next_page)
        pager.addWidget(self.btn_prev_page)
        pager.addWidget(self.lbl_page)
        pager.addWidget(self.btn_next_page)
        pager.addStretch()
        layout.addLayout(pager)

        self.load_projects()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_projects()

    def load_projects(self):
        search_query = self.txt_search.text().strip()
        offset = self._current_page * self._page_size
        projects, total = self.db.get_projects_paginated(
            limit=self._page_size,
            offset=offset,
            search_query=search_query,
            archived_only=True,
        )
        self._all_projects = list(projects)
        self._total_projects = int(total or 0)
        max_page = max(0, (self._total_projects - 1) // self._page_size)
        if self._current_page > max_page:
            self._current_page = max_page
            return self.load_projects()
        self._render(self._all_projects)
        self._update_pager()

    def _filter(self, text):
        self._current_page = 0
        self.load_projects()

    def _update_pager(self):
        page_count = max(1, (self._total_projects + self._page_size - 1) // self._page_size)
        self.lbl_page.setText(
            f"Sayfa {self._current_page + 1} / {page_count}"
        )
        self.btn_prev_page.setEnabled(self._current_page > 0)
        self.btn_next_page.setEnabled(self._current_page + 1 < page_count)

    def _previous_page(self):
        if self._current_page <= 0:
            return
        self._current_page -= 1
        self.load_projects()

    def _next_page(self):
        page_count = max(1, (self._total_projects + self._page_size - 1) // self._page_size)
        if self._current_page + 1 >= page_count:
            return
        self._current_page += 1
        self.load_projects()

    def _render(self, projects):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not projects:
            lbl = QLabel("Arşivde proje bulunmuyor.")
            lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px;"))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl, 0, 0, 1, 3)
            return

        col_count = 3
        for idx, proj in enumerate(projects):
            row = idx // col_count
            col = idx % col_count
            card = ArchivedProjectCard(proj, page=self)
            self.grid_layout.addWidget(card, row, col)

    def restore_project(self, project_id, project_name):
        if self.db.archive_project(project_id, archived=False):
            show_success(self, f"'{project_name}' arşivden çıkarıldı.")
            self.load_projects()
        else:
            show_error(self, "İşlem sırasında hata oluştu.")

    def confirm_delete(self, project_id, project_name):
        from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
        dlg = ModernConfirmDialog(
            "Projeyi Kalıcı Sil",
            f"'{project_name}' projesini kalıcı olarak silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!",
            self,
            confirm_text="Evet, Sil",
            cancel_text="Vazgeç",
            destructive=True
        )
        if dlg.exec():
            if self.db.delete_project(project_id):
                show_success(self, "Proje kalıcı olarak silindi.")
                self.load_projects()
            else:
                show_error(self, "Silme sırasında hata oluştu.")


class ArchivedProjectCard(QFrame):
    def __init__(self, project_data, page):
        super().__init__()
        self.project = project_data
        self.page = page
        self.setFixedSize(290, 170)
        self.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border-radius: 10px;
                border: 1px solid @border;
                opacity: 0.85;
            }
        """))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        keys = self.project.keys() if hasattr(self.project, 'keys') else []

        # Name + ref
        ref_no = self.project['ref_no'] if 'ref_no' in keys else None
        name_txt = self.project['name']
        if ref_no:
            name_txt = f"[{ref_no}] {name_txt}"
        lbl_name = QLabel(name_txt)
        lbl_name.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_name.setStyleSheet(theme_qss("border: none; color: @text_muted;"))
        lbl_name.setWordWrap(True)
        layout.addWidget(lbl_name)

        # Customer
        cust = self.project['customer_name'] if 'customer_name' in keys else None
        if cust:
            lbl_cust = QLabel(f"👤 {cust}")
            lbl_cust.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
            layout.addWidget(lbl_cust)

        # Status
        status = self.project['status']
        lbl_status = QLabel(f"Durum: {status}")
        lbl_status.setStyleSheet(theme_qss("color: @disabled_text; font-size: 10px; border: none;"))
        layout.addWidget(lbl_status)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_restore = QPushButton("↩️ Geri Al")
        btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore.setStyleSheet(theme_qss("""
            QPushButton {
                background: @accent; color: @selection_text;
                border: none; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: @accent_hover; }
        """))
        btn_restore.clicked.connect(lambda: self.page.restore_project(self.project['id'], self.project['name']))
        btn_row.addWidget(btn_restore)

        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setToolTip("Kalıcı Sil")
        btn_del.setStyleSheet(theme_qss("""
            QPushButton {
                background: transparent; color: @disabled_text;
                border: 1px solid @border; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { color: @danger; border-color: @danger; }
        """))
        btn_del.clicked.connect(lambda: self.page.confirm_delete(self.project['id'], self.project['name']))
        btn_row.addWidget(btn_del)

        layout.addLayout(btn_row)
