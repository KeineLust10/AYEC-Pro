# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QDateEdit, QDialog, QComboBox, QTextEdit, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QAbstractItemView,
    QGridLayout
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from src.utils.toast_notification import show_error, show_warning, show_info
from src.ui.styles.tab_styles import TAB_STYLE
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens



class RemindersPage(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(theme_qss('background: @window; color: @text;'))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(16)

        header = QLabel('Hatırlatıcı Yönetimi')
        header.setFont(QFont('Segoe UI', 18, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss('color: @text;'))
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.tabBar().setDocumentMode(True)
        self.tabs.tabBar().setExpanding(True)
        self.tabs.setStyleSheet(TAB_STYLE)

        self.tab_add = QWidget()
        self.setup_add_tab()
        self.tabs.addTab(self.tab_add, 'Hatırlatıcı Ekle')

        self.tab_list = QWidget()
        self.setup_list_tab()
        self.tabs.addTab(self.tab_list, 'Liste ve Düzenleme')

        layout.addWidget(self.tabs)
        self.load_personnel()
        self.load_reminders()

    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        lbl.setStyleSheet(theme_qss('color: @text;'))
        return lbl

    def _input_style(self):
        return theme_qss(
            'QLineEdit, QComboBox, QDateEdit, QTextEdit {'
            ' background: @surface; color: @text; border: 1px solid @border;'
            ' border-radius: 12px; padding: 10px 12px; font-size: 14px; }'
            'QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {'
            ' border: 1px solid @accent; background: @surface_alt; }'
            'QComboBox QAbstractItemView {'
            ' background: @surface; color: @text; selection-background-color: @selection_bg;'
            ' selection-color: @selection_text; }'
        )

    def setup_add_tab(self):
        layout = QVBoxLayout(self.tab_add)
        layout.setSpacing(18)
        layout.setContentsMargins(16, 20, 16, 16)

        form_group = QGroupBox('Yeni Hatırlatma Detayları')
        form_group.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        form_group.setStyleSheet(theme_qss(
            'QGroupBox {'
            ' color: @text; border: 1px solid @border; border-radius: 16px;'
            ' margin-top: 12px; padding-top: 18px; background: @surface; }'
            'QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }'
        ))
        form_layout = QVBoxLayout(form_group)
        form_layout.setContentsMargins(18, 24, 18, 18)
        form_layout.setSpacing(16)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(0, 6)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)

        self.inp_title = QLineEdit()
        self.inp_title.setPlaceholderText('Örn: Müşteri Araması')
        self.inp_title.setStyleSheet(self._input_style())
        self.inp_title.setMinimumHeight(44)

        self.cmb_personnel = QComboBox()
        self.cmb_personnel.setStyleSheet(self._input_style())
        self.cmb_personnel.setMinimumHeight(44)

        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDisplayFormat('dd.MM.yyyy')
        self.inp_date.setStyleSheet(self._input_style())
        self.inp_date.setMinimumHeight(44)

        grid.addWidget(self._field_label('Başlık'), 0, 0)
        grid.addWidget(self._field_label('İlgili Personel'), 0, 1)
        grid.addWidget(self._field_label('Tarih'), 0, 2)
        grid.addWidget(self.inp_title, 1, 0)
        grid.addWidget(self.cmb_personnel, 1, 1)
        grid.addWidget(self.inp_date, 1, 2)
        form_layout.addLayout(grid)

        form_layout.addWidget(self._field_label('Açıklama / Notlar'))
        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText('Hatırlatılacak konunun detaylarını buraya giriniz...')
        self.txt_desc.setStyleSheet(self._input_style())
        self.txt_desc.setMinimumHeight(140)
        form_layout.addWidget(self.txt_desc)

        layout.addWidget(form_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_add = QPushButton('Kaydet ve Ekle')
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setMinimumSize(220, 48)
        self.btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss('success', size='lg')))
        self.btn_add.clicked.connect(self.add_reminder)
        btn_layout.addWidget(self.btn_add)
        layout.addLayout(btn_layout)
        layout.addStretch()

    def setup_list_tab(self):
        layout = QVBoxLayout(self.tab_list)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(12)

        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton('Yenile')
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(theme_qss(DesignTokens.get_button_qss('secondary')))
        btn_refresh.clicked.connect(self.load_reminders)

        btn_delete = QPushButton('Seçili Olanı Sil')
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet(theme_qss(DesignTokens.get_button_qss('danger')))
        btn_delete.clicked.connect(self.delete_reminder)

        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_delete)
        layout.addLayout(btn_layout)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['ID', 'Başlık', 'Personel', 'Tarih', 'Açıklama', 'Durum'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        layout.addWidget(self.table)

    def load_personnel(self):
        self.cmb_personnel.clear()
        self.cmb_personnel.addItem('Genel (Herkes)', None)
        try:
            self.db.cursor.execute('SELECT id, name FROM personnel')
            for pid, name in self.db.cursor.fetchall():
                self.cmb_personnel.addItem(name, pid)
        except Exception:
            pass

    def add_reminder(self):
        title = self.inp_title.text().strip()
        pid = self.cmb_personnel.currentData()
        date_str = self.inp_date.date().toString('yyyy-MM-dd')
        desc = self.txt_desc.toPlainText().strip()

        if not title:
            show_warning(self, 'Lütfen bir başlık giriniz.')
            return

        success = self.db.add_reminder(title, pid, date_str, desc)
        if success:
            show_info(self, 'Hatırlatıcı sisteme eklendi.')
            self.load_reminders()
            self.inp_title.clear()
            self.txt_desc.clear()
            self.tabs.setCurrentIndex(1)
        else:
            show_error(self, 'Hatırlatıcı eklenirken veritabanı hatası oluştu.')

    def delete_reminder(self):
        row = self.table.currentRow()
        if row < 0:
            show_warning(self, 'Lütfen silinecek bir satır seçin.')
            return

        rem_id = self.table.item(row, 0).text()
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        dialog = SimpleConfirmDialog('Silme Onayı', 'Bu hatırlatıcıyı silmek istediğinize emin misiniz')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.db.cursor.execute('DELETE FROM reminders WHERE id=?', (rem_id,))
                self.db.conn.commit()
                self.load_reminders()
                show_info(self, 'Kayıt silindi.')
            except Exception as e:
                show_error(self, f'Silinemedi: {e}')

    def load_reminders(self):
        self.table.setRowCount(0)
        try:
            rows = self.db.get_reminders()
            for r, row in enumerate(rows):
                self.table.insertRow(r)
                def get_col(i):
                    return str(row[i]) if i < len(row) and row[i] is not None else ''
                self.table.setItem(r, 0, QTableWidgetItem(get_col(0)))
                self.table.setItem(r, 1, QTableWidgetItem(get_col(1)))
                self.table.setItem(r, 2, QTableWidgetItem(get_col(2)))
                self.table.setItem(r, 3, QTableWidgetItem(get_col(3)))
                self.table.setItem(r, 4, QTableWidgetItem(get_col(6)))
                self.table.setItem(r, 5, QTableWidgetItem(get_col(5)))
        except Exception as e:
            show_error(self, f'Hatırlatıcılar yüklenemedi: {e}')

    def _wire_ui_signals(self):
        self.cmb_personnel.currentIndexChanged.connect(self._on_ui_widget_changed)
