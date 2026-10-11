# -*- coding: utf-8 -*-

import os
import re
from datetime import datetime

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QScrollArea, QFrame, QWidget,
                             QListWidget, QListWidgetItem, QAbstractItemView, QComboBox,
                             QFileDialog, QLineEdit, QSplitter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from src.utils.theme_colors import theme_qss, tc
from PyQt6.QtGui import QFont, QColor, QIcon, QAction, QTextCharFormat, QTextCursor, QTextListFormat
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.logger import logger
from src.utils.toast_notification import show_success, show_error

class FilterButton(QPushButton):
    def __init__(self, text, type_val, parent=None):
        super().__init__(text, parent)
        self.type_val = type_val
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)
        self.setCheckable(True)
        self.update_style(False)

    def update_style(self, active):
        if active:
            self.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @accent;
                    color: white;
                    border-radius: 6px;
                    padding: 0 10px;
                    font-weight: bold;
                    font-size: 9px;
                    border: none;
                }
            """))
        else:
            self.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @surface_alt;
                    color: @text_muted;
                    border: 1px solid @border;
                    border-radius: 6px;
                    padding: 0 10px;
                    font-weight: 500;
                    font-size: 9px;
                }
                QPushButton:hover {
                    background-color: @border;
                }
            """))

class CustomerNoteCard(QWidget):
    deleted = pyqtSignal(int)
    open_requested = pyqtSignal(object)
    pdf_requested = pyqtSignal(object)
    
    def __init__(self, note_data, parent=None):
        super().__init__(parent)
        self.note_data = tuple(note_data) if note_data is not None else tuple()
        self.note_id = note_data[0]
        self.note_type = note_data[1]
        self.title = note_data[2] if len(note_data) >= 5 else ""
        self.content = note_data[3] if len(note_data) >= 5 else note_data[2]
        self.date = note_data[4] if len(note_data) >= 5 else note_data[3]
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        
        container = QFrame()
        container.setObjectName("NoteContainer")
        container.setStyleSheet(theme_qss("""
            QFrame#NoteContainer {
                background-color: white;
                border: 1px solid @border;
                border-radius: 12px;
            }
        """))
        
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(15, 12, 15, 12)
        c_layout.setSpacing(8)
        
        # Header Row
        h_row = QHBoxLayout()
        
        # Type Badge
        icon = "📝"
        color = tc("accent")
        bg_color = tc("selection_bg")
        
        if self.note_type == "WhatsApp Mesajı":
            icon = "📱"
            color = tc("success")
            bg_color = tc("success_bg")
        elif self.note_type == "SMS":
            icon = "📩"
            color = tc("warning")
            bg_color = tc("warning_bg")
        elif self.note_type == "Telefon Görüşmesi":
            icon = "📞"
            color = tc("accent")
            bg_color = tc("selection_bg")
        elif self.note_type == "E-Posta":
            icon = "✉️"
            color = tc("danger")
            bg_color = tc("surface_alt")
        elif self.note_type in ("Teklif", "PC Teklif"):
            icon = "📋"
            color = tc("accent")
            bg_color = tc("selection_bg")

        display_title = self.title or self.date or "Not"
        lbl_type = QLabel(f"{icon} {display_title}")
        lbl_type.setStyleSheet(theme_qss(f"""
            color: {color}; 
            background-color: {bg_color}; 
            padding: 4px 10px; 
            border-radius: 12px; 
            font-weight: bold; 
            font-size: 11px;
        """))
        
        lbl_date = QLabel(self.date)
        lbl_date.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px;"))

        is_offer = self.note_type in ("Teklif", "PC Teklif")

        btn_open = QPushButton("Aç")
        btn_open.setFixedHeight(24)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setStyleSheet(theme_qss("""
            QPushButton {
                background: @accent;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 800;
            }
        """))
        btn_open.clicked.connect(lambda: self.open_requested.emit(self.note_data))
        btn_open.setVisible(is_offer)

        btn_pdf = QPushButton("PDF")
        btn_pdf.setFixedHeight(24)
        btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pdf.setStyleSheet(theme_qss("""
            QPushButton {
                background: @success;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 800;
            }
        """))
        btn_pdf.clicked.connect(lambda: self.pdf_requested.emit(self.note_data))
        btn_pdf.setVisible(is_offer)
        
        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(24, 24)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(theme_qss("QPushButton { border: none; background: transparent; color: @disabled_text; } QPushButton:hover { color: @danger; }"))
        btn_del.clicked.connect(lambda: self.deleted.emit(self.note_id))
        
        h_row.addWidget(lbl_type)
        h_row.addStretch()
        h_row.addWidget(lbl_date)
        h_row.addWidget(btn_open)
        h_row.addWidget(btn_pdf)
        h_row.addWidget(btn_del)
        
        c_layout.addLayout(h_row)
        
        # Content
        lbl_content = QLabel(self.content)
        lbl_content.setWordWrap(True)
        lbl_content.setStyleSheet(theme_qss("color: @text; font-size: 13px; line-height: 1.4;"))
        c_layout.addWidget(lbl_content)

        if self.note_type in ("Teklif", "PC Teklif"):
            lbl_hint = QLabel("Bu teklif kaydını Aç, PDF veya Sil butonlarıyla yönetebilirsiniz.")
            lbl_hint.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-style: italic;"))
            c_layout.addWidget(lbl_hint)
        
        layout.addWidget(container)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.note_data)
        super().mouseDoubleClickEvent(event)


