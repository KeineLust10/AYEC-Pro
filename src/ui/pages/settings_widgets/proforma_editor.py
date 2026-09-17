# -*- coding: utf-8 -*-
"""Word-like proforma template editor widget.

Replaces the legacy coordinate-drawing designer. The user edits a rich-text
document (fonts, colors, alignment, lists, images, dynamic field codes),
previews a real PDF rendered with sample offer data, and can activate the
template for production or switch back to the embedded professional builder.
"""

import os
import tempfile

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QImage,
    QKeySequence,
    QTextCharFormat,
    QTextCursor,
    QTextListFormat,
)
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFontComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.utils import message_helper
from src.utils.theme_colors import theme_qss
from src.utils.custom_editor_proforma import (
    SETTING_TEMPLATE_HTML,
    SETTING_USE_CUSTOM,
    default_template_html,
)

# key -> (menu label, inline?) mapping for dynamic fields
_FIELD_MENU = [
    ("firma_adi", "Firma Ad\u0131"),
    ("musteri_adi", "M\u00fc\u015fteri Ad\u0131"),
    ("yetkili", "Yetkili"),
    ("proje", "Proje"),
    ("teklif_no", "Teklif No"),
    ("tarih", "Tarih"),
    ("gecerlilik", "Ge\u00e7erlilik Tarihi"),
    ("para_birimi", "Para Birimi"),
    (None, None),  # separator
    ("logo", "Logo (Blok)"),
    ("urun_tablosu", "\u00dcr\u00fcn Tablosu (Blok)"),
    ("toplamlar", "Toplamlar (Blok)"),
    ("ticari_kosullar", "Ticari Ko\u015fullar (Blok)"),
    ("imza_alani", "\u0130mza Alan\u0131 (Blok)"),
]

_SAMPLE_ITEMS = [
    {"service": "\u00d6rnek \u00dcr\u00fcn 1", "description": "A\u00e7\u0131klama sat\u0131r\u0131", "qty": 2, "price": 1500.0},
    {"service": "\u00d6rnek Hizmet 2", "description": "Kurulum ve devreye alma", "qty": 1, "price": 4750.0},
    {"service": "\u00d6rnek \u00dcr\u00fcn 3", "description": "Aksesuar seti", "qty": 4, "price": 320.0},
]
_SAMPLE_TOTALS = (8030.0, 0.0, 0.20, 1606.0, 9636.0)


