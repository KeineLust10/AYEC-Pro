# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QBoxLayout, QLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QHeaderView, QComboBox, QLineEdit, QFormLayout, QMessageBox, QFrame, QMenu,
                             QGraphicsDropShadowEffect, QAbstractItemView, QStyle, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QColor
from src.utils.message_helper import show_success, show_error, show_question
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.theme_colors import theme_qss
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.navigation_glyph import navigation_icon
import logging

logger = logging.getLogger("AYECProLogger")


class QuickNotesSettingsWidget(QWidget):

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_table_columns)

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """
    Hızlı Notlar Ayar Sayfası (Modern UI)
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self.load_notes()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.setMinimumSize(0, 0)
        self.page_layout = layout
        layout.setContentsMargins(30, 33, 30, 24)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header = QHBoxLayout()
        self.header_layout = header
        title_box = QVBoxLayout()
        title_box.setSpacing(13)
        title_row = QHBoxLayout()
        self.title_row_layout = title_row
        title_row.setSpacing(16)
        title_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lbl_title = QLabel("H\u0131zl\u0131 Notlar & Makrolar")
        lbl_title.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        lbl_title.setStyleSheet(theme_qss(
            "color: @text; font-size: 28px; font-weight: 800; border: none;"
        ))
        self.lbl_count = QLabel("0 \u015eablon Aktif")
        self.lbl_count.setStyleSheet(theme_qss(
            "color: @primary; background: @finance_surface_alt; "
            "border: 1px solid @finance_outline; border-radius: 14px; padding: 2px 10px; "
            "font-size: 12px; font-weight: 700;"
        ))
        self.lbl_count.setFixedHeight(28)
        self.lbl_count.setFixedWidth(130)
        title_row.addWidget(lbl_title)
        title_row.addWidget(self.lbl_count)
        title_box.addLayout(title_row)
        lbl_desc = QLabel(
            "Teknisyen paneli ve servis operasyon s\u00fcre\u00e7leri i\u00e7in "
            "haz\u0131r metin \u015fablonlar\u0131n\u0131 y\u00f6netin."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px; border: none;"))
        title_box.addWidget(lbl_desc)
        header.addLayout(title_box, 1)

        self.btn_refresh = QPushButton("\u27f3  Yenile")
        self.btn_add = QPushButton("+  Yeni Not Ekle")
        self.btn_add.setIcon(navigation_icon("plus", 16, "selection_text"))
        self.btn_add.setIconSize(QSize(16, 16))
        self.btn_refresh.setFixedHeight(42)
        self.btn_add.setFixedHeight(42)
        self.btn_refresh.setMinimumWidth(107)
        self.btn_add.setMinimumWidth(175)
        self.btn_refresh.setStyleSheet(theme_qss(
            "QPushButton { background: @surface; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 0 16px; font-weight: 600; } "
            "QPushButton:hover { background: @hover; border-color: @primary; }"
        ))
        self.btn_add.setStyleSheet(theme_qss(
            "QPushButton { background: @primary; color: @selection_text; border: 1px solid @primary; "
            "border-radius: 8px; padding: 0 18px; font-weight: 700; } "
            "QPushButton:hover { background: @primary_hover; }"
        ))
        self.btn_refresh.clicked.connect(self.load_notes)
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.header_actions = QHBoxLayout()
        self.header_actions.addWidget(self.btn_refresh)
        self.header_actions.addWidget(self.btn_add)
        header.addLayout(self.header_actions)
        layout.addLayout(header)
        layout.addSpacing(7)

        filter_frame = QFrame()
        self.filter_frame = filter_frame
        filter_frame.setFixedHeight(63)
        filter_frame.setStyleSheet(theme_qss(
            "QFrame { background: transparent; border: none; }"
        ))
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.filter_layout = filter_layout
        filter_layout.setContentsMargins(0, 25, 0, 0)
        filter_layout.setSpacing(10)
        filter_label = QLabel("Filtrele:")
        filter_label.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; border: none;"))
        filter_label.setFixedWidth(54)
        self.combo_filter = QComboBox()
        self.combo_filter.addItem("T\u00fcm Kategoriler")
        self.combo_filter.setMinimumWidth(310)
        self.combo_filter.setFixedHeight(38)
        self.combo_filter.setStyleSheet(theme_qss(
            "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 0 12px; } QComboBox:focus { border-color: @primary; }"
        ))
        self.combo_filter.currentIndexChanged.connect(self.load_notes)
        search_label = QLabel("Ara:")
        search_label.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; border: none;"))
        search_label.setFixedWidth(31)
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Notlarda ara...")
        self.inp_search.setFixedHeight(38)
        self.inp_search.setMaximumWidth(420)
        self.inp_search.addAction(
            navigation_icon("search", 16, "text_muted"), QLineEdit.ActionPosition.LeadingPosition
        )
        self.inp_search.setStyleSheet(theme_qss(
            "QLineEdit { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 0 12px 0 34px; } QLineEdit:focus { border-color: @primary; }"
        ))
        self.inp_search.textChanged.connect(self.load_notes)
        tag_label = QLabel("H\u0131zl\u0131 Etiketler:")
        self.tag_label = tag_label
        tag_label.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; border: none;"))
        tag_label.setFixedWidth(98)
        self.quick_tag_buttons = []
        self.category_filter_group = QWidget(filter_frame)
        category_group_layout = QHBoxLayout(self.category_filter_group)
        category_group_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        category_group_layout.setContentsMargins(0, 0, 0, 0)
        category_group_layout.setSpacing(8)
        category_group_layout.addWidget(filter_label)
        category_group_layout.addWidget(self.combo_filter, 1)
        self.search_filter_group = QWidget(filter_frame)
        search_group_layout = QHBoxLayout(self.search_filter_group)
        search_group_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        search_group_layout.setContentsMargins(0, 0, 0, 0)
        search_group_layout.setSpacing(8)
        search_group_layout.addWidget(search_label)
        search_group_layout.addWidget(self.inp_search, 1)
        self.quick_tags_group = QWidget(filter_frame)
        quick_tags_layout = QHBoxLayout(self.quick_tags_group)
        quick_tags_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        quick_tags_layout.setContentsMargins(0, 0, 0, 0)
        quick_tags_layout.setSpacing(6)
        quick_tags_layout.addWidget(tag_label)
        for tag in ("Ar\u0131za", "Test", "Aksesuar"):
            button = QPushButton("#" + tag)
            button.setFixedWidth({"Ar\u0131za": 64, "Test": 58, "Aksesuar": 92}[tag])
            button.setCheckable(True)
            button.setFixedHeight(34)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: transparent; color: @text; border: 1px solid @border; "
                "border-radius: 6px; padding: 0 10px; } "
                "QPushButton:checked { background: @selection_bg; color: @selection_text; "
                "border-color: @primary; }"
            ))
            button.clicked.connect(
                lambda checked, value=tag: self._apply_quick_tag(value if checked else "")
            )
            self.quick_tag_buttons.append(button)
            quick_tags_layout.addWidget(button)
        filter_layout.addWidget(self.category_filter_group)
        filter_layout.addWidget(self.search_filter_group, 1)
        filter_layout.addWidget(self.quick_tags_group)
        layout.addWidget(filter_frame)
        layout.addSpacing(27)

        table_frame = QFrame()
        self.table_frame = table_frame
        table_frame.setStyleSheet(theme_qss(
            "QFrame { background: @surface; border: 1px solid @border; border-radius: 14px; }"
        ))
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)
        table_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.table = QTableWidget()
        self.table.setMinimumWidth(0)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "KATEGOR\u0130", "NOT \u0130\u00c7ER\u0130\u011e\u0130", "SIRA", "DURUM", "\u0130\u015eLEMLER"
        ])
        self.table.setStyleSheet(theme_qss("""
            QTableWidget { border: none; background: transparent; "
                selection-background-color: @selection_bg; selection-color: @selection_text; }
            QTableWidget::item { padding: 10px; border-bottom: none; font-size: 14px; }
            QHeaderView::section { background: @surface_alt; color: @text_muted; border: none; "
                border-bottom: 1px solid @border; padding: 14px 12px; font-size: 12px; font-weight: 700; }
        """))
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 72)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 120)
        header_view.setMinimumHeight(52)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._row_separators = []
        self.table.verticalScrollBar().valueChanged.connect(self._position_row_separators)
        self.table.horizontalScrollBar().valueChanged.connect(self._position_row_separators)
        self.table.doubleClicked.connect(self.open_edit_dialog)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        table_layout.addWidget(self.table)
        layout.addWidget(table_frame)
        self._quick_tag = ""
        self._apply_table_columns()

    def _apply_table_columns(self):
        if not hasattr(self, "table"):
            return
        width = max(0, self.table.viewport().width())
        category_width = min(402, max(210, int(width * 0.33)))
        self.table.setColumnWidth(1, category_width)
        self.table.setColumnWidth(
            2, max(160, width - 72 - category_width - 80 - 130 - 120)
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "filter_layout"):
            self._apply_table_columns()
            return
        compact = self.width() < 1000
        mobile = self.width() < 700
        self.page_layout.setContentsMargins(12, 14, 12, 14) if mobile else self.page_layout.setContentsMargins(30, 33, 30, 24)
        self.page_layout.setSpacing(12 if mobile else 20)
        self.header_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if mobile
            else QBoxLayout.Direction.LeftToRight
        )
        self.header_layout.setStretch(0, 0 if mobile else 1)
        self.header_layout.setStretch(1, 0)
        self.title_row_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if mobile
            else QBoxLayout.Direction.LeftToRight
        )
        self.header_actions.setDirection(
            QBoxLayout.Direction.LeftToRight
        )
        self.header_actions.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.filter_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if mobile
            else QBoxLayout.Direction.LeftToRight
        )
        self.filter_frame.setFixedHeight(142 if mobile else 63)
        self.filter_layout.setContentsMargins(0, 8 if mobile else 25, 0, 0)
        self.filter_layout.setSpacing(6 if mobile else 10)
        self.inp_search.setMinimumWidth(0)
        self.combo_filter.setMinimumWidth(154 if compact else 310)
        self.filter_layout.setSpacing(6 if compact else 10)
        self.combo_filter.setMinimumWidth(154 if compact else 310)
        self.tag_label.setFixedWidth(80 if compact else 98)
        for button, width in zip(self.quick_tag_buttons, (64, 58, 82) if compact else (64, 58, 92)):
            button.setFixedWidth(width)
        table_height = 52 + self.table.rowCount() * 61 + 4
        if self.height() < 1000:
            available_height = max(320, self.height() - 240)
            self.table.setMinimumHeight(0)
            self.table.setMaximumHeight(available_height)
            self.table_frame.setMinimumHeight(0)
            self.table_frame.setMaximumHeight(available_height + 2)
        else:
            self.table.setFixedHeight(table_height)
            self.table_frame.setFixedHeight(table_height + 2)
        self._apply_table_columns()
        self._position_row_separators()

    def _apply_quick_tag(self, tag):
        self._quick_tag = str(tag or "")
        for button in self.quick_tag_buttons:
            button.blockSignals(True)
            button.setChecked(button.text().lstrip("#") == self._quick_tag)
            button.blockSignals(False)
        self.load_notes()

    def load_notes(self):
        for separator in self._row_separators:
            separator.deleteLater()
        self._row_separators = []
        self.table.setRowCount(0)
        self._notes_by_id = {}
        try:
            notes = list(self.db.get_fast_notes() or [])
        except Exception as exc:
            logger.error("Quick notes load error: %s", exc)
            notes = []

        categories = sorted({
            str(row[5] or row[1] or "Genel") if len(row) > 5 else str(row[1] or "Genel")
            for row in notes
        })
        selected_category = self.combo_filter.currentText()
        self.combo_filter.blockSignals(True)
        self.combo_filter.clear()
        self.combo_filter.addItem("T\u00fcm Kategoriler")
        self.combo_filter.addItems(categories)
        if selected_category in categories:
            self.combo_filter.setCurrentText(selected_category)
        else:
            self.combo_filter.setCurrentIndex(0)
        self.combo_filter.blockSignals(False)
        category_filter = self.combo_filter.currentText()
        if category_filter == "T\u00fcm Kategoriler":
            category_filter = ""
        search_txt = self.inp_search.text().lower().strip()
        quick_tag = str(getattr(self, "_quick_tag", "") or "").lower()
        active_count = 0

        for note in notes:
            n_id, n_cat, n_label, n_active, n_order = note[:5]
            self._notes_by_id[n_id] = tuple(note)
            display_category = str(note[5] or "") if len(note) > 5 else ""
            title = str(note[6] or "") if len(note) > 6 else ""
            display_category = display_category or str(n_cat or "Genel")
            if n_active:
                active_count += 1
            if category_filter and display_category != category_filter:
                continue
            haystack = " ".join((str(n_cat), display_category, title, str(n_label))).lower()
            if search_txt and search_txt not in haystack:
                continue
            if quick_tag and quick_tag not in haystack:
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            id_item = QTableWidgetItem(str(n_id))
            id_item.setData(Qt.ItemDataRole.UserRole, n_id)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)

            category_cell = QWidget()
            category_cell.setStyleSheet("background: transparent; border: none;")
            category_layout = QHBoxLayout(category_cell)
            category_layout.setContentsMargins(10, 0, 8, 0)
            category_layout.setSpacing(8)
            category_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            badge = QLabel(display_category)
            badge.setFixedHeight(28)
            badge_style = (
                "@finance_breadcrumb_active" if "telefon" in display_category.lower()
                else "#c084fc" if "g\u00fcvenlik" in display_category.lower()
                else "@primary"
            )
            badge.setStyleSheet(theme_qss(
                f"color: {badge_style}; background: @finance_surface_alt; border: 1px solid @finance_outline; "
                "border-radius: 5px; padding: 4px 6px; font-size: 12px; font-weight: 700;"
            ))
            category_layout.addWidget(badge)
            if title:
                separator = QLabel("::")
                separator.setStyleSheet(theme_qss("color: @text_muted; border: none;"))
                category_layout.addWidget(separator)
                title_label = QLabel(title)
                title_label.setMaximumHeight(30)
                title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                title_label.setStyleSheet(theme_qss("color: @text; border: none; font-size: 14px; font-weight: 600;"))
                category_layout.addWidget(title_label)
            category_layout.addStretch(1)
            self.table.setCellWidget(row, 1, category_cell)
            content_item = QTableWidgetItem("")
            content_upper = str(n_label or "").upper()
            content_color = "@text"
            if "KIRIK" in content_upper:
                content_color = "#fb7185"
            elif "KAMERA" in content_upper:
                content_color = "#fbbf24"
            self.table.setItem(row, 2, content_item)
            content_label = QLabel(str(n_label or ""))
            content_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            content_label.setStyleSheet(theme_qss(
                f"color: {content_color}; border: none; "
                "padding-left: 10px; font-size: 14px; font-weight: 600;"
            ))
            self.table.setCellWidget(row, 2, content_label)
            order_item = QTableWidgetItem(str(n_order or 0))
            order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, order_item)
            self.table.setItem(row, 4, QTableWidgetItem(""))
            status_cell = QWidget()
            status_cell.setStyleSheet("background: transparent; border: none;")
            status_layout = QHBoxLayout(status_cell)
            status_layout.setContentsMargins(15, 0, 8, 0)
            status_layout.setSpacing(12)
            status_label = QLabel("Aktif" if n_active else "Pasif")
            status_label.setStyleSheet(theme_qss(
                "color: @success; border: none; font-weight: 700;"
                if n_active else "color: @danger; border: none; font-weight: 700;"
            ))
            toggle = AnimatedToggle()
            toggle.setFixedSize(42, 24)
            toggle.setChecked(bool(n_active))
            toggle.stateChanged.connect(
                lambda state, nid=n_id, label=status_label: self.on_toggle_change(nid, state, label)
            )
            status_layout.addWidget(status_label)
            status_layout.addWidget(toggle)
            status_layout.addStretch(1)
            self.table.setCellWidget(row, 4, status_cell)

            self.table.setItem(row, 5, QTableWidgetItem(""))
            actions = QWidget()
            actions.setStyleSheet("background: transparent; border: none;")
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(2, 0, 4, 0)
            action_layout.setSpacing(4)
            edit_button = QPushButton()
            delete_button = QPushButton()
            edit_button.setIcon(navigation_icon("pencil", 16))
            delete_button.setIcon(navigation_icon("trash", 16))
            for button, tooltip in ((edit_button, "D\u00fczenle"), (delete_button, "Sil")):
                button.setToolTip(tooltip)
                button.setFixedSize(30, 30)
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: transparent; color: @text_muted; border: 1px solid transparent; "
                    "border-radius: 5px; font-size: 15px; } "
                    "QPushButton:hover { background: @surface_alt; color: @text; border-color: @border; }"
                ))
            edit_button.clicked.connect(lambda _checked=False, target=row: self._edit_row(target))
            delete_button.clicked.connect(lambda _checked=False, target=row: self._delete_row(target))
            action_layout.addWidget(edit_button)
            action_layout.addWidget(delete_button)
            self.table.setCellWidget(row, 5, actions)
            self.table.setRowHeight(row, 61)
            separator = QFrame(self.table.viewport())
            separator.setFixedHeight(1)
            separator.setStyleSheet(theme_qss("background: @border; border: none;"))
            separator.show()
            separator.raise_()
            self._row_separators.append(separator)

        self._position_row_separators()
        self._apply_table_columns()
        table_height = 52 + self.table.rowCount() * 61 + 4
        if self.height() < 1000:
            available_height = max(320, self.height() - 240)
            self.table.setMinimumHeight(0)
            self.table.setMaximumHeight(available_height)
            self.table_frame.setMinimumHeight(0)
            self.table_frame.setMaximumHeight(available_height + 2)
        else:
            self.table.setFixedHeight(table_height)
            self.table_frame.setFixedHeight(table_height + 2)
        self.lbl_count.setText(f"{active_count} \u015eablon Aktif")

    def _position_row_separators(self, *_args):
        if not self._row_separators:
            return
        model = self.table.model()
        for row, separator in enumerate(self._row_separators):
            if row >= model.rowCount():
                separator.hide()
                continue
            rect = self.table.visualRect(model.index(row, 0))
            separator.setGeometry(0, rect.bottom(), self.table.viewport().width(), 1)
            separator.setVisible(rect.intersects(self.table.viewport().rect()))
            separator.raise_()

    def _edit_row(self, row):
        self.table.setCurrentCell(row, 0)
        self.open_edit_dialog()

    def _delete_row(self, row):
        self.table.setCurrentCell(row, 0)
        self.delete_note()

    def on_toggle_change(self, note_id, state, lbl_status):
        is_active = 1 if state == Qt.CheckState.Checked else 0
        
        # Update Label UI immediately
        if is_active:
            lbl_status.setText("Aktif")
            lbl_status.setStyleSheet(theme_qss("color: @success; margin-left: 8px; font-weight: 700;"))
        else:
            lbl_status.setText("Pasif")
            lbl_status.setStyleSheet(theme_qss("color: @danger; margin-left: 8px; font-weight: 700;"))
            
        # Update DB
        try:
            self.db.cursor.execute("UPDATE fast_notes SET is_active=? WHERE id=?", (is_active, note_id))
            self.db.conn.commit()
        except Exception as e:
            logger.error("Quick notes toggle update error: %s", e)

    def open_add_dialog(self):
        dlg = QuickNoteDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            try:
                self.db.add_fast_note(
                    data['category'], data['label'], data['is_active'], data['order'],
                    data['display_category'], data['title'],
                )
                self.load_notes()
                show_success(self, "Başarılı", "Not eklendi.")
            except Exception as e:
                show_error(self, "Hata", str(e))

    def open_edit_dialog(self):
        row = self.table.currentRow()
        if row < 0:
            return
        
        n_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        note = self._notes_by_id.get(n_id, ())
        n_cat = note[1] if len(note) > 1 else ""
        n_label = note[2] if len(note) > 2 else ""
        n_order = int(note[4] or 0) if len(note) > 4 else 0
        display_category = note[5] if len(note) > 5 else ""
        title = note[6] if len(note) > 6 else ""
        
        # Get active status from toggle widget
        container = self.table.cellWidget(row, 4)
        toggle = container.findChild(AnimatedToggle)
        n_active = 1 if toggle.isChecked() else 0
        
        note_data = (n_id, n_cat, n_label, n_active, n_order, display_category, title)
        
        dlg = QuickNoteDialog(self, note_data)
        if dlg.exec():
            data = dlg.get_data()
            try:
                self.db.update_fast_note(
                    n_id, data['label'], data['is_active'], data['category'], data['order'],
                    data['display_category'], data['title'],
                )
                self.load_notes()
                show_success(self, "Başarılı", "Not güncellendi.")
            except Exception as e:
                show_error(self, "Hata", str(e))

    def open_context_menu(self, pos):
        if not is_context_menu_enabled(self.db):
            return
        menu = QMenu()
        menu.addAction("✏️ Düzenle", self.open_edit_dialog)
        menu.addAction("🗑️ Sil", self.delete_note)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_note(self):
        row = self.table.currentRow()
        if row < 0:
            return
        
        n_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        confirm = show_question(self, "Onay", "Bu notu silmek istediğinize emin misiniz")
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_fast_note(n_id)
                self.load_notes()
                show_success(self, "Başarılı", "Not silindi.")
            except Exception as e:
                show_error(self, "Hata", str(e))

class QuickNoteDialog(ModernDialog):
    def __init__(self, parent=None, note_data=None):
        super().__init__("H\u0131zl\u0131 Not Detay\u0131", parent=parent, width=680, height=760)
        self.note_data = note_data
        self.setup_ui()
        if note_data:
            self.populate()

    def setup_ui(self):
        self.content_layout.setContentsMargins(30, 24, 30, 24)
        self.content_layout.setSpacing(16)
        title = QLabel("H\u0131zl\u0131 Not\u0131 D\u00fczenle / Ekle")
        title.setStyleSheet(theme_qss(
            "color: @text; background: transparent; border: none; font-size: 20px; font-weight: 800;"
        ))
        description = QLabel(
            "Servis ak\u0131\u015f\u0131ndaki kategori, ba\u015fl\u0131k ve not i\u00e7eri\u011fini d\u00fczenleyin."
        )
        description.setWordWrap(True)
        description.setStyleSheet(theme_qss(
            "color: @text_muted; background: transparent; border: none;"
        ))
        self.content_layout.addWidget(title)
        self.content_layout.addWidget(description)

        form = QFormLayout()
        form.setVerticalSpacing(14)
        form.setHorizontalSpacing(18)
        self.cmb_cat = QComboBox()
        self.cmb_cat.addItems(["Ar\u0131za Notu", "\u0130\u015flem Detay\u0131", "Gizli Not"])
        self.cmb_cat.setEditable(True)
        self.cmb_cat.setFixedHeight(42)
        form.addRow("Servis Ak\u0131\u015f Kategorisi:", self.cmb_cat)

        self.cmb_display_category = QComboBox()
        self.cmb_display_category.addItems([
            "Bilgisayar", "Cep Telefonu", "G\u00fcvenlik Sistemleri"
        ])
        self.cmb_display_category.setEditable(True)
        self.cmb_display_category.setFixedHeight(42)
        form.addRow("G\u00f6r\u00fcnen Kategori:", self.cmb_display_category)

        self.inp_title = QLineEdit()
        self.inp_title.setPlaceholderText("\u015eablon ba\u015fl\u0131\u011f\u0131...")
        self.inp_title.setFixedHeight(42)
        form.addRow("Ba\u015fl\u0131k:", self.inp_title)

        self.inp_label = QLineEdit()
        self.inp_label.setPlaceholderText("Not i\u00e7eri\u011fini yaz\u0131n...")
        self.inp_label.setFixedHeight(42)
        form.addRow("Not \u0130\u00e7eri\u011fi:", self.inp_label)

        self.inp_order = QLineEdit("0")
        self.inp_order.setFixedHeight(42)
        form.addRow("S\u0131ralama:", self.inp_order)

        active_row = QHBoxLayout()
        self.toggle_active = AnimatedToggle()
        self.toggle_active.setChecked(True)
        self.toggle_active.setFixedSize(50, 26)
        self.lbl_active = QLabel("Aktif")
        self.lbl_active.setStyleSheet(theme_qss(
            "color: @success; background: transparent; border: none; font-weight: 700;"
        ))
        active_row.addWidget(self.lbl_active)
        active_row.addWidget(self.toggle_active)
        active_row.addStretch(1)
        form.addRow("Durum:", active_row)
        self.content_layout.addLayout(form)
        self.content_layout.addStretch(1)

        self.btn_cancel = self.add_button("\u0130ptal", "secondary", self.reject)
        self.btn_save = self.add_button("Kaydet", "primary", self.accept)
        self.set_footer_visible(True, 80)

    # Allow dragging the frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def populate(self):
        # (id, category, content, active, order, display_category, title)
        idx = self.cmb_cat.findText(self.note_data[1])
        if idx >= 0:
            self.cmb_cat.setCurrentIndex(idx)
        else:
            self.cmb_cat.setCurrentText(self.note_data[1])
        
        self.inp_label.setText(self.note_data[2])
        self.toggle_active.setChecked(bool(self.note_data[3]))
        self.inp_order.setText(str(self.note_data[4]))
        if len(self.note_data) > 5:
            value = str(self.note_data[5] or "")
            if self.cmb_display_category.findText(value) < 0:
                self.cmb_display_category.addItem(value)
            self.cmb_display_category.setCurrentText(value)
        if len(self.note_data) > 6:
            self.inp_title.setText(str(self.note_data[6] or ""))

    def get_data(self):
        return {
            'category': self.cmb_cat.currentText(),
            'label': self.inp_label.text(),
            'is_active': 1 if self.toggle_active.isChecked() else 0,
            'order': int(self.inp_order.text() or 0),
            'display_category': self.cmb_display_category.currentText(),
            'title': self.inp_title.text(),
        }