class OfferPreviewDialog(BaseModernDialog):
    deleted = pyqtSignal(int)

    def __init__(self, db, note_data, parent=None):
        self.db = db
        self.note_data = note_data
        self.note_id = note_data[0]
        self.note_type = note_data[1]
        self.title = note_data[2] if len(note_data) >= 5 else ""
        self.content = note_data[3] if len(note_data) >= 5 else note_data[2] or ""
        self.created_at = note_data[4] if len(note_data) >= 5 else note_data[3] or ""
        dialog_title = "Teklif Önizleme" if self.note_type in ("Teklif", "PC Teklif") else "Not Detayı"
        super().__init__(parent, title=dialog_title, width=980, height=760)
        self._build_ui()

    def _extract_offer_no(self):
        match = re.search(r"No:\s*([A-Z0-9-]+)", self.content)
        return match.group(1) if match else f"NOT-{self.note_id}"

    def _build_ui(self):
        info_card = QFrame()
        info_card.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 14px;
            }
        """))
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(18, 14, 18, 14)
        info_layout.setSpacing(16)

        offer_no = self._extract_offer_no()
        lbl_offer = QLabel(f"Teklif No: {offer_no}")
        lbl_offer.setStyleSheet(theme_qss("font-size: 16px; font-weight: 900; color: @text;"))
        lbl_type = QLabel(f"Tür: {self.note_type}")
        lbl_type.setStyleSheet(theme_qss("font-size: 13px; font-weight: 700; color: @accent;"))
        lbl_date = QLabel(f"Kayıt: {self.created_at}")
        lbl_date.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))

        info_layout.addWidget(lbl_offer)
        info_layout.addWidget(lbl_type)
        info_layout.addStretch()
        info_layout.addWidget(lbl_date)
        self.content_layout.addWidget(info_card)

        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setPlainText(self.content)
        self.txt_preview.setStyleSheet(theme_qss("""
            QTextEdit {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 14px;
                padding: 14px;
                font-size: 13px;
            }
        """))
        self.content_layout.addWidget(self.txt_preview, 1)

        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_pdf = QPushButton("PDF G\u00f6r / Kaydet")
        self.btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pdf.setStyleSheet(theme_qss("""
            QPushButton {
                background: @accent;
                color: @selection_text;
                border: none;
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: 800;
            }
        """))
        self.btn_pdf.clicked.connect(self._export_pdf)

        btn_delete = QPushButton("Sil")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet(theme_qss("""
            QPushButton {
                background: @danger;
                color: @selection_text;
                border: none;
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: 800;
            }
        """))
        btn_delete.clicked.connect(self._delete_note)

        btn_close = QPushButton("Kapat")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: 800;
            }
        """))
        btn_close.clicked.connect(self.accept)

        actions.addWidget(self.btn_pdf)
        actions.addWidget(btn_delete)
        actions.addWidget(btn_close)
        self.content_layout.addLayout(actions)

    def _export_pdf(self):
        offer_no = self._extract_offer_no()
        default_name = f"Teklif_{offer_no}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Teklif PDF Kaydet",
            default_name,
            "PDF Dosyalar\u0131 (*.pdf)",
        )
        if not save_path:
            return
        try:
            from src.ui.utils.background_task import run_cancellable_task

            note_type = self.note_type
            created_at = self.created_at
            content_lines = tuple(self.content.splitlines())
            self.btn_pdf.setEnabled(False)

            def produce_pdf(is_cancelled):
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import cm
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

                if is_cancelled():
                    return None
                doc = SimpleDocTemplate(
                    save_path,
                    pagesize=A4,
                    rightMargin=1.5 * cm,
                    leftMargin=1.5 * cm,
                    topMargin=1.5 * cm,
                    bottomMargin=1.5 * cm,
                )
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    "OfferTitle",
                    parent=styles["Heading1"],
                    fontSize=18,
                    leading=22,
                )
                body_style = ParagraphStyle(
                    "OfferBody",
                    parent=styles["BodyText"],
                    fontSize=10,
                    leading=14,
                )
                story = [
                    Paragraph(f"Teklif Kayd\u0131 - {offer_no}", title_style),
                    Spacer(1, 10),
                    Paragraph(f"Kay\u0131t T\u00fcr\u00fc: {note_type}", body_style),
                    Paragraph(f"Kay\u0131t Tarihi: {created_at}", body_style),
                    Spacer(1, 12),
                ]
                for line in content_lines:
                    if is_cancelled():
                        return None
                    safe_line = (
                        line.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    story.append(
                        Paragraph(
                            safe_line if safe_line.strip() else "&nbsp;",
                            body_style,
                        )
                    )
                doc.build(story)
                return save_path

            def pdf_ready(result_path):
                if not result_path:
                    return
                try:
                    os.startfile(result_path)
                except OSError:
                    pass
                show_success(self, "Teklif PDF olarak olu\u015fturuldu.")

            run_cancellable_task(
                owner=self,
                title="Teklif PDF olusturuluyor",
                target=produce_pdf,
                on_success=pdf_ready,
                on_error=lambda message: show_error(
                    self,
                    f"PDF olu\u015fturulamad\u0131: {message}",
                ),
                on_done=lambda: self.btn_pdf.setEnabled(True),
                output_path=save_path,
            )
        except Exception as e:
            self.btn_pdf.setEnabled(True)
            logger.error("Offer PDF export error: %s", e)
            show_error(self, f"PDF olu\u015fturulamad\u0131: {e}")

    def export_pdf_to_path(self):
        self._export_pdf()

    def _delete_note(self):
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        dlg = SimpleConfirmDialog(self, title="Sil", text="Bu teklif kaydını silmek istiyor musunuz", ok_text="Sil", cancel_text="İptal", btn_color=tc("danger"))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.db.delete_customer_note(self.note_id)
            self.deleted.emit(self.note_id)
            self.accept()

class CustomerNotesDialog(BaseModernDialog):
    def __init__(self, db, customer_id, customer_name, parent=None):
        self.db = db
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.current_filter = "Tümü"
        
        super().__init__(parent, title="M\u00fc\u015fteri Notlar\u0131", width=864, height=840)
        
        self.setup_modern_content_clean()
        self.load_notes()

    def setup_modern_content_clean(self):
        """Build the split note-history and rich-text editor layout."""
        self.header.setFixedHeight(48)
        header_layout = self.header.layout()
        header_layout.setContentsMargins(16, 0, 14, 0)
        header_layout.removeWidget(self.lbl_title)
        header_layout.insertWidget(1, self.lbl_title)
        self.lbl_title.setStyleSheet(theme_qss(
            "font-size: 12px; font-weight: 800; color: @text;"
        ))
        customer_badge = QLabel(
            "{}   ID: #C-{}".format(self.customer_name, str(self.customer_id).zfill(4))
        )
        customer_badge.setStyleSheet(theme_qss(
            "font-size: 9px; color: @text_muted; padding-left: 8px;"
        ))
        header_layout.insertWidget(2, customer_badge)
        header_subtitle = QLabel(
            "M\u00fc\u015fteri etkile\u015fim ge\u00e7mi\u015fi ve dahili teknik not kay\u0131tlar\u0131"
        )
        header_subtitle.setStyleSheet(theme_qss(
            "font-size: 8px; color: @text_muted; padding-left: 8px;"
        ))
        header_layout.insertWidget(3, header_subtitle, 1)
        minimize_button = QPushButton("\u2014")
        minimize_button.setFixedSize(24, 24)
        minimize_button.setAccessibleName("Minimize")
        minimize_button.setCursor(Qt.CursorShape.PointingHandCursor)
        minimize_button.setStyleSheet(theme_qss(
            "QPushButton { background: transparent; color: @text_muted; "
            "border: 1px solid @border; border-radius: 4px; font-size: 10px; }"
        ))
        minimize_button.clicked.connect(self.showMinimized)
        header_layout.insertWidget(max(0, header_layout.count() - 1), minimize_button)

        filter_frame = QFrame()
        filter_lay = QHBoxLayout(filter_frame)
        filter_lay.setContentsMargins(0, 0, 0, 0)
        filter_lay.setSpacing(6)
        self.filter_buttons = []
        for text, value in (("T\u00fcm\u00fc", "T\u00fcm\u00fc"), ("Genel Not", "Genel Not"),
                            ("WhatsApp", "WhatsApp Mesaj\u0131"), ("SMS", "SMS"),
                            ("Telefon", "Telefon G\u00f6r\u00fc\u015fmesi"), ("E-Posta", "E-Posta"),
                            ("Teklif", "PC Teklif")):
            button = FilterButton(text, value)
            button.clicked.connect(lambda _checked=False, b=button: self.set_filter(b))
            button.setChecked(text == "T\u00fcm\u00fc")
            button.update_style(text == "T\u00fcm\u00fc")
            filter_lay.addWidget(button)
            self.filter_buttons.append(button)
        filter_lay.addStretch(1)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Notlarda ara...")
        self.search_input.setFixedSize(168, 30)
        self.search_input.setStyleSheet(theme_qss(
            "QLineEdit { background: @surface; color: @text; border: 1px solid @border; "
            "border-radius: 7px; padding: 0 10px; font-size: 10px; } "
            "QLineEdit:focus { border-color: @accent; }"
        ))
        self.search_input.textChanged.connect(self.load_notes)
        filter_lay.addWidget(self.search_input)
        self.content_layout.addWidget(filter_frame)
        self.content_layout.setContentsMargins(9, 4, 16, 0)
        self.content_layout.setSpacing(12)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)

        history_panel = QFrame()
        history_panel.setObjectName("noteHistoryPanel")
        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(14)
        history_header = QHBoxLayout()
        history_title = QLabel("Kay\u0131t Ge\u00e7mi\u015fi")
        history_title.setStyleSheet(theme_qss(
            "font-size: 10px; font-weight: 700; color: @text_muted;"
        ))
        self.notes_count_label = QLabel("0 Kay\u0131t Listelendi")
        self.notes_count_label.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 9px; color: @text_muted;"
        ))
        history_header.addWidget(history_title)
        history_header.addStretch(1)
        history_header.addWidget(self.notes_count_label)
        history_layout.addLayout(history_header)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("NotesList")
        self.list_widget.setMinimumWidth(245)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setStyleSheet(theme_qss("""
            QListWidget#NotesList { background: @surface_alt; border: 1px solid @border; border-radius: 8px; outline: none; }
            QListWidget::item { min-height: 82px; padding: 10px; margin: 3px; border: 1px solid @border; border-radius: 8px; color: @text; background: @surface; }
            QListWidget::item:selected { background: #102649; border: 1px solid @accent; border-left: 3px solid @accent; color: @text; }
        """))
        self.list_widget.itemClicked.connect(self._open_selected_note)
        history_layout.addWidget(self.list_widget, 1)
        self.splitter.addWidget(history_panel)

        self.editor_panel = QFrame()
        self.editor_panel.setObjectName("noteEditorPanel")
        editor_layout = QVBoxLayout(self.editor_panel)
        editor_layout.setContentsMargins(14, 9, 0, 0)
        editor_layout.setSpacing(6)
        title_row = QHBoxLayout()
        title_label = QLabel("Not Ba\u015fl\u0131\u011f\u0131  *")
        title_label.setStyleSheet(theme_qss("font-size: 10px; font-weight: 700; color: @text_muted;"))
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        self.date_label = QLabel("Yeni not - tarih kay\u0131tta otomatik olu\u015fturulacak")
        self.date_label.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 9px; color: @text_muted;"
        ))
        title_row.addWidget(self.date_label)
        editor_layout.addLayout(title_row)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Not ba\u015fl\u0131\u011f\u0131")
        self.title_edit.setFixedHeight(34)
        self.title_edit.setStyleSheet(theme_qss(
            "QLineEdit { font-size: 12px; padding: 0 10px; background: @surface; color: @text; "
            "border: 1px solid @border; border-radius: 7px; } "
            "QLineEdit:focus { border-color: @accent; }"
        ))
        editor_layout.addWidget(self.title_edit)

        toolbar = QFrame()
        toolbar.setObjectName("noteToolbar")
        toolbar.setStyleSheet(theme_qss(
            "QFrame#noteToolbar { background: @surface_alt; border: 1px solid @border; "
            "border-radius: 7px 7px 0 0; }"
        ))
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(7, 3, 7, 3)
        toolbar_layout.setSpacing(4)
        self.txt_note = QTextEdit()
        self.txt_note.setAcceptRichText(True)
        self.txt_note.setPlaceholderText("Not metnini buraya yaz\u0131n\u0131z...")
        self.txt_note.setStyleSheet(theme_qss(
            "QTextEdit { background: @surface; color: @text; border: 1px solid @border; "
            "border-radius: 0 0 7px 7px; padding: 10px; font-size: 12px; } "
            "QTextEdit:focus { border-color: @accent; }"
        ))
        for label, action in (("B", self._format_bold), ("I", self._format_italic),
                              ("U", self._format_underline), ("\u2261", self._format_bullets),
                              ("</>", self._format_code), ("\u25a3", self._insert_note_date)):
            button = QPushButton(label)
            button.setFixedSize(27, 24)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: transparent; color: @text_muted; border: 0; "
                "border-radius: 4px; font-size: 10px; font-weight: 700; } "
                "QPushButton:hover { background: @selection_bg; color: @accent; }"
            ))
            button.clicked.connect(action)
            toolbar_layout.addWidget(button)
        toolbar_layout.addStretch(1)
        self.note_character_label = QLabel("0 karakter")
        self.note_character_label.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 9px; color: @text_muted; background: transparent; border: none;"
        ))
        toolbar_layout.addWidget(self.note_character_label)
        self.editor_panel.setProperty("noteToolbar", toolbar)
        editor_layout.addWidget(toolbar)
        editor_layout.addWidget(self.txt_note, 1)
        self.txt_note.textChanged.connect(self._update_character_count)
        paste_hint = QFrame()
        paste_hint.setObjectName("notePasteHint")
        paste_hint.setFixedHeight(24)
        paste_hint.setStyleSheet(theme_qss(
            "QFrame#notePasteHint { background: @surface; border: 1px solid @border; "
            "border-top: 0; border-radius: 0 0 7px 7px; }"
        ))
        paste_layout = QHBoxLayout(paste_hint)
        paste_layout.setContentsMargins(10, 0, 10, 0)
        paste_hint_label = QLabel(
            "\U0001f4ce Dosya veya ekran g\u00f6r\u00fcnt\u00fcs\u00fc yap\u0131\u015ft\u0131rabilirsiniz (Ctrl+V)"
        )
        paste_hint_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 8px; border: 0;"))
        encoding_label = QLabel("UTF-8 Destekli")
        encoding_label.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; color: @text_muted; font-size: 8px; border: 0;"
        ))
        paste_layout.addWidget(paste_hint_label)
        paste_layout.addStretch(1)
        paste_layout.addWidget(encoding_label)
        editor_layout.addWidget(paste_hint)
        editor_layout.addSpacing(16)
        self.splitter.addWidget(self.editor_panel)
        self.splitter.setSizes([280, 556])
        self.content_layout.addWidget(self.splitter, 1)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Genel Not", "WhatsApp Mesaj\u0131", "SMS", "Telefon G\u00f6r\u00fc\u015fmesi", "E-Posta"])
        self.cmb_type.setFixedSize(132, 28)
        self.cmb_type.currentTextChanged.connect(self._on_type_changed)
        self.last_updated_label = QLabel("Son G\u00fcncelleme: --:--")
        self.last_updated_label.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 8px; color: @text_muted;"
        ))
        self.set_footer_visible(True, height=50)
        self.footer_layout.setContentsMargins(14, 0, 14, 0)
        self.footer_layout.setSpacing(4)
        category_label = QLabel("Kategori:")
        category_label.setFixedWidth(38)
        category_label.setStyleSheet(theme_qss("font-size: 9px; color: @text_muted;"))
        self.footer_layout.addWidget(category_label)
        self.footer_layout.addWidget(self.cmb_type)
        self.footer_layout.addWidget(self.last_updated_label)
        self.footer_layout.addStretch(1)
        self.btn_new = QPushButton("+ Yeni Not")
        self.btn_new.setFixedSize(79, 30)
        self.btn_new.clicked.connect(self._new_note)
        self.btn_save = QPushButton("Kaydet / G\u00fcncelle")
        self.btn_save.setFixedSize(126, 30)
        self.btn_save.clicked.connect(self.save_note)
        self.btn_save.setStyleSheet(theme_qss(
            "QPushButton { background: @accent; color: @selection_text; border: 0; "
            "border-radius: 7px; font-size: 10px; font-weight: 700; } "
            "QPushButton:hover { background: @accent_hover; }"
        ))
        self.footer_layout.addWidget(self.btn_new)
        self.footer_layout.addSpacing(5)
        self.footer_layout.addWidget(self.btn_save)
        self._selected_note_id = None
        self._new_note()

    def _merge_note_format(self, char_format):
        cursor = self.txt_note.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(char_format)
        self.txt_note.mergeCurrentCharFormat(char_format)

    def _format_bold(self):
        char_format = QTextCharFormat()
        char_format.setFontWeight(QFont.Weight.Bold)
        self._merge_note_format(char_format)

    def _format_italic(self):
        char_format = QTextCharFormat()
        char_format.setFontItalic(True)
        self._merge_note_format(char_format)

    def _format_underline(self):
        char_format = QTextCharFormat()
        char_format.setFontUnderline(True)
        self._merge_note_format(char_format)

    def _format_bullets(self):
        cursor = self.txt_note.textCursor()
        cursor.createList(QTextListFormat.Style.ListDisc)
        self.txt_note.setTextCursor(cursor)

    def _format_code(self):
        char_format = QTextCharFormat()
        char_format.setFontFamily("JetBrains Mono")
        char_format.setBackground(QColor(tc("surface_alt")))
        self._merge_note_format(char_format)

    def _insert_note_date(self):
        self.txt_note.textCursor().insertText(datetime.now().strftime("%Y-%m-%d"))

    def setup_modern_content(self):
        # 1. Filter Bar
        filter_frame = QFrame()
        filter_lay = QHBoxLayout(filter_frame)
        filter_lay.setContentsMargins(0, 5, 0, 5)
        filter_lay.setSpacing(8)
        
        self.filter_buttons = []
        filter_options = [
            ("Tümü", "Tümü"),
            ("Genel Not", "Genel Not"),
            ("WhatsApp", "WhatsApp Mesajı"),
            ("SMS", "SMS"),
            ("Telefon", "Telefon Görüşmesi"),
            ("E-Posta", "E-Posta"),
            ("Teklif", "PC Teklif"),
        ]
        
        for text, val in filter_options:
            btn = FilterButton(text, val)
            btn.clicked.connect(lambda checked, b=btn: self.set_filter(b))
            filter_lay.addWidget(btn)
            self.filter_buttons.append(btn)
            if text == "Tümü":
                btn.setChecked(True)
                btn.update_style(True)
        
        filter_lay.addStretch()
        self.content_layout.addWidget(filter_frame)

        # 2. Notes List Area
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("NotesList")
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_widget.setStyleSheet(theme_qss("""
            QListWidget#NotesList {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item { background-color: transparent; padding: 0; }
            QListWidget::item:selected { background-color: transparent; }
        """))
        self.splitter.addWidget(self.list_widget)

        self.editor_panel = QFrame()
        editor_layout = QVBoxLayout(self.editor_panel)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Not ba\u015fl\u0131\u011f\u0131")
        editor_layout.addWidget(self.title_edit)
        self.txt_note = QTextEdit()
        self.txt_note.setPlaceholderText("Not metnini buraya yaz\u0131n\u0131z...")
        editor_layout.addWidget(self.txt_note, 1)
        editor_buttons = QHBoxLayout()
        self.btn_new = QPushButton("Yeni Not")
        self.btn_new.clicked.connect(self._new_note)
        self.btn_save = QPushButton("Kaydet / G\u00fcncelle")
        self.btn_save.clicked.connect(self.save_note)
        editor_buttons.addWidget(self.cmb_type if hasattr(self, "cmb_type") else QLabel(""))
        editor_buttons.addStretch()
        editor_buttons.addWidget(self.btn_new)
        editor_buttons.addWidget(self.btn_save)
        editor_layout.addLayout(editor_buttons)
        self.splitter.addWidget(self.editor_panel)
        self.splitter.setSizes([360, 780])
        self.content_layout.addWidget(self.splitter, 1)

        # 3. Keep a compact type selector for communication records.
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Genel Not", "WhatsApp Mesaj\u0131", "SMS", "Telefon G\u00f6r\u00fc\u015fmesi", "E-Posta"])
        editor_buttons.replaceWidget(editor_buttons.itemAt(0).widget(), self.cmb_type)
        self._selected_note_id = None
        self.list_widget.itemClicked.connect(self._open_selected_note)
        self._new_note()
        return

        # 3. Input Area
        input_frame = QFrame()
        input_frame.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: 16px;
            }
        """))
        input_lay = QVBoxLayout(input_frame)
        input_lay.setContentsMargins(20, 20, 20, 20)
        input_lay.setSpacing(12)
        
        lbl_new = QLabel("Yeni Not veya İletişim Kaydı Ekle")
        lbl_new.setStyleSheet(theme_qss("font-weight: bold; color: @text; font-size: 13px; border: none;"))
        input_lay.addWidget(lbl_new)

        self.txt_note = QTextEdit()
        self.txt_note.setPlaceholderText("İçeriği buraya yazınız...")
        self.txt_note.setFixedHeight(110)
        self.txt_note.setStyleSheet(theme_qss("""
            QTextEdit {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
                color: @text;
            }
            QTextEdit:focus { border-color: @accent; }
        """))
        input_lay.addWidget(self.txt_note)
        
        # Bottom Tools
        tools_lay = QHBoxLayout()
        
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Genel Not", "WhatsApp Mesajı", "SMS", "Telefon Görüşmesi", "E-Posta"])
        self.cmb_type.setFixedHeight(38)
        self.cmb_type.setFixedWidth(160)
        self.cmb_type.setStyleSheet(theme_qss("""
            QComboBox {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 0 10px;
                font-weight: 500;
            }
            QComboBox:hover { border-color: @accent; background-color: @surface_alt; }
        """))
        self.cmb_type.currentTextChanged.connect(self._on_type_changed)
        
        self.btn_save = QPushButton("💾 KAYDET")
        self.btn_save.setFixedWidth(120)
        self.btn_save.setFixedHeight(38)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        self.btn_save.clicked.connect(self.save_note)
        
        tools_lay.addWidget(self.cmb_type)
        tools_lay.addStretch()
        tools_lay.addWidget(self.btn_save)
        
        input_lay.addLayout(tools_lay)
        self.content_layout.addWidget(input_frame)
        self._on_type_changed(self.cmb_type.currentText())

    def set_filter(self, clicked_btn):
        for btn in self.filter_buttons:
            if btn != clicked_btn:
                btn.setChecked(False)
                btn.update_style(False)
        
        clicked_btn.setChecked(True)
        clicked_btn.update_style(True)
        self.current_filter = clicked_btn.type_val
        self.load_notes()
    
    def load_notes(self):
        selected_id = self._selected_note_id
        self.list_widget.clear()
        try:
            notes = self.db.get_customer_notes(self.customer_id)
            total_note_count = len(notes)
            for button in self.filter_buttons:
                if button.type_val == "T\u00fcm\u00fc":
                    button.setText("T\u00fcm\u00fc {}".format(total_note_count))
            if self.current_filter != "T\u00fcm\u00fc":
                if self.current_filter == "PC Teklif":
                    notes = [note for note in notes if note[1] in ("PC Teklif", "Teklif")]
                else:
                    notes = [note for note in notes if note[1] == self.current_filter]
            query = self.search_input.text().strip().casefold()
            if query:
                notes = [
                    note for note in notes
                    if query in " ".join(str(value or "") for value in note).casefold()
                ]
            self.notes_count_label.setText(
                "{} Kay\u0131t Listelendi".format(len(notes))
            )
            if not notes:
                item = QListWidgetItem(
                    "Bu m\u00fc\u015fteriye ait not yok.\nYeni Not ile ba\u015flay\u0131n."
                )
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setSizeHint(QSize(240, 84))
                self.list_widget.addItem(item)
                return

            selected_row = 0
            for index, note in enumerate(notes):
                title = note[2] or note[4] or "Not"
                raw_content = re.sub(r"<[^>]+>", " ", str(note[3] or ""))
                preview = " ".join(raw_content.split())[:78]
                note_type = str(note[1] or "Genel Not")
                date = str(note[4] or "")
                item = QListWidgetItem()
                item.setSizeHint(QSize(240, 109))
                item.setData(Qt.ItemDataRole.UserRole, note)
                self.list_widget.addItem(item)
                item.setSizeHint(QSize(240, 105))
                self.list_widget.setItemWidget(item, self._build_note_card(
                    title, preview, date, note_type
                ))
                if selected_id and str(note[0]) == str(selected_id):
                    selected_row = index
            if selected_id or self._selected_note_id is None:
                self.list_widget.setCurrentRow(selected_row)
                self._open_selected_note(self.list_widget.currentItem())
        except Exception as e:
            logger.warning(
                "Customer notes load failed for customer %s: %s",
                self.customer_id,
                e,
            )

    def _build_note_card(self, title, preview, date, note_type):
        card = QFrame()
        card.setObjectName("NoteHistoryCard")
        card.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        card.setStyleSheet(theme_qss(
            "QFrame#NoteHistoryCard { background: @surface; border: 1px solid @border; "
            "border-left: 3px solid @border; border-radius: 7px; }"
        ))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 7, 8, 6)
        layout.setSpacing(3)
        title_row = QHBoxLayout()
        title_label = QLabel(str(title))
        title_label.setStyleSheet(theme_qss(
            "font-size: 10px; font-weight: 700; color: @text; background: transparent; border: 0;"
        ))
        category = QLabel(str(note_type))
        category_color = {
            "WhatsApp Mesaj\u0131": "@success",
            "WhatsApp": "@success",
            "SMS": "@warning",
            "Telefon G\u00f6r\u00fc\u015fmesi": "@electric_blue",
            "E-Posta": "#a78bfa",
            "PC Teklif": "@accent",
        }.get(str(note_type), "@accent")
        category.setStyleSheet(theme_qss(
            f"font-size: 8px; font-weight: 700; color: {category_color}; background: @surface_alt; "
            "border: 1px solid @border; border-radius: 4px; padding: 1px 5px;"
        ))
        title_row.addWidget(title_label, 1)
        title_row.addWidget(category)
        layout.addLayout(title_row)
        preview_label = QLabel(str(preview))
        preview_label.setWordWrap(True)
        preview_label.setMaximumHeight(28)
        preview_label.setStyleSheet(theme_qss(
            "font-size: 8px; color: @text_muted; background: transparent; border: 0;"
        ))
        layout.addWidget(preview_label, 1)
        date_label = QLabel(str(date))
        date_label.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 8px; color: @text_muted; "
            "background: transparent; border: 0;"
        ))
        layout.addWidget(date_label)
        return card

    def _update_character_count(self):
        self.note_character_label.setText(
            "{} karakter".format(len(self.txt_note.toPlainText()))
        )

    def save_note(self):
        content = self.txt_note.toHtml().strip()
        title = self.title_edit.text().strip()
        if not title:
            title = "Not " + datetime.now().strftime("%Y-%m-%d %H:%M")
        if not self.txt_note.toPlainText().strip():
            show_error(self, "Not i\u00e7eri\u011fi bo\u015f b\u0131rak\u0131lamaz.")
            return
        note_type = self.cmb_type.currentText()
        try:
            if self._selected_note_id:
                self.db.cursor.execute("PRAGMA table_info(customer_notes)")
                columns = {row[1] for row in (self.db.cursor.fetchall() or [])}
                if "title" not in columns:
                    self.db.cursor.execute("ALTER TABLE customer_notes ADD COLUMN title TEXT")
                    columns.add("title")
                type_column = "note_type" if "note_type" in columns else "type"
                self.db.cursor.execute(
                    f"UPDATE customer_notes SET title=?, content=?, {type_column}=? WHERE id=? AND customer_id=?",
                    (title, content, note_type, self._selected_note_id, self.customer_id),
                )
                if self.db.cursor.rowcount == 0:
                    raise RuntimeError("Not kaydi bulunamadi veya bu musteriye ait degil.")
                self.db.conn.commit()
            else:
                if not self.db.add_customer_note(self.customer_id, note_type, content, title):
                    raise RuntimeError("Yeni not kaydedilemedi.")
        except Exception as exc:
            logger.exception("Customer note save failed")
            show_error(self, f"Not kaydedilemedi: {exc}")
            return
        self.load_notes()
        self._new_note()

    def _new_note(self):
        self._selected_note_id = None
        self.title_edit.clear()
        self.txt_note.clear()
        self.cmb_type.setCurrentText("Genel Not")
        self.date_label.setText("Yeni not - tarih kay\u0131tta olu\u015fturulacak")
        if hasattr(self, "last_updated_label"):
            self.last_updated_label.setText("Son G\u00fcncelleme: --:--")

    def _open_selected_note(self, item, *_args):
        note = item.data(Qt.ItemDataRole.UserRole)
        if not note:
            return
        self._selected_note_id = note[0]
        self.cmb_type.setCurrentText(note[1])
        self.title_edit.setText(note[2] or note[4] or "Not")
        self.txt_note.setHtml(note[3] or "")
        self.date_label.setText(f"Kay\u0131t tarihi: {note[4] or '-'}")
        if hasattr(self, "last_updated_label"):
            self.last_updated_label.setText(
                "Son G\u00fcncelleme: {}".format(
                    str(note[4] or "--:--").replace("T", " ").split()[-1][:5]
                )
            )
        
    def delete_note(self, note_id):
        # Using simple confirm dialog but will be framed
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        dlg = SimpleConfirmDialog(self, title="Sil", text="Bu kaydı silmek istiyor musunuz", ok_text="Sil", cancel_text="İptal", btn_color=tc("danger"))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.db.delete_customer_note(note_id)
            self.load_notes()

    def open_note(self, note_data):
        dlg = OfferPreviewDialog(self.db, note_data, self)
        dlg.deleted.connect(lambda _note_id: self.load_notes())
        dlg.exec()

    def export_note_pdf(self, note_data):
        dlg = OfferPreviewDialog(self.db, note_data, self)
        dlg.export_pdf_to_path()

    def _on_type_changed(self, note_type):
        placeholders = {
            "Genel Not": "Genel not içeriğini yazın...",
            "WhatsApp Mesajı": "WhatsApp mesaj içeriğini yazın...",
            "SMS": "SMS içeriğini yazın...",
            "Telefon Görüşmesi": "Telefon görüşmesi notunu yazın...",
            "E-Posta": "E-posta içeriğini yazın..."
        }
        self.txt_note.setPlaceholderText(placeholders.get(note_type, "İçeriği buraya yazınız..."))
