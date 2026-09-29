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
from PyQt6.QtGui import QFont, QColor, QIcon, QAction
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.logger import logger
from src.utils.toast_notification import show_success, show_error

class FilterButton(QPushButton):
    def __init__(self, text, type_val, parent=None):
        super().__init__(text, parent)
        self.type_val = type_val
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self.setCheckable(True)
        self.update_style(False)

    def update_style(self, active):
        if active:
            self.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @accent;
                    color: white;
                    border-radius: 16px;
                    padding: 0 15px;
                    font-weight: bold;
                    border: none;
                }
            """))
        else:
            self.setStyleSheet(theme_qss("""
                QPushButton {
                    background-color: @surface_alt;
                    color: @text_muted;
                    border: 1px solid @border;
                    border-radius: 16px;
                    padding: 0 15px;
                    font-weight: 500;
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
        
        super().__init__(parent, title=f"M\u00fc\u015fteri Notlar\u0131 - {customer_name}", width=1200, height=820)
        
        self.setup_modern_content_clean()
        self.load_notes()

    def setup_modern_content_clean(self):
        """Build the split note-history and document editor layout."""
        filter_frame = QFrame()
        filter_lay = QHBoxLayout(filter_frame)
        filter_lay.setContentsMargins(0, 4, 0, 8)
        filter_lay.setSpacing(8)
        self.filter_buttons = []
        for text, value in (("T\u00fcm\u00fc", "T\u00fcm\u00fc"), ("Genel Not", "Genel Not"),
                            ("WhatsApp", "WhatsApp Mesaj\u0131"), ("SMS", "SMS"),
                            ("Telefon", "Telefon G\u00f6r\u00fc\u015fmesi"), ("E-Posta", "E-Posta"),
                            ("Teklif", "PC Teklif")):
            button = FilterButton(text, value)
            button.clicked.connect(lambda _checked, b=button: self.set_filter(b))
            button.setChecked(text == "T\u00fcm\u00fc")
            button.update_style(text == "T\u00fcm\u00fc")
            filter_lay.addWidget(button)
            self.filter_buttons.append(button)
        filter_lay.addStretch()
        self.content_layout.addWidget(filter_frame)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("NotesList")
        self.list_widget.setMinimumWidth(300)
        self.list_widget.setStyleSheet(theme_qss("""
            QListWidget#NotesList { background: @surface_alt; border: 1px solid @border; border-radius: 10px; }
            QListWidget::item { padding: 12px 14px; border-bottom: 1px solid @border; color: @text; }
            QListWidget::item:selected { background: @selection_bg; color: @text; border-left: 3px solid @accent; }
        """))
        self.list_widget.itemClicked.connect(self._open_selected_note)
        self.splitter.addWidget(self.list_widget)

        self.editor_panel = QFrame()
        self.editor_panel.setObjectName("noteEditorPanel")
        editor_layout = QVBoxLayout(self.editor_panel)
        editor_layout.setContentsMargins(18, 18, 18, 18)
        editor_layout.setSpacing(10)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Not ba\u015fl\u0131\u011f\u0131")
        self.title_edit.setMinimumHeight(42)
        self.title_edit.setStyleSheet(theme_qss("QLineEdit { font-size: 16px; font-weight: 700; padding: 8px 12px; background: @surface; color: @text; border: 1px solid @border; border-radius: 8px; }"))
        editor_layout.addWidget(self.title_edit)
        self.date_label = QLabel("Yeni not - tarih kay\u0131tta olu\u015fturulacak")
        self.date_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        editor_layout.addWidget(self.date_label)
        self.txt_note = QTextEdit()
        self.txt_note.setAcceptRichText(True)
        self.txt_note.setPlaceholderText("Not metnini buraya yaz\u0131n\u0131z...")
        self.txt_note.setStyleSheet(theme_qss("QTextEdit { background: @surface; color: @text; border: 1px solid @border; border-radius: 8px; padding: 12px; font-size: 14px; }"))
        editor_layout.addWidget(self.txt_note, 1)
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Genel Not", "WhatsApp Mesaj\u0131", "SMS", "Telefon G\u00f6r\u00fc\u015fmesi", "E-Posta"])
        self.cmb_type.setFixedWidth(180)
        actions = QHBoxLayout()
        actions.addWidget(self.cmb_type)
        actions.addStretch()
        self.btn_new = QPushButton("Yeni Not")
        self.btn_new.clicked.connect(self._new_note)
        actions.addWidget(self.btn_new)
        self.btn_save = QPushButton("Kaydet / G\u00fcncelle")
        self.btn_save.clicked.connect(self.save_note)
        actions.addWidget(self.btn_save)
        editor_layout.addLayout(actions)
        self.splitter.addWidget(self.editor_panel)
        self.splitter.setSizes([330, 820])
        self.content_layout.addWidget(self.splitter, 1)
        self._selected_note_id = None
        self._new_note()

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
        self.list_widget.clear()
        try:
            notes = self.db.get_customer_notes(self.customer_id)
            if self.current_filter != "Tümü":
                if self.current_filter == "PC Teklif":
                    notes = [n for n in notes if n[1] in ("PC Teklif", "Teklif")]
                else:
                    notes = [n for n in notes if n[1] == self.current_filter]
                
            if not notes:
                item = QListWidgetItem("Bu m\u00fc\u015fteriye ait not yok.\nYeni Not ile ba\u015flay\u0131n.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list_widget.addItem(item)
                return

            for n in notes:
                title = n[2] or n[4] or "Not"
                date = n[4] or ""
                item = QListWidgetItem(f"{title}\n{date}")
                item.setData(Qt.ItemDataRole.UserRole, n)
                self.list_widget.addItem(item)
        except Exception as e:
            logger.warning(f"Customer notes load failed for customer {self.customer_id}: {e}")

    def save_note(self):
        content = self.txt_note.toHtml().strip()
        title = self.title_edit.text().strip()
        if not title:
            title = "Not " + datetime.now().strftime("%Y-%m-%d %H:%M")
        if not content or content == "<p></p>": return
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
        self._new_note()
        self.load_notes()

    def _new_note(self):
        self._selected_note_id = None
        self.title_edit.clear()
        self.txt_note.clear()
        self.cmb_type.setCurrentText("Genel Not")
        self.date_label.setText("Yeni not - tarih kay\u0131tta olu\u015fturulacak")

    def _open_selected_note(self, item, *_args):
        note = item.data(Qt.ItemDataRole.UserRole)
        if not note:
            return
        self._selected_note_id = note[0]
        self.cmb_type.setCurrentText(note[1])
        self.title_edit.setText(note[2] or note[4] or "Not")
        self.txt_note.setHtml(note[3] or "")
        self.date_label.setText(f"Kay\u0131t tarihi: {note[4] or '-'}")
        
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