class ProformaTemplateEditor(QWidget):
    """Rich-text template editor bound to the proforma settings keys."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self._load_template()
        self._refresh_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.lbl_status = QLabel()
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setStyleSheet(theme_qss(
            "QToolBar { background: @surface_alt; border: 1px solid @border; "
            "border-radius: 8px; padding: 4px; spacing: 4px; } "
            "QToolButton { color: @text; padding: 4px 8px; border-radius: 4px; } "
            "QToolButton:hover { background: @surface; } "
            "QToolButton:checked { background: @accent; color: @selection_text; }"
        ))

        self.font_box = QFontComboBox()
        self.font_box.setMaximumWidth(160)
        self.font_box.currentFontChanged.connect(self._apply_font_family)
        toolbar.addWidget(self.font_box)

        self.size_box = QComboBox()
        for s in (8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28):
            self.size_box.addItem(str(s), s)
        self.size_box.setCurrentText("10")
        self.size_box.currentIndexChanged.connect(self._apply_font_size)
        toolbar.addWidget(self.size_box)
        toolbar.addSeparator()

        self.act_bold = self._tool_action(toolbar, "K", "Kal\u0131n (Ctrl+B)", checkable=True)
        self.act_bold.setShortcut(QKeySequence.StandardKey.Bold)
        self.act_bold.triggered.connect(self._apply_bold)
        self.act_italic = self._tool_action(toolbar, "T", "\u0130talik (Ctrl+I)", checkable=True)
        self.act_italic.setShortcut(QKeySequence.StandardKey.Italic)
        self.act_italic.triggered.connect(self._apply_italic)
        self.act_underline = self._tool_action(toolbar, "A", "Alt\u0131 \u00e7izili (Ctrl+U)", checkable=True)
        self.act_underline.setShortcut(QKeySequence.StandardKey.Underline)
        self.act_underline.triggered.connect(self._apply_underline)
        act_color = self._tool_action(toolbar, "Renk", "Yaz\u0131 rengi")
        act_color.triggered.connect(self._apply_color)
        toolbar.addSeparator()

        act_left = self._tool_action(toolbar, "Sola", "Sola hizala")
        act_left.triggered.connect(lambda: self._apply_align(Qt.AlignmentFlag.AlignLeft))
        act_center = self._tool_action(toolbar, "Orta", "Ortala")
        act_center.triggered.connect(lambda: self._apply_align(Qt.AlignmentFlag.AlignCenter))
        act_right = self._tool_action(toolbar, "Sa\u011fa", "Sa\u011fa hizala")
        act_right.triggered.connect(lambda: self._apply_align(Qt.AlignmentFlag.AlignRight))
        act_list = self._tool_action(toolbar, "Liste", "Madde i\u015faretli liste")
        act_list.triggered.connect(self._apply_bullet_list)
        toolbar.addSeparator()

        act_image = self._tool_action(toolbar, "G\u00f6rsel", "G\u00f6rsel ekle")
        act_image.triggered.connect(self._insert_image)

        btn_field = QToolButton()
        btn_field.setText("Alan Ekle \u25be")
        btn_field.setToolTip("Dinamik alan ekle (\u00fcretimde ger\u00e7ek veriyle dolar)")
        btn_field.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(btn_field)
        for key, label in _FIELD_MENU:
            if key is None:
                menu.addSeparator()
                continue
            action = menu.addAction(label)
            action.triggered.connect(lambda checked=False, k=key: self._insert_field(k))
        btn_field.setMenu(menu)
        toolbar.addWidget(btn_field)

        root.addWidget(toolbar)

        # A4-like page canvas
        page_wrap = QScrollArea()
        page_wrap.setWidgetResizable(True)
        page_wrap.setFrameShape(QFrame.Shape.NoFrame)
        page_wrap.setStyleSheet(theme_qss("QScrollArea { background: @surface; border: 1px solid @border; border-radius: 8px; }"))

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        # ~A4 width at 96 dpi minus margins; gives a page-like editing surface
        self.editor.setFixedWidth(794)
        self.editor.setMinimumHeight(560)
        self.editor.setStyleSheet(
            "QTextEdit { background: white; color: #1F2937; border: none; padding: 36px 44px; font-size: 10pt; }"
        )
        self.editor.cursorPositionChanged.connect(self._sync_toolbar)

        holder = QWidget()
        holder.setStyleSheet(theme_qss("background: @surface;"))
        hl = QHBoxLayout(holder)
        hl.setContentsMargins(12, 12, 12, 12)
        hl.addStretch(1)
        hl.addWidget(self.editor)
        hl.addStretch(1)
        page_wrap.setWidget(holder)
        page_wrap.setMinimumHeight(480)
        root.addWidget(page_wrap, 1)

        # Action buttons
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        bh = QHBoxLayout(btn_row)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(8)

        self.btn_save = QPushButton("\u015eablonu Kaydet")
        self.btn_save.setFixedHeight(36)
        self.btn_save.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 6px; padding: 0 14px; font-weight: bold; } "
            "QPushButton:hover { background: @surface; }"
        ))
        self.btn_save.clicked.connect(self._save_template)
        bh.addWidget(self.btn_save)

        self.btn_preview = QPushButton("PDF \u00d6nizleme")
        self.btn_preview.setFixedHeight(36)
        self.btn_preview.setStyleSheet(theme_qss(
            "QPushButton { background: @accent_hover; color: @selection_text; border-radius: 6px; "
            "padding: 0 14px; font-weight: bold; } QPushButton:hover { background: @accent; }"
        ))
        self.btn_preview.clicked.connect(self._preview_pdf)
        bh.addWidget(self.btn_preview)

        self.btn_activate = QPushButton("PDF'e \u00c7evir ve Proforma Olarak Kullan")
        self.btn_activate.setFixedHeight(36)
        self.btn_activate.setStyleSheet(theme_qss(
            "QPushButton { background: @accent; color: @selection_text; border-radius: 6px; "
            "padding: 0 14px; font-weight: bold; } QPushButton:hover { background: @accent_hover; }"
        ))
        self.btn_activate.clicked.connect(self._activate_template)
        bh.addWidget(self.btn_activate)

        self.btn_reset = QPushButton("Varsay\u0131lana D\u00f6n")
        self.btn_reset.setFixedHeight(36)
        self.btn_reset.setStyleSheet(theme_qss(
            "QPushButton { background: @danger; color: @selection_text; border-radius: 6px; "
            "padding: 0 14px; font-weight: bold; }"
        ))
        self.btn_reset.clicked.connect(self._reset_to_default)
        bh.addWidget(self.btn_reset)
        bh.addStretch(1)
        root.addWidget(btn_row)

    def _tool_action(self, toolbar, text, tooltip, checkable=False):
        action = QAction(text, self)
        action.setToolTip(tooltip)
        action.setCheckable(checkable)
        toolbar.addAction(action)
        return action

    # ------------------------------------------------------------------
    # Formatting handlers
    # ------------------------------------------------------------------
    def _merge_char_format(self, fmt):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _apply_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.act_bold.isChecked() else QFont.Weight.Normal)
        self._merge_char_format(fmt)

    def _apply_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.act_italic.isChecked())
        self._merge_char_format(fmt)

    def _apply_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.act_underline.isChecked())
        self._merge_char_format(fmt)

    def _apply_color(self):
        color = QColorDialog.getColor(self.editor.textColor(), self, "Yaz\u0131 Rengi")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self._merge_char_format(fmt)

    def _apply_font_family(self, qfont):
        fmt = QTextCharFormat()
        fmt.setFontFamilies([qfont.family()])
        self._merge_char_format(fmt)

    def _apply_font_size(self):
        size = self.size_box.currentData()
        if size:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(float(size))
            self._merge_char_format(fmt)

    def _apply_align(self, flag):
        self.editor.setAlignment(flag)
        self.editor.setFocus()

    def _apply_bullet_list(self):
        cursor = self.editor.textCursor()
        list_fmt = QTextListFormat()
        list_fmt.setStyle(QTextListFormat.Style.ListDisc)
        cursor.createList(list_fmt)
        self.editor.setFocus()

    def _sync_toolbar(self):
        fmt = self.editor.currentCharFormat()
        self.act_bold.setChecked(fmt.fontWeight() >= QFont.Weight.Bold)
        self.act_italic.setChecked(fmt.fontItalic())
        self.act_underline.setChecked(fmt.fontUnderline())

    # ------------------------------------------------------------------
    # Content helpers
    # ------------------------------------------------------------------
    def _insert_field(self, key):
        cursor = self.editor.textCursor()
        block = key in {"logo", "urun_tablosu", "toplamlar", "ticari_kosullar", "imza_alani"}
        token = "{{" + key + "}}"
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#145A86"))
        fmt.setFontWeight(QFont.Weight.Bold)
        if block:
            # Block fields live on their own paragraph so production rendering
            # can replace them with full-width flowables.
            if cursor.block().text().strip():
                cursor.insertBlock()
            cursor.insertText(token, fmt)
            cursor.insertBlock()
        else:
            cursor.insertText(token, fmt)
        plain = QTextCharFormat()
        plain.setForeground(QColor("#1F2937"))
        plain.setFontWeight(QFont.Weight.Normal)
        cursor.setCharFormat(plain)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "G\u00f6rsel Se\u00e7", "", "G\u00f6rseller (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            message_helper.show_warning(self, "Uyar\u0131", "G\u00f6rsel okunamad\u0131.")
            return
        cursor = self.editor.textCursor()
        cursor.insertHtml(f'<img src="{path}" />')
        self.editor.setFocus()

    # ------------------------------------------------------------------
    # Persistence / production hooks
    # ------------------------------------------------------------------
    def _load_template(self):
        html = str(self.db.get_setting(SETTING_TEMPLATE_HTML, "") or "").strip()
        if not html:
            html = default_template_html()
        self.editor.setHtml(html)

    def _save_template(self, silent=False):
        html = self.editor.toHtml()
        self.db.set_setting(SETTING_TEMPLATE_HTML, html)
        if not silent:
            message_helper.show_success(self, "Ba\u015far\u0131l\u0131", "\u015eablon kaydedildi.")
        self._refresh_status()

    def _render_sample(self, save_path):
        from src.utils.pdf_manager import PDFManagerQt
        from src.utils.custom_editor_proforma import build_custom_editor_proforma

        manager = PDFManagerQt(self.db)
        company = str(self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro")
        return build_custom_editor_proforma(
            manager,
            cart_items=_SAMPLE_ITEMS,
            totals=_SAMPLE_TOTALS,
            company_name=company,
            customer_name="\u00d6rnek M\u00fc\u015fteri A.\u015e.",
            save_path=save_path,
            currency="\u20ba",
            project_name="\u00d6rnek Proje",
            contact_name="Ad Soyad",
            reference_no="PRF-ONIZLEME",
            currency_code="TRY",
            template_html=self.editor.toHtml(),
        )

    def _preview_pdf(self):
        fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix="proforma_onizleme_")
        os.close(fd)
        ok, result = self._render_sample(tmp_path)
        if not ok:
            message_helper.show_error(self, "Hata", f"\u00d6nizleme olu\u015fturulamad\u0131:\n{result}")
            return
        self._show_pdf_dialog(result)

    def _show_pdf_dialog(self, pdf_path):
        try:
            from PyQt6.QtPdf import QPdfDocument
            from PyQt6.QtPdfWidgets import QPdfView
        except Exception:
            # Fall back to the system PDF viewer if Qt PDF widgets are missing
            try:
                os.startfile(pdf_path)
            except Exception:
                pass
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Proforma \u00d6nizleme")
        dlg.resize(860, 900)
        lay = QVBoxLayout(dlg)
        doc = QPdfDocument(dlg)
        doc.load(pdf_path)
        view = QPdfView(dlg)
        view.setDocument(doc)
        view.setPageMode(QPdfView.PageMode.MultiPage)
        view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        lay.addWidget(view)
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(dlg.accept)
        lay.addWidget(btn_close)
        dlg.exec()

    def _activate_template(self):
        # Validate by producing a real sample PDF before activation
        self._save_template(silent=True)
        fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix="proforma_dogrulama_")
        os.close(fd)
        ok, result = self._render_sample(tmp_path)
        if not ok:
            message_helper.show_error(
                self, "Hata",
                "\u015eablon PDF'e \u00e7evrilemedi, aktif edilmedi:\n" + str(result),
            )
            return
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        self.db.set_setting(SETTING_USE_CUSTOM, "1")
        self._refresh_status()
        message_helper.show_success(
            self, "Ba\u015far\u0131l\u0131",
            "\u015eablon aktif edildi. Bundan sonra t\u00fcm proforma PDF'leri bu \u015fablonla \u00fcretilecek.",
        )

    def _reset_to_default(self):
        self.db.set_setting(SETTING_USE_CUSTOM, "0")
        self._refresh_status()
        message_helper.show_success(
            self, "Ba\u015far\u0131l\u0131",
            "Varsay\u0131lan proforma \u00fcreticisine d\u00f6n\u00fcld\u00fc. \u015eablonunuz silinmedi; "
            "istedi\u011finizde tekrar aktif edebilirsiniz.",
        )

    def _refresh_status(self):
        active = str(self.db.get_setting(SETTING_USE_CUSTOM, "0") or "0").strip() in {"1", "true", "True"}
        if active:
            self.lbl_status.setText(
                "\u25cf Durum: \u00d6zel \u015fablon AKT\u0130F - proforma PDF'leri bu \u015fablonla \u00fcretiliyor."
            )
            self.lbl_status.setStyleSheet(theme_qss("color: @accent; font-weight: bold; font-size: 9pt;"))
        else:
            self.lbl_status.setText(
                "\u25cb Durum: Varsay\u0131lan profesyonel \u00fcretici aktif. \u015eablonu haz\u0131rlay\u0131p "
                "'PDF'e \u00c7evir ve Proforma Olarak Kullan' ile ge\u00e7i\u015f yapabilirsiniz."
            )
            self.lbl_status.setStyleSheet(theme_qss("color: @text_muted; font-size: 9pt;"))
